from dataclasses import dataclass

from tmexio.exceptions import EventException


@dataclass()
class HandlerSpec:
    summary: str | None = None
    description: str | None = None
    exceptions: list[EventException] | None = None
