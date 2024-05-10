from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from dataclasses import dataclass, field
from typing import Any
from warnings import warn

from pydantic import BaseModel, ValidationError
from socketio.exceptions import ConnectionRefusedError  # type: ignore[import-untyped]

from tmexio.exceptions import (
    EventBodyException,
    EventException,
    UndocumentedExceptionWarning,
)
from tmexio.markers import Marker
from tmexio.packagers import CodedPackager, ErrorPackager
from tmexio.structures import ClientEvent
from tmexio.types import DataOrTuple

ExtractedMarkers = dict[Marker[Any], Any]
ParsedBody = BaseModel | None
DependencyCacheKey = Callable[..., Awaitable[Any]]
ResolvedDependencies = dict[DependencyCacheKey, Any]
KwargsIterator = Iterator[tuple[str, Any]]
Kwargs = dict[str, Any]


@dataclass()
class HandlerContext:
    stack: AsyncExitStack
    extracted_markers: ExtractedMarkers
    parsed_body: ParsedBody
    resolved_dependencies: ResolvedDependencies = field(default_factory=dict)


class KwargsBuilder:
    def __init__(
        self,
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_destinations: list[tuple[str, list[str]]],
        dependency_destinations: list[tuple[DependencyCacheKey, list[str]]],
    ) -> None:
        self.marker_destinations = marker_destinations
        self.body_destinations = body_destinations
        self.dependency_destinations = dependency_destinations

    def markers_to_kwargs(self, extracted_markers: ExtractedMarkers) -> KwargsIterator:
        for marker, parameter_names in self.marker_destinations:
            yield from ((name, extracted_markers[marker]) for name in parameter_names)

    def body_to_kwargs(self, parsed_body: BaseModel) -> KwargsIterator:
        for field_name, parameter_names in self.body_destinations:
            # TODO replace fallback with error or warning
            value = getattr(parsed_body, field_name, None)
            yield from ((name, value) for name in parameter_names)

    def dependencies_to_kwargs(
        self, resolved_dependencies: ResolvedDependencies
    ) -> KwargsIterator:
        for dependency_key, parameter_names in self.dependency_destinations:
            # TODO replace fallback with error or warning
            value = resolved_dependencies.get(dependency_key)
            yield from ((name, value) for name in parameter_names)

    def iterate_kwargs(self, context: HandlerContext) -> KwargsIterator:
        yield from self.markers_to_kwargs(context.extracted_markers)
        if context.parsed_body is not None:
            yield from self.body_to_kwargs(context.parsed_body)
        yield from self.dependencies_to_kwargs(context.resolved_dependencies)

    def build_kwargs(self, context: HandlerContext) -> Kwargs:
        return dict(self.iterate_kwargs(context))


class BaseDependency(KwargsBuilder):
    async def __call__(self, context: HandlerContext) -> Any:
        raise NotImplementedError


class ValueDependency(BaseDependency):
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_destinations: list[tuple[str, list[str]]],
        dependency_destinations: list[tuple[DependencyCacheKey, list[str]]],
    ) -> None:
        super().__init__(
            marker_destinations=marker_destinations,
            body_destinations=body_destinations,
            dependency_destinations=dependency_destinations,
        )
        self.async_callable = async_callable

    async def __call__(self, context: HandlerContext) -> Any:
        kwargs: Kwargs = self.build_kwargs(context)
        return await self.async_callable(**kwargs)


