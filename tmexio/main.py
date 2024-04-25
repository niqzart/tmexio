from collections.abc import Callable
from logging import Logger
from typing import Any, Literal

from socketio import AsyncManager, AsyncServer  # type: ignore[import-untyped]
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio.types import AsyncEventHandler


class TMEXIO:
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
    ) -> None:
        # TODO support for multiple namespaces
        self.backend.on(event=event_name, handler=handler, namespace="/")

    def on(
        self,
        event_name: str,
        # TODO summary: str | None = None,
        # TODO description: str | None = None,
    ) -> Callable[[AsyncEventHandler], AsyncEventHandler]:
        def on_inner(handler: AsyncEventHandler) -> AsyncEventHandler:
            self.add_handler(event_name, handler)
            return handler

        return on_inner
