from typing import Annotated, Any, Generic, TypeVar

from pydantic import TypeAdapter

from tmexio.server import AsyncServer, AsyncSocket, Emitter
from tmexio.structures import ClientEvent

T = TypeVar("T")


class Marker(Generic[T]):
    def extract(self, event: ClientEvent) -> T:
        raise NotImplementedError


class EventNameMarker(Marker[str]):
    def extract(self, event: ClientEvent) -> str:
        return event.event_name


class SidMarker(Marker[str]):
    def extract(self, event: ClientEvent) -> str:
        return event.sid


class AsyncServerMarker(Marker[AsyncServer]):
    def extract(self, event: ClientEvent) -> AsyncServer:
        return event.server


class AsyncSocketMarker(Marker[AsyncSocket]):
    def extract(self, event: ClientEvent) -> AsyncSocket:
        return event.socket


class ClientEventMarker(Marker[ClientEvent]):
    def extract(self, event: ClientEvent) -> ClientEvent:
        return event


class ServerEmitterMarker(Marker[Emitter[T]]):
    def __init__(self, body_annotation: Any, event_name: str) -> None:
        self.event_name = event_name
        self.adapter = TypeAdapter(body_annotation)

    def extract(self, event: ClientEvent) -> Emitter[T]:
        return Emitter(
            server=event.server,
            event_name=self.event_name,
            adapter=self.adapter,
        )


Sid = Annotated[str, SidMarker()]
EventName = Annotated[str, EventNameMarker()]
