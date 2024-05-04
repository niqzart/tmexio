from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import Parameter, Signature, iscoroutinefunction, signature
from logging import Logger
from typing import Annotated, Any, Literal, get_args, get_origin

import socketio  # type: ignore[import-untyped]
from asgiref.sync import sync_to_async
from pydantic import BaseModel, create_model
from socketio.packet import Packet  # type: ignore[import-untyped]

from tmexio import markers, packagers
from tmexio.event_handlers import AsyncEventHandler
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


class HandlerBuilder:
    type_to_marker: dict[type[Any], markers.Marker[Any]] = {
        AsyncServer: markers.AsyncServerMarker(),
        AsyncSocket: markers.AsyncSocketMarker(),
        ClientEvent: markers.ClientEventMarker(),
    }

    def __init__(self, function: Callable[..., Any]) -> None:
        self.function = function
        self.signature: Signature = signature(function)
        self.destinations = Destinations()

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

    def parse_return_annotation(self) -> packagers.BasePackager[Any]:
        annotation = self.signature.return_annotation
        args = get_args(annotation)

        if annotation is None:
            return packagers.NoContentPackager()
        elif (  # noqa: WPS337
            get_origin(annotation) is Annotated
            and len(args) == 2
            and isinstance(args[1], packagers.BasePackager)
        ):
            return args[1]
        return packagers.PydanticPackager(annotation)

    def build_handler(self) -> AsyncEventHandler:
        for parameter in self.signature.parameters.values():
            self.parse_parameter(parameter)
        ack_packager = self.parse_return_annotation()

        if iscoroutinefunction(self.function):
            async_callable = self.function
        elif callable(self.function):
            async_callable = sync_to_async(self.function)
        else:
            raise TypeError("Handler is not callable")

        return AsyncEventHandler(
            async_callable=async_callable,
            marker_destinations=self.destinations.build_marker_destinations(),
            body_model=self.destinations.build_body_model(),
            body_destinations=self.destinations.build_body_destinations(),
            ack_packager=ack_packager,
        )


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
            handler = HandlerBuilder(function=function).build_handler()
            self.add_handler(
                event_name=event_name,
                handler=handler,
                spec=HandlerSpec(
                    summary=summary,
                    description=description,
                    exceptions=exceptions or [],
                    body_model=handler.body_model,
                ),
            )
            return function

        return on_inner

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
        async def add_handler_inner(sid: str, *args: DataType) -> DataOrTuple:
            return await handler(ClientEvent(self.server, sid, *args))

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
