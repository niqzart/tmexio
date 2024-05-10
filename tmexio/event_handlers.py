from __future__ import annotations

from abc import ABC
from collections.abc import Awaitable, Callable, Iterator
from typing import Any, cast
from warnings import warn

from pydantic import BaseModel, ValidationError
from socketio.exceptions import ConnectionRefusedError  # type: ignore[import-untyped]

from tmexio.exceptions import EventException
from tmexio.markers import Marker
from tmexio.packagers import CodedPackager, ErrorPackager
from tmexio.structures import ClientEvent
from tmexio.types import DataOrTuple, DataType

ExtractedMarkers = dict[Marker[Any], Any]
ParsedBody = BaseModel | None
KwargsIterator = Iterator[tuple[str, Any]]
Kwargs = dict[str, Any]


class BaseAsyncHandler:
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_definitions: list[Marker[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
    ) -> None:
        self.async_callable = async_callable
        self.markers_definitions = marker_definitions
        self.marker_destinations = marker_destinations

    def collect_markers(self, event: ClientEvent) -> Iterator[tuple[Marker[Any], Any]]:
        yield from (
            (marker, marker.extract(event)) for marker in self.markers_definitions
        )

    def markers_to_kwargs(self, markers: ExtractedMarkers) -> KwargsIterator:
        for marker, parameter_names in self.marker_destinations:
            yield from ((name, markers[marker]) for name in parameter_names)

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        raise NotImplementedError


class EventBodyException(EventException):
    def __init__(self, validation_error: ValidationError) -> None:
        super().__init__(code=422, ack_body=cast(DataType, validation_error.errors()))


class UndocumentedExceptionWarning(RuntimeWarning):
    def __init__(self, exception: EventException) -> None:
        super().__init__(f"Exception {exception} is not documented, but was raised")


class BaseAsyncHandlerWithArguments(BaseAsyncHandler, ABC):
    error_packager: ErrorPackager = ErrorPackager()

    zero_arguments_expected_error = EventException(422, "Event expects zero arguments")
    one_argument_expected_error = EventException(422, "Event expects one argument")

    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_definitions: list[Marker[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_model: type[BaseModel] | None,
        body_destinations: list[tuple[str, list[str]]],
        possible_exceptions: set[EventException],
    ) -> None:
        super().__init__(
            async_callable=async_callable,
            marker_definitions=marker_definitions,
            marker_destinations=marker_destinations,
        )
        self.body_model = body_model
        self.body_destinations = body_destinations
        self.possible_exceptions = possible_exceptions

    def parse_body(self, event: ClientEvent) -> ParsedBody:
        if self.body_model is None:
            if len(event.args) != 0 and event.args[0] is not None:
                raise self.zero_arguments_expected_error
            return None
        else:
            if len(event.args) != 1:
                raise self.one_argument_expected_error

            try:
                return self.body_model.model_validate(event.args[0])
            except ValidationError as e:
                raise EventBodyException(e)

    def body_to_kwargs(self, body: ParsedBody) -> KwargsIterator:
        if body is None:
            return

        for field_name, parameter_names in self.body_destinations:
            # TODO replace fallback with error or warning
            value = getattr(body, field_name, None)
            yield from ((name, value) for name in parameter_names)

    def build_kwargs(
        self, markers: ExtractedMarkers, body: ParsedBody
    ) -> KwargsIterator:
        yield from self.markers_to_kwargs(markers)
        yield from self.body_to_kwargs(body)


class AsyncEventHandler(BaseAsyncHandlerWithArguments):
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_definitions: list[Marker[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_model: type[BaseModel] | None,
        body_destinations: list[tuple[str, list[str]]],
        possible_exceptions: set[EventException],
        ack_packager: CodedPackager[Any],
    ) -> None:
        super().__init__(
            async_callable=async_callable,
            marker_definitions=marker_definitions,
            marker_destinations=marker_destinations,
            body_model=body_model,
            body_destinations=body_destinations,
            possible_exceptions=possible_exceptions,
        )
        self.ack_packager = ack_packager

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        try:
            body = self.parse_body(event)
        except EventException as e:
            return self.error_packager.pack_data(e)

        markers: ExtractedMarkers = dict(self.collect_markers(event))

        kwargs: Kwargs = dict(self.build_kwargs(markers, body))

        try:
            result = await self.async_callable(**kwargs)
        except EventException as e:
            if e not in self.possible_exceptions:
                warn(UndocumentedExceptionWarning(e))
            return self.error_packager.pack_data(e)

        # TODO error handling on ack packing for clarity
        return self.ack_packager.pack_data(result)


class AsyncConnectHandler(BaseAsyncHandlerWithArguments):
    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        # Here `event.args` has at most one argument

        try:
            body = self.parse_body(event)
        except EventException as e:
            raise ConnectionRefusedError(self.error_packager.pack_data(e))

        markers: ExtractedMarkers = dict(self.collect_markers(event))

        kwargs: Kwargs = dict(self.build_kwargs(markers, body))

        try:
            await self.async_callable(**kwargs)
        except EventException as e:
            if e not in self.possible_exceptions:
                warn(UndocumentedExceptionWarning(e))
            raise ConnectionRefusedError(self.error_packager.pack_data(e))

        return None


class AsyncDisconnectHandler(BaseAsyncHandler):
    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        # Here `event.args` is always empty
        markers: ExtractedMarkers = dict(self.collect_markers(event))
        kwargs: Kwargs = dict(self.markers_to_kwargs(markers))
        await self.async_callable(**kwargs)
        return None
