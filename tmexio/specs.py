from dataclasses import dataclass

from tmexio.exceptions import EventException
from tmexio.types import ModelType


@dataclass()
class AckSpec:
    code: int
    model: ModelType | None


@dataclass()
class HandlerSpec:
    summary: str | None
    description: str | None
    tags: list[str]
    body_model: ModelType | None
    ack: AckSpec | None
    exceptions: list[EventException]


@dataclass()
class EmitterSpec:
    summary: str | None
    description: str | None
    tags: list[str]
    body_model: ModelType
