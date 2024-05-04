from dataclasses import dataclass

from pydantic import BaseModel

from tmexio.exceptions import EventException


@dataclass()
class HandlerSpec:
    summary: str | None
    description: str | None
    body_model: type[BaseModel] | None
    exceptions: list[EventException]
