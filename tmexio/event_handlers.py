from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from tmexio.markers import Marker
from tmexio.structures import ClientEvent
from tmexio.types import DataOrTuple


class Destinations:
    def __init__(self) -> None:
        self.markers: dict[Marker[Any], list[str]] = {}

    def add_marker_destination(self, marker: Marker[Any], destination: str) -> None:
        self.markers.setdefault(marker, []).append(destination)


class AsyncEventHandler:
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        destinations: Destinations,
    ) -> None:
        self.async_callable = async_callable
        self.destinations = destinations

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        kwargs: dict[str, Any] = {}
        for marker, parameter_names in self.destinations.markers.items():
            value = marker.extract(event)
            for name in parameter_names:
                kwargs[name] = value

        return await self.async_callable(*event.args, **kwargs)  # type: ignore[no-any-return]
        # TODO pack result from Any to DataOrTuple
