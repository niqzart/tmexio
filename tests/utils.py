import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Self
from unittest.mock import patch

from engineio import packet as eio_packet  # type: ignore[import-untyped]
from socketio import AsyncServer, packet  # type: ignore[import-untyped]


class AsyncSIOTestClient:
    def __init__(self, server: AsyncServer, eio_sid: str) -> None:
        self.server: AsyncServer = server
        self.eio_sid: str = eio_sid
        self.events: dict[str, list[Any]] = {}
        self.packets: dict[int, list[packet.Packet]] = {}
        self.eio_packets: dict[int, list[eio_packet.Packet]] = {}

    @property
    def sid(self) -> str:
        return self.server.manager.sid_from_eio_sid(self.eio_sid, "/")  # type: ignore

    def event_put(self, event: str, data: Any) -> None:
        self.events.setdefault(event, []).append(data)

    def event_pop(self, event: str) -> Any | None:
        result = self.events.get(event, [])
        if len(result) < 2:
            self.events.pop(event, None)
        if len(result) == 0:
            return None
        return result.pop(0)

    def event_count(self, event: str | None = None) -> int:
        if event is None:
            return sum(len(queue) for queue in self.events.values())
        return len(self.events.get(event, []))

    async def emit(self, event: str, *data: Any) -> Any:
        return await self.server._trigger_event(event, "/", self.sid, *data)


class AsyncSIOTestServer:
    def __init__(self, server: AsyncServer) -> None:
        self.server: AsyncServer = server
        self.clients: dict[str, AsyncSIOTestClient] = {}

    async def _send_eio_packet(self, eio_sid: str, eio_pkt: eio_packet.Packet) -> None:
        # TODO encode packets before parsing again

        client: AsyncSIOTestClient | None = self.clients.get(eio_sid)
        if client is None:
            return  # TODO logging?

        if eio_pkt.packet_type == eio_packet.MESSAGE:
            # TODO this is a band-aid, doesn't work with multi-packet messages
            pkt = packet.Packet(encoded_packet=eio_pkt.data)
            if pkt.packet_type in {packet.EVENT, packet.BINARY_EVENT}:
                client.event_put(event=pkt.data[0], data=pkt.data[1])
            else:
                logging.warning(f"Unknown packet: {pkt.packet_type=} {pkt.data=}")
                client.packets.setdefault(pkt.packet_type, []).append(pkt)
        else:
            logging.warning(f"Unknown eio packet: {eio_pkt.data=}")
            client.eio_packets.setdefault(eio_pkt.packet_type, []).append(eio_pkt)

    @contextmanager
    def patch(self) -> Iterator[Self]:
        mock_send = patch.object(self.server, "_send_eio_packet", self._send_eio_packet)
        mock_send.start()
        yield self
        mock_send.stop()

    @asynccontextmanager
    async def connect_client(
        self, data: Any = None
    ) -> AsyncIterator[AsyncSIOTestClient]:
        eio_sid: str = self.server.eio.generate_id()
        client = AsyncSIOTestClient(server=self.server, eio_sid=eio_sid)
        self.clients[eio_sid] = client

        await self.server._handle_eio_connect(eio_sid=eio_sid, environ={})
        await self.server._handle_connect(eio_sid=eio_sid, namespace="/", data=data)

        # TODO check client.packets for the CONNECT-type packet

        yield client

        await self.server._handle_disconnect(eio_sid=eio_sid, namespace="/")
        await self.server._handle_eio_disconnect(eio_sid=eio_sid)

        # TODO check client.packets for the DISCONNECT-type packet

        self.clients.pop(eio_sid)
