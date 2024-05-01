from collections.abc import Callable
from typing import Any

AnyKwargs = dict[str, Any]
AnyCallable = Callable[..., Any]

DataType = None | int | str | bytes | dict["DataType", "DataType"] | list["DataType"]
DataOrTuple = DataType | tuple[DataType, ...]
