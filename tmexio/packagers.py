from typing import Any, Generic, TypeVar, cast

from pydantic import TypeAdapter

from tmexio.exceptions import EventException
from tmexio.types import DataOrTuple, DataType

PackedType = TypeVar("PackedType")


class BasePackager(Generic[PackedType]):
    def pack_data(self, data: PackedType) -> DataOrTuple:
        raise NotImplementedError


class ErrorPackager(BasePackager[EventException]):
    def pack_data(self, data: EventException) -> DataOrTuple:
        return data.code, data.ack_body


class CodedPackager(Generic[PackedType], BasePackager[PackedType]):
    def __init__(self, code: int = 200) -> None:
        self.code = code

    def pack_body(self, data: PackedType) -> DataType:
        raise NotImplementedError

    def pack_data(self, data: PackedType) -> DataOrTuple:
        return self.code, self.pack_body(data)

    def body_json_schema(self) -> dict[str, Any]:
        raise NotImplementedError


class NoContentPackager(CodedPackager[None]):
    def __init__(self) -> None:
        super().__init__(code=204)

    def pack_body(self, data: None) -> DataType:
        return None

    def body_json_schema(self) -> dict[str, Any]:
        return {"type": "null"}


class PydanticPackager(CodedPackager[Any]):
    def __init__(self, annotation: Any, code: int = 200) -> None:
        super().__init__(code=code)
        self.adapter = TypeAdapter(annotation)

    def pack_body(self, data: Any) -> DataType:
        validated_data = self.adapter.validate_python(data, from_attributes=True)
        return cast(
            DataType,
            self.adapter.dump_python(validated_data, mode="json", by_alias=True),
        )

    def body_json_schema(self) -> dict[str, Any]:
        return self.adapter.json_schema()
