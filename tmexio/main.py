from __future__ import annotations

from collections.abc import Callable
from logging import Logger
from typing import Any, Literal

from socketio import AsyncManager, AsyncServer  # type: ignore[import-untyped]
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio.specs import HandlerSpec
from tmexio.types import AsyncEventHandler


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
    ) -> Callable[[AsyncEventHandler], AsyncEventHandler]:
        def on_inner(handler: AsyncEventHandler) -> AsyncEventHandler:
            self.add_handler(
                event_name=event_name,
                handler=handler,
                spec=HandlerSpec(
                    summary=summary,
                    description=description,
                ),
            )
            return handler

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
