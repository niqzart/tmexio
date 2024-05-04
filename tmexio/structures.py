from __future__ import annotations

from tmexio.server import AsyncServer, AsyncSocket
from tmexio.types import DataType


class ClientEvent:
    def __init__(
        self,
        server: AsyncServer,
        event_name: str,
        sid: str,
        *args: DataType,
    ) -> None:
        self.event_name = event_name
        self.sid = sid
        self.server = server
        self.socket = AsyncSocket(server=server, sid=sid)
        self.args = args
