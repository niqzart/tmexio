from typing import Annotated

from tests.example.collection_sio import router as collection_router
from tests.example.common import SIO_TOKEN, authorization_exception
from tests.example.entries_sio import router as entries_router
from tmexio import TMEXIO, EventName, EventRouter, PydanticPackager, Sid

main_router = EventRouter()
main_router.include_router(collection_router)
main_router.include_router(entries_router)


@main_router.on_other()
async def handle_other_events(
    event_name: EventName,
) -> Annotated[str, PydanticPackager(str, 404)]:
    return f"Unknown event: '{event_name}'"


tmex = TMEXIO()
tmex.include_router(main_router)
connections: set[str] = set()


@tmex.on_connect(exceptions=[authorization_exception])
async def connect(sid: Sid, token: str) -> None:
    if token != SIO_TOKEN:
        raise authorization_exception
    connections.add(sid)


@tmex.on_disconnect()
async def disconnect(sid: Sid) -> None:
    connections.remove(sid)


app = tmex.build_asgi_app()
