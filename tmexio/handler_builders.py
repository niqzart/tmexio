from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from inspect import Parameter, Signature, iscoroutinefunction, signature
from typing import Annotated, Any, Generic, TypeVar, get_args, get_origin

from asgiref.sync import sync_to_async
from pydantic import BaseModel, create_model

from tmexio import markers, packagers
from tmexio.event_handlers import (
    AsyncConnectHandler,
    AsyncDisconnectHandler,
    AsyncEventHandler,
    BaseAsyncHandler,
    BaseAsyncHandlerWithArguments,
)
from tmexio.exceptions import EventException
from tmexio.server import AsyncServer, AsyncSocket
from tmexio.specs import HandlerSpec
from tmexio.structures import ClientEvent


class Destinations:
    def __init__(self) -> None:
        self.markers: dict[markers.Marker[Any], set[str]] = {}
        self.body_annotations: dict[str, Any] = {}
        self.body_destinations: dict[str, set[str]] = {}

    def add_marker_destination(
        self, marker: markers.Marker[Any], destination: str
    ) -> None:
        self.markers.setdefault(marker, set()).add(destination)

    def add_body_field(self, field_name: str, parameter_annotation: Any) -> None:
        if get_origin(parameter_annotation) is not Annotated:
            parameter_annotation = parameter_annotation, ...
        self.body_annotations[field_name] = parameter_annotation
        self.body_destinations.setdefault(field_name, set()).add(field_name)

    def build_marker_destinations(self) -> list[tuple[markers.Marker[Any], list[str]]]:
        return [
            (marker, list(destinations))
            for marker, destinations in self.markers.items()
        ]

    def build_body_model(self) -> type[BaseModel] | None:
        if not self.body_annotations:
            return None
        return create_model(
            "Model",  # TODO better naming
            **self.body_annotations,
        )

    def build_body_destinations(self) -> list[tuple[str, list[str]]]:
        return [
            (field, list(destinations))
            for field, destinations in self.body_destinations.items()
        ]


HandlerType = TypeVar("HandlerType", bound=BaseAsyncHandler)


class HandlerBuilder(Generic[HandlerType]):
    type_to_marker: dict[type[Any], markers.Marker[Any]] = {
        AsyncServer: markers.AsyncServerMarker(),
        AsyncSocket: markers.AsyncSocketMarker(),
        ClientEvent: markers.ClientEventMarker(),
    }

    def __init__(
        self,
        function: Callable[..., Any],
        possible_exceptions: list[EventException],
    ) -> None:
        self.function = function
        self.signature: Signature = signature(function)
        self.destinations = Destinations()

        self.possible_exceptions = possible_exceptions

    def parse_parameter(self, parameter: Parameter) -> None:
        annotation = parameter.annotation
        if isinstance(annotation, type):
            marker = self.type_to_marker.get(annotation)
            if marker is not None:
                annotation = Annotated[annotation, marker]
        args = get_args(annotation)

        if (  # noqa: WPS337
            get_origin(annotation) is Annotated
            and len(args) == 2
            and isinstance(args[1], markers.Marker)
        ):
            self.destinations.add_marker_destination(args[1], parameter.name)
        else:
            self.destinations.add_body_field(parameter.name, parameter.annotation)

    def build_async_callable(self) -> Callable[..., Awaitable[Any]]:
        if iscoroutinefunction(self.function):
            return self.function
        elif callable(self.function):
            return sync_to_async(self.function)
        raise TypeError("Handler is not callable")

    def build_handler(self) -> HandlerType:
        raise NotImplementedError

    @classmethod
    def build_spec_from_handler(
        cls,
        handler: HandlerType,
        summary: str | None,
        description: str | None,
    ) -> HandlerSpec:
        raise NotImplementedError


HandlerWithExceptionsType = TypeVar(
    "HandlerWithExceptionsType", bound=BaseAsyncHandlerWithArguments
)


class HandlerWithExceptionsBuilder(
    HandlerBuilder[HandlerWithExceptionsType],
    Generic[HandlerWithExceptionsType],
):
    @classmethod
    def build_exceptions(
        cls, handler: HandlerWithExceptionsType
    ) -> Iterator[EventException]:
        yield from list(handler.possible_exceptions)
        if handler.body_model is None:
            yield handler.zero_arguments_expected_error
        else:
            yield handler.one_argument_expected_error


