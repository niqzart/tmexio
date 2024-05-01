from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any, Protocol

AnyKwargs = dict[str, Any]
AnyCallable = Callable[..., Any]

DataType = None | int | str | bytes | dict["DataType", "DataType"] | list["DataType"]
DataOrTuple = DataType | tuple[DataType, ...]

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class ASGIAppProtocol(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        pass
