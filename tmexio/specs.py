from dataclasses import dataclass


@dataclass()
class HandlerSpec:
    event_name: str
    summary: str | None = None
    description: str | None = None
