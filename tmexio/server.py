from contextlib import AbstractAsyncContextManager
from typing import Any, Generic, Literal, TypeVar, cast

import socketio  # type: ignore[import-untyped]
from pydantic import TypeAdapter

from tmexio.types import CallbackProtocol, DataOrTuple, DataType


class AsyncServer:
    def __init__(self, backend: socketio.AsyncServer) -> None:
        self.backend = backend

    async def emit(
        self,
        event: str,
        # TODO proper support for pydantic `data`
        data: DataOrTuple | dict[str, Any],
        target: str | None = None,
        skip_sid: str | None = None,
        namespace: str | None = None,
        callback: CallbackProtocol | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.backend.emit(
            event=event,
            data=data,
            to=target,
            skip_sid=skip_sid,
            namespace=namespace,
            callback=callback,
            ignore_queue=ignore_queue,
        )

    async def send(
        self,
        data: DataOrTuple,
        target: str | None = None,
        skip_sid: str | None = None,
        namespace: str | None = None,
        callback: CallbackProtocol | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.backend.send(
            data=data,
            to=target,
            skip_sid=skip_sid,
            namespace=namespace,
            callback=callback,
            ignore_queue=ignore_queue,
        )

    async def call(
        self,
        event: str,
        data: DataOrTuple,
        sid: str,
        namespace: str | None = None,
        timeout: int = 60,
        ignore_queue: bool = False,
    ) -> DataOrTuple:
        return cast(
            DataOrTuple,
            await self.backend.call(
                event=event,
                data=data,
                sid=sid,
                namespace=namespace,
                timeout=timeout,
                ignore_queue=ignore_queue,
            ),
        )

    def get_environ(self, sid: str, namespace: str | None = None) -> dict[str, Any]:
        return cast(dict[str, Any], self.backend.get_environ(sid, namespace))

    async def get_session(
        self,
        sid: str,
        namespace: str | None = None,
    ) -> dict[Any, Any]:
        return cast(
            dict[Any, Any],
            await self.backend.get_session(sid=sid, namespace=namespace),
        )

    async def save_session(
        self,
        sid: str,
        session: dict[Any, Any],
        namespace: str | None = None,
    ) -> None:
        await self.backend.save_session(sid=sid, session=session, namespace=namespace)

    def session(
        self,
        sid: str,
        namespace: str | None = None,
    ) -> AbstractAsyncContextManager[dict[Any, Any]]:
        return cast(
            AbstractAsyncContextManager[dict[Any, Any]],
            self.backend.session(sid=sid, namespace=namespace),
        )

    def transport(self, sid: str) -> Literal["polling", "webserver"]:
        return cast(Literal["polling", "webserver"], self.backend.transport(sid))

    async def enter_room(
        self, sid: str, room: str, namespace: str | None = None
    ) -> None:
        await self.backend.enter_room(sid=sid, room=room, namespace=namespace)

    async def leave_room(
        self, sid: str, room: str, namespace: str | None = None
    ) -> None:
        await self.backend.leave_room(sid=sid, room=room, namespace=namespace)

    def rooms(self, sid: str, namespace: str | None = None) -> list[str]:
        return cast(list[str], self.backend.rooms(sid=sid, namespace=namespace))

    async def close_room(self, room: str, namespace: str | None = None) -> None:
        await self.backend.close_room(room=room, namespace=namespace)

    async def disconnect(
        self,
        sid: str,
        namespace: str | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.backend.disconnect(
            sid=sid,
            namespace=namespace,
            ignore_queue=ignore_queue,
        )


class AsyncSocket:
    def __init__(self, server: AsyncServer, sid: str) -> None:
        self.server = server
        self.sid = sid

    async def emit(
        self,
        event: str,
        # TODO proper support for pydantic `data`
        data: DataType | tuple[DataType, ...] | dict[str, Any],
        target: str | None = None,
        skip_sid: str | None = None,
        exclude_self: bool = False,
        namespace: str | None = None,
        callback: CallbackProtocol | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.server.emit(
            event=event,
            data=data,
            target=target,
            skip_sid=skip_sid or (self.sid if exclude_self else None),
            namespace=namespace,
            callback=callback,
            ignore_queue=ignore_queue,
        )

    async def send(
        self,
        data: DataOrTuple,
        target: str | None = None,
        skip_sid: str | None = None,
        exclude_self: bool = False,
        namespace: str | None = None,
        callback: CallbackProtocol | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.server.send(
            data=data,
            target=target,
            skip_sid=skip_sid or self.sid if exclude_self else None,
            namespace=namespace,
            callback=callback,
            ignore_queue=ignore_queue,
        )

    async def call(
        self,
        event: str,
        data: DataType | tuple[DataType, ...],
        namespace: str | None = None,
        timeout: int = 60,
        ignore_queue: bool = False,
    ) -> DataOrTuple:
        return await self.server.call(
            event=event,
            data=data,
            sid=self.sid,
            namespace=namespace,
            timeout=timeout,
            ignore_queue=ignore_queue,
        )

    def get_environ(self, namespace: str | None = None) -> dict[str, Any]:
        return self.server.get_environ(self.sid, namespace)

    async def get_session(self, namespace: str | None = None) -> dict[Any, Any]:
        return await self.server.get_session(sid=self.sid, namespace=namespace)

    async def save_session(
        self,
        session: dict[Any, Any],
        namespace: str | None = None,
    ) -> None:
        await self.server.save_session(
            sid=self.sid, session=session, namespace=namespace
        )

    def session(
        self,
        namespace: str | None = None,
    ) -> AbstractAsyncContextManager[dict[Any, Any]]:
        return self.server.session(sid=self.sid, namespace=namespace)

    def transport(self) -> Literal["polling", "webserver"]:
        return self.server.transport(self.sid)

    async def enter_room(self, room: str, namespace: str | None = None) -> None:
        await self.server.enter_room(sid=self.sid, room=room, namespace=namespace)

    async def leave_room(self, room: str, namespace: str | None = None) -> None:
        await self.server.leave_room(sid=self.sid, room=room, namespace=namespace)

    def rooms(self, namespace: str | None = None) -> list[str]:
        return self.server.rooms(sid=self.sid, namespace=namespace)

    async def close_room(self, room: str, namespace: str | None = None) -> None:
        await self.server.close_room(room=room, namespace=namespace)

    async def disconnect(
        self,
        namespace: str | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.server.disconnect(
            sid=self.sid,
            namespace=namespace,
            ignore_queue=ignore_queue,
        )


T = TypeVar("T")


class Emitter(Generic[T]):
    def __init__(
        self,
        server: AsyncServer,
        event_name: str,
        adapter: TypeAdapter[T],
    ) -> None:
        self.server = server
        self.event_name = event_name
        self.adapter = adapter

    def dump_data(self, data: T) -> Any:
        return self.adapter.dump_python(data, mode="json")

    async def emit(
        self,
        data: T,
        target: str | None = None,
        skip_sid: str | None = None,
        namespace: str | None = None,
        callback: CallbackProtocol | None = None,
        ignore_queue: bool = False,
    ) -> None:
        await self.server.emit(
            event=self.event_name,
            data=self.dump_data(data),
            target=target,
            skip_sid=skip_sid,
            namespace=namespace,
            callback=callback,
            ignore_queue=ignore_queue,
        )

    async def call(
        self,
        data: T,
        sid: str,
        namespace: str | None = None,
        timeout: int = 60,
        ignore_queue: bool = False,
    ) -> DataOrTuple:
        return await self.server.call(
            event=self.event_name,
            data=self.dump_data(data),
            sid=sid,
            namespace=namespace,
            timeout=timeout,
            ignore_queue=ignore_queue,
        )