class EventHandlerBuilder(HandlerWithExceptionsBuilder[AsyncEventHandler]):
    def parse_return_annotation(self) -> packagers.CodedPackager[Any]:
        annotation = self.signature.return_annotation
        args = get_args(annotation)

        if annotation is None:
            return packagers.NoContentPackager()
        elif (  # noqa: WPS337
            get_origin(annotation) is Annotated
            and len(args) == 2
            and isinstance(args[1], packagers.CodedPackager)
        ):
            return args[1]
        return packagers.PydanticPackager(annotation)

    def build_handler(self) -> AsyncEventHandler:
        for parameter in self.signature.parameters.values():
            self.parse_parameter(parameter)
        ack_packager = self.parse_return_annotation()

        return AsyncEventHandler(
            async_callable=self.build_async_callable(),
            marker_destinations=self.destinations.build_marker_destinations(),
            body_model=self.destinations.build_body_model(),
            body_destinations=self.destinations.build_body_destinations(),
            possible_exceptions=set(self.possible_exceptions),
            ack_packager=ack_packager,
        )

    @classmethod
    def build_spec_from_handler(
        cls,
        handler: AsyncEventHandler,
        summary: str | None,
        description: str | None,
    ) -> HandlerSpec:
        return HandlerSpec(
            summary=summary,
            description=description,
            exceptions=list(cls.build_exceptions(handler)),
            ack_code=handler.ack_packager.code,
            ack_body_schema=handler.ack_packager.body_json_schema(),
            event_body_model=handler.body_model,
        )


class ConnectHandlerBuilder(HandlerWithExceptionsBuilder[AsyncConnectHandler]):
    def build_handler(self) -> AsyncConnectHandler:
        for parameter in self.signature.parameters.values():
            self.parse_parameter(parameter)

        if self.signature.return_annotation is not None:
            raise TypeError("Connection handlers can not return anything")

        return AsyncConnectHandler(
            async_callable=self.build_async_callable(),
            marker_destinations=self.destinations.build_marker_destinations(),
            body_model=self.destinations.build_body_model(),
            body_destinations=self.destinations.build_body_destinations(),
            possible_exceptions=set(self.possible_exceptions),
        )

    @classmethod
    def build_spec_from_handler(
        cls,
        handler: AsyncConnectHandler,
        summary: str | None,
        description: str | None,
    ) -> HandlerSpec:
        return HandlerSpec(
            summary=summary,
            description=description,
            exceptions=list(cls.build_exceptions(handler)),
            ack_code=None,
            ack_body_schema=None,
            event_body_model=handler.body_model,
        )


class DisconnectHandlerBuilder(HandlerBuilder[AsyncDisconnectHandler]):
    def build_handler(self) -> AsyncDisconnectHandler:
        if self.possible_exceptions:
            raise TypeError("Disconnection handlers can not have possible exceptions")

        for parameter in self.signature.parameters.values():
            self.parse_parameter(parameter)

        if self.destinations.build_body_model() is not None:
            raise TypeError("Disconnection handlers can not have arguments")

        if self.signature.return_annotation is not None:
            raise TypeError("Disconnection handlers can not return anything")

        return AsyncDisconnectHandler(
            async_callable=self.build_async_callable(),
            marker_destinations=self.destinations.build_marker_destinations(),
        )

    @classmethod
    def build_spec_from_handler(
        cls,
        handler: AsyncDisconnectHandler,
        summary: str | None,
        description: str | None,
    ) -> HandlerSpec:
        return HandlerSpec(
            summary=summary,
            description=description,
            exceptions=[],
            ack_code=None,
            ack_body_schema=None,
            event_body_model=None,
        )


EVENT_NAME_TO_HANDLER_BUILDER: dict[str, type[HandlerBuilder[Any]]] = {
    "connect": ConnectHandlerBuilder,
    "disconnect": DisconnectHandlerBuilder,
}


def pick_handler_class_by_event_name(event_name: str) -> type[HandlerBuilder[Any]]:
    return EVENT_NAME_TO_HANDLER_BUILDER.get(event_name, EventHandlerBuilder)
