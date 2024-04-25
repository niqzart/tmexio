from collections.abc import Callable
from typing import Any, Protocol

AnyKwargs = dict[str, Any]
AnyCallable = Callable[..., Any]

DataType = None | int | str | bytes | dict["DataType", "DataType"] | list["DataType"]
DataOrTuple = DataType | tuple[DataType, ...]


class AsyncEventHandler(Protocol):
    async def __call__(self, sid: str, *args: DataType) -> DataOrTuple:
        pass
