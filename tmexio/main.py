from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutinefunction
from logging import Logger
from typing import Any, Literal

from asgiref.sync import sync_to_async
from socketio import AsyncManager, AsyncServer  # type: ignore[import-untyped]
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio.exceptions import EventException
from tmexio.specs import HandlerSpec
from tmexio.types import AsyncEventHandler, DataOrTuple, DataType


class HandlerBuilder:
    def __init__(
        self,
        function: Callable[..., Any],
        summary: str | None,
        description: str | None,
        exceptions: list[EventException],
    ) -> None:
        self.function = function
        self.spec = HandlerSpec(
            summary=summary,
            description=description,
            exceptions=exceptions,
        )

    def build_handler(self) -> AsyncEventHandler:
        if iscoroutinefunction(self.function):
            async_callable = self.function
        elif callable(self.function):
            async_callable = sync_to_async(self.function)
        else:
            raise TypeError("Handler is not callable")

        async def handler(sid: str, *args: DataType) -> DataOrTuple:
            # TODO pack result from Any to DataOrTuple
            return await async_callable(sid, *args)  # type: ignore[no-any-return]

        return handler

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
        self.backend.on(event=event_name, handler=handler, namespace="/")
        super().add_handler(event_name, handler, spec)
