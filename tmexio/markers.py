from typing import Annotated, Generic, TypeVar

from tmexio.server import AsyncServer, AsyncSocket
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


Sid = Annotated[str, SidMarker()]
EventName = Annotated[str, EventNameMarker()]
