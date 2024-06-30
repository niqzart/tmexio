from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from logging import Logger
from typing import Any, Literal

import socketio  # type: ignore[import-untyped]
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio.event_handlers import BaseAsyncHandler
from tmexio.exceptions import EventException
from tmexio.handler_builders import Depends, pick_handler_class_by_event_name
from tmexio.markers import ServerEmitterMarker
from tmexio.server import AsyncServer
from tmexio.specs import EmitterSpec, HandlerSpec
from tmexio.structures import ClientEvent
from tmexio.types import AnyCallable, ASGIAppProtocol, DataOrTuple, DataType


def register_dependency(
    exceptions: list[EventException] | None = None,
    dependencies: list[Depends] | None = None,
) -> Callable[[AnyCallable], Depends]:
    def register_dependency_inner(function: AnyCallable) -> Depends:
        return Depends(
            function=function,
            exceptions=exceptions or [],
            dependencies=dependencies or [],
        )

    return register_dependency_inner


class EventRouter:
    def __init__(
        self,
        *,
        dependencies: list[Depends] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.event_handlers: dict[str, tuple[BaseAsyncHandler, HandlerSpec]] = {}
        self.event_emitters: dict[str, EmitterSpec] = {}
        self.default_dependencies = dependencies or []
        self.default_tags = tags or []
        # TODO these dependencies do not apply to included routers

    def add_emitter(self, event_name: str, spec: EmitterSpec) -> None:
        spec.tags = [*spec.tags, *self.default_tags]
        self.event_emitters[event_name] = spec

    def register_server_emitter(
        self,
        body_annotation: Any,
        event_name: str,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> ServerEmitterMarker[Any]:
        marker: ServerEmitterMarker[Any] = ServerEmitterMarker(
            body_annotation=body_annotation, event_name=event_name
        )
        self.add_emitter(
            event_name=event_name,
            spec=EmitterSpec(
                summary=summary,
                description=description,
                tags=tags or [],
                body_model=marker.adapter,
            ),
        )
        return marker

    def add_handler(
        self,
        event_name: str,
        handler: BaseAsyncHandler,
        spec: HandlerSpec,
    ) -> None:
        spec.tags = [*spec.tags, *self.default_tags]
        self.event_handlers[event_name] = handler, spec

    def on(
        self,
        event_name: str,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        exceptions: list[EventException] | None = None,
        dependencies: list[Depends] | None = None,
        server_summary: str | None = None,
        server_description: str | None = None,
        server_tags: list[str] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        handler_builder_class = pick_handler_class_by_event_name(event_name)

        def on_inner(function: Callable[..., Any]) -> Callable[..., Any]:
            handler_builder = handler_builder_class(
                event_name=event_name,
                function=function,
                possible_exceptions=exceptions or [],
                sub_dependencies=self.default_dependencies + (dependencies or []),
            )
            handler = handler_builder.build_handler()

            self.add_handler(
                event_name=event_name,
                handler=handler,
                spec=handler_builder_class.build_spec_from_handler(
                    handler=handler,
                    summary=summary,
                    tags=tags or [],
                    description=description,
                ),
            )

            if handler_builder.context.duplex_emitter_model is not None:
                self.add_emitter(
                    event_name=event_name,
                    spec=EmitterSpec(
                        summary=server_summary or summary,
                        description=server_description or description,
                        tags=server_tags or tags or [],
                        body_model=handler_builder.context.duplex_emitter_model,
                    ),
                )

            return function

        return on_inner

    def on_connect(
        self,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
        dependencies: list[Depends] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.on(
            event_name="connect",
            summary=summary,
            description=description,
            exceptions=exceptions,
            dependencies=dependencies,
        )

    def on_disconnect(
        self,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
        dependencies: list[Depends] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.on(
            event_name="disconnect",
            summary=summary,
            description=description,
            exceptions=exceptions,
            dependencies=dependencies,
        )

    def on_other(
        self,
        summary: str | None = None,
        description: str | None = None,
        exceptions: list[EventException] | None = None,
        dependencies: list[Depends] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.on(
            event_name="*",
            summary=summary,
            description=description,
            exceptions=exceptions,
            dependencies=dependencies,
        )

    def include_router(self, router: EventRouter) -> None:
        for event_name, (handler, handler_spec) in router.event_handlers.items():
            self.add_handler(event_name, handler, deepcopy(handler_spec))
        for event_name, emitter_spec in router.event_emitters.items():
            self.add_emitter(event_name, deepcopy(emitter_spec))


class TMEXIO(EventRouter):
    def __init__(
        self,
        client_manager: socketio.AsyncManager | None = None,
        logger: bool | Logger = False,
        engineio_logger: bool | Logger = False,
        namespaces: Literal["*"] | list[str] | None = None,
        always_connect: bool = False,
        serializer: type[Packet] = Packet,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(tags=tags)
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
        handler: BaseAsyncHandler,
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
