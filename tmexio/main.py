from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from inspect import Parameter, Signature, iscoroutinefunction, signature
from logging import Logger
from typing import Annotated, Any, Generic, Literal, TypeVar, get_args, get_origin

import socketio  # type: ignore[import-untyped]
from asgiref.sync import sync_to_async
from pydantic import BaseModel, create_model
from socketio.packet import Packet  # type: ignore[import-untyped]

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
from tmexio.types import ASGIAppProtocol, DataOrTuple, DataType


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


class EventRouter:
    def __init__(self) -> None:
        self.event_handlers: dict[str, tuple[AsyncEventHandler, HandlerSpec]] = {}

    def add_handler(
        self,
        event_name: str,
        handler: AsyncEventHandler,
        spec: HandlerSpec,
    ) -> None:
        self.event_handlers[event_name] = handler, spec

    def on(
        self,
        event_name: str,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        handler_builder_class = pick_handler_class_by_event_name(event_name)

        def on_inner(function: Callable[..., Any]) -> Callable[..., Any]:
            handler = handler_builder_class(
                function=function,
                possible_exceptions=exceptions or [],
            ).build_handler()
            self.add_handler(
                event_name=event_name,
                handler=handler,
                spec=handler_builder_class.build_spec_from_handler(
                    handler=handler,
                    summary=summary,
                    description=description,
                ),
            )
            return function

        return on_inner

    def on_connect(
        self,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.on(
            event_name="connect",
            summary=summary,
            description=description,
            exceptions=exceptions,
        )

    def on_disconnect(
        self,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.on(
            event_name="disconnect",
            summary=summary,
            description=description,
            exceptions=exceptions,
        )

    def on_other(
        self,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.on(
            event_name="*",
            summary=summary,
            description=description,
            exceptions=exceptions,
        )

    def include_router(self, router: EventRouter) -> None:
        for event_name, (handler, spec) in router.event_handlers.items():
            self.add_handler(event_name, handler, spec)


class TMEXIO(EventRouter):
    def __init__(
        self,
        client_manager: socketio.AsyncManager | None = None,
        logger: bool | Logger = False,
        engineio_logger: bool | Logger = False,
        namespaces: Literal["*"] | list[str] | None = None,
        always_connect: bool = False,
        serializer: type[Packet] = Packet,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.backend = socketio.AsyncServer(
            client_manager=client_manager,
            logger=logger,
            namespaces=namespaces,
            always_connect=always_connect,
            serializer=serializer,
            engineio_logger=engineio_logger,
            **kwargs,
        )
        self.server = AsyncServer(backend=self.backend)

    def add_handler(
        self,
        event_name: str,
        handler: AsyncEventHandler,
        spec: HandlerSpec,
    ) -> None:
        super().add_handler(event_name=event_name, handler=handler, spec=spec)

        if event_name == "connect":

            async def add_handler_inner(
                sid: str, _environ: Any, auth: DataType = None
            ) -> DataOrTuple:
                return await handler(ClientEvent(self.server, "connect", sid, auth))

        elif event_name == "disconnect":

            async def add_handler_inner(sid: str) -> DataOrTuple:  # type: ignore[misc]
                return await handler(ClientEvent(self.server, "disconnect", sid))

        elif event_name == "*":

            async def add_handler_inner(  # type: ignore[misc]
                event: str, sid: str, *args: DataType
            ) -> DataOrTuple:
                return await handler(ClientEvent(self.server, event, sid, *args))

        else:

            async def add_handler_inner(sid: str, *args: DataType) -> DataOrTuple:  # type: ignore[misc]
                return await handler(ClientEvent(self.server, event_name, sid, *args))

        self.backend.on(
            event=event_name,
            handler=add_handler_inner,
            namespace="/",  # TODO support for multiple namespaces
        )

    def build_asgi_app(
        self,
        other_asgi_app: ASGIAppProtocol | None = None,
        static_files: dict[str, str] | None = None,
        socketio_path: str | None = "socket.io",
        on_startup: Callable[[], Awaitable[None]] | None = None,
        on_shutdown: Callable[[], Awaitable[None]] | None = None,
    ) -> ASGIAppProtocol:
        return socketio.ASGIApp(  # type: ignore[no-any-return]
            socketio_server=self.backend,
            other_asgi_app=other_asgi_app,
            static_files=static_files,
            socketio_path=socketio_path,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        )
