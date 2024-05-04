from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from tmexio.markers import Marker
from tmexio.packagers import BasePackager
from tmexio.structures import ClientEvent
from tmexio.types import DataOrTuple


class AsyncEventHandler:
    def __init__(
        self,
        async_callable: Callable[..., Awaitable[Any]],
        marker_destinations: list[tuple[Marker[Any], list[str]]],
        body_model: type[BaseModel],
        body_destinations: list[tuple[str, list[str]]],
        ack_packager: BasePackager[Any],
    ) -> None:
        self.async_callable = async_callable
        self.marker_destinations = marker_destinations
        self.body_model = body_model
        self.body_destinations = body_destinations
        self.ack_packager = ack_packager

    async def __call__(self, event: ClientEvent) -> DataOrTuple:
        if len(event.args) != 1:  # TODO convert to 422
            raise NotImplementedError("Multiple arguments are not supported")

        body = self.body_model.model_validate(event.args[0])

        kwargs: dict[str, Any] = {}
        for field_name, parameter_names in self.body_destinations:
            value = getattr(body, field_name, None)  # TODO replace fallback with error
            for name in parameter_names:
                kwargs[name] = value

        for marker, parameter_names in self.marker_destinations:
            value = marker.extract(event)
            for name in parameter_names:
                kwargs[name] = value

        result = await self.async_callable(**kwargs)

        return self.ack_packager.pack_data(result)
