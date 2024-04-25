from collections.abc import Callable
from logging import Logger
from typing import Any, Literal

from socketio import AsyncManager, AsyncServer  # type: ignore[import-untyped]
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio.specs import HandlerSpec
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
        self.handler_specs: list[HandlerSpec] = []

    def add_handler(self, handler: AsyncEventHandler, spec: HandlerSpec) -> None:
        # TODO support for multiple namespaces
        self.backend.on(event=spec.event_name, handler=handler, namespace="/")
        self.handler_specs.append(spec)

    def on(
        self,
        event_name: str,
        summary: str | None = None,
        description: str | None = None,
    ) -> Callable[[AsyncEventHandler], AsyncEventHandler]:
        def on_inner(handler: AsyncEventHandler) -> AsyncEventHandler:
            self.add_handler(
                handler,
                spec=HandlerSpec(
                    event_name=event_name,
                    summary=summary,
                    description=description,
                ),
            )
            return handler

        return on_inner