class ContextualDependency(BaseDependency):
    def __init__(
        self,
        dependency_function: Callable[..., AbstractAsyncContextManager[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_destinations: list[tuple[str, list[str]]],
        dependency_destinations: list[tuple[DependencyCacheKey, list[str]]],
    ) -> None:
        super().__init__(
            marker_destinations=marker_destinations,
            body_destinations=body_destinations,
            dependency_destinations=dependency_destinations,
        )
        self.dependency_function = dependency_function

    async def __call__(self, context: HandlerContext) -> Any:
        kwargs: Kwargs = self.build_kwargs(context)
        cm: AbstractAsyncContextManager[Any] = self.dependency_function(**kwargs)
        return await context.stack.enter_async_context(cm)


class BaseAsyncHandler(KwargsBuilder):
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
        dependency_definitions: list[tuple[DependencyCacheKey, BaseDependency]],
        dependency_destinations: list[tuple[DependencyCacheKey, list[str]]],
        possible_exceptions: set[EventException],
    ) -> None:
        super().__init__(
            marker_destinations=marker_destinations,
            body_destinations=body_destinations,
            dependency_destinations=dependency_destinations,
        )
        self.async_callable = async_callable
        self.markers_definitions = marker_definitions
        self.body_model = body_model
        self.dependency_definitions = dependency_definitions
        self.possible_exceptions = possible_exceptions

    def collect_markers(self, event: ClientEvent) -> ExtractedMarkers:
        return {marker: marker.extract(event) for marker in self.markers_definitions}

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

    async def resolve_dependencies(self, context: HandlerContext) -> None:
        for dependency_key, dependency in self.dependency_definitions:
            context.resolved_dependencies[dependency_key] = await dependency(context)

    async def run(self, markers: ExtractedMarkers, body: ParsedBody) -> Any:
        async with AsyncExitStack() as stack:
            handler_context = HandlerContext(
                stack=stack,
                extracted_markers=markers,
                parsed_body=body,
            )
            await self.resolve_dependencies(handler_context)

            kwargs: Kwargs = self.build_kwargs(handler_context)
            return await self.async_callable(**kwargs)

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        raise NotImplementedError


class AsyncEventHandler(BaseAsyncHandler):
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_definitions: list[Marker[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_model: type[BaseModel] | None,
        body_destinations: list[tuple[str, list[str]]],
        dependency_definitions: list[tuple[DependencyCacheKey, BaseDependency]],
        dependency_destinations: list[tuple[DependencyCacheKey, list[str]]],
        possible_exceptions: set[EventException],
        ack_packager: CodedPackager[Any],
    ) -> None:
        super().__init__(
            async_callable=async_callable,
            marker_definitions=marker_definitions,
            marker_destinations=marker_destinations,
            body_model=body_model,
            body_destinations=body_destinations,
            dependency_definitions=dependency_definitions,
            dependency_destinations=dependency_destinations,
            possible_exceptions=possible_exceptions,
        )
        self.ack_packager = ack_packager

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        try:
            body = self.parse_body(event)
        except EventException as e:
            return self.error_packager.pack_data(e)
        markers: ExtractedMarkers = self.collect_markers(event)

        try:
            result = await self.run(markers=markers, body=body)
        except EventException as e:
            if e not in self.possible_exceptions:
                warn(UndocumentedExceptionWarning(e))
            return self.error_packager.pack_data(e)

        # TODO error handling on ack packing for clarity
        return self.ack_packager.pack_data(result)


class AsyncConnectHandler(BaseAsyncHandler):
    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        # Here `event.args` has at most one argument

        try:
            body = self.parse_body(event)
        except EventException as e:
            raise ConnectionRefusedError(self.error_packager.pack_data(e))
        markers: ExtractedMarkers = self.collect_markers(event)

        try:
            await self.run(markers=markers, body=body)
        except EventException as e:
            if e not in self.possible_exceptions:
                warn(UndocumentedExceptionWarning(e))
            raise ConnectionRefusedError(self.error_packager.pack_data(e))

        return None


class AsyncDisconnectHandler(BaseAsyncHandler):
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_definitions: list[Marker[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        dependency_definitions: list[tuple[DependencyCacheKey, BaseDependency]],
        dependency_destinations: list[tuple[DependencyCacheKey, list[str]]],
    ) -> None:
        super().__init__(
            async_callable=async_callable,
            marker_definitions=marker_definitions,
            marker_destinations=marker_destinations,
            body_model=None,
            body_destinations=[],
            dependency_definitions=dependency_definitions,
            dependency_destinations=dependency_destinations,
            possible_exceptions=set(),
        )

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        # Here `event.args` is always empty
        markers: ExtractedMarkers = self.collect_markers(event)
        await self.run(markers=markers, body=None)
        return None
