from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from tmexio.exceptions import EventException


@dataclass()
class HandlerSpec:
    summary: str | None
    description: str | None
    tags: list[str]
    event_body_model: type[BaseModel] | None
    ack_code: int | None
    ack_body_schema: dict[str, Any] | None
    exceptions: list[EventException]
