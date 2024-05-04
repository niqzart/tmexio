from typing import Annotated

from tests.example.collection_sio import router as collection_router
from tests.example.entries_sio import router as entries_router
from tmexio import TMEXIO, EventName, EventRouter, PydanticPackager

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

app = tmex.build_asgi_app()
