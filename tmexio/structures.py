from __future__ import annotations

from tmexio.server import AsyncServer, AsyncSocket
from tmexio.types import DataType


class ClientEvent:
    def __init__(self, server: AsyncServer, sid: str, *args: DataType) -> None:
        self.sid = sid
        self.server = server
        self.socket = AsyncSocket(server=server, sid=sid)
        self.args = args
