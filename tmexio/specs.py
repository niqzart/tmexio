from dataclasses import dataclass


@dataclass()
class HandlerSpec:
    summary: str | None = None
    description: str | None = None
