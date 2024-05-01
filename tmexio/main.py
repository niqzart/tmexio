from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import Parameter, Signature, iscoroutinefunction, signature
from logging import Logger
from typing import Annotated, Any, Literal, get_args, get_origin

from asgiref.sync import sync_to_async
from socketio import AsyncManager, AsyncServer  # type: ignore[import-untyped]
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio.exceptions import EventException
from tmexio.specs import HandlerSpec
from tmexio.types import DataOrTuple, DataType


class Sid(str):
    pass


class AsyncEventHandler:
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        sid_destinations: list[str],
    ) -> None:
        self.async_callable = async_callable
        self.sid_destinations = sid_destinations

    async def __call__(self, sid: str, *args: DataType) -> DataOrTuple:
        kwargs = {name: sid for name in self.sid_destinations}
        return await self.async_callable(*args, **kwargs)  # type: ignore[no-any-return]
        # TODO pack result from Any to DataOrTuple


class HandlerBuilder:
    def __init__(
        self,
        function: Callable[..., Any],
        summary: str | None,
        description: str | None,
        exceptions: list[EventException],
    ) -> None:
        self.function = function
        self.signature: Signature = signature(function)
        self.sid_destinations: list[str] = []

        self.spec = HandlerSpec(
            summary=summary,
            description=description,
            exceptions=exceptions,
        )

    def parse_parameter(self, parameter: Parameter) -> None:
        # TODO `if parameter.kind != parameter.POSITIONAL_OR_KEYWORD:`
        #  `raise TypeError(f"{parameter.kind} parameters are not supported")`

        if get_origin(parameter.annotation) is Annotated:
            args = get_args(parameter.annotation)
            if len(args) == 2:
                pass  # TODO
        elif parameter.annotation == Sid:
            self.sid_destinations.append(parameter.name)
        # TODO arguments

    def parse_return_annotation(self) -> None:
        pass  # TODO self.signature.return_annotation

    def parse_signature(self) -> None:
        for parameter in self.signature.parameters.values():
            self.parse_parameter(parameter)
        self.parse_return_annotation()

    def build_handler(self) -> AsyncEventHandler:
        self.parse_signature()

        if iscoroutinefunction(self.function):
            async_callable = self.function
        elif callable(self.function):
            async_callable = sync_to_async(self.function)
        else:
            raise TypeError("Handler is not callable")

        return AsyncEventHandler(async_callable, self.sid_destinations)

    def build_spec(self) -> HandlerSpec:
        return self.spec


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
        def on_inner(function: Callable[..., Any]) -> Callable[..., Any]:
            handler_builder = HandlerBuilder(
                function=function,
                summary=summary,
                description=description,
                exceptions=exceptions or [],
            )
            self.add_handler(
                event_name=event_name,
                handler=handler_builder.build_handler(),
                spec=handler_builder.build_spec(),
            )
            return function

        return on_inner

    def include_router(self, router: EventRouter) -> None:
        for event_name, (handler, spec) in router.event_handlers.items():
            self.add_handler(event_name, handler, spec)


class TMEXIO(EventRouter):
    def __init__(
        self,
        client_manager: AsyncManager | None = None,
        logger: bool | Logger = False,
        engineio_logger: bool | Logger = False,
        namespaces: Literal["*"] | list[str] | None = None,
        always_connect: bool = False,
        serializer: type[Packet] = Packet,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.backend = AsyncServer(
            client_manager=client_manager,
            logger=logger,
            namespaces=namespaces,
            always_connect=always_connect,
            serializer=serializer,
            engineio_logger=engineio_logger,
            **kwargs,
        )

    def add_handler(
        self,
        event_name: str,
        handler: AsyncEventHandler,
        spec: HandlerSpec,
    ) -> None:
        # TODO support for multiple namespaces
        self.backend.on(
            event=event_name,
            # coroutine check in socketio doesn't check the __call__ method
            handler=handler.__call__,  # noqa: WPS609
            namespace="/",
        )
        super().add_handler(event_name, handler, spec)
