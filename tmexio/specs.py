from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, TypeAdapter

from tmexio.exceptions import EventException


@dataclass()
class AckSpec:
    code: int
    model: TypeAdapter[Any] | type[BaseModel] | None


@dataclass()
class HandlerSpec:
    summary: str | None
    description: str | None
    tags: list[str]
    body_model: TypeAdapter[Any] | type[BaseModel] | None
    ack: AckSpec | None
    exceptions: list[EventException]


@dataclass()
class EmitterSpec:
    summary: str | None
    description: str | None
    tags: list[str]
    body_model: TypeAdapter[Any] | type[BaseModel]
