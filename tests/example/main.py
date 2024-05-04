from tests.example.collection_sio import router as collection_router
from tests.example.entries_sio import router as entries_router
from tmexio import TMEXIO, EventRouter

main_router = EventRouter()
main_router.include_router(collection_router)
main_router.include_router(entries_router)

tmex = TMEXIO()
tmex.include_router(main_router)

app = tmex.build_asgi_app()
