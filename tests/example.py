from socketio import ASGIApp  # type: ignore[import-untyped]

from tmexio import TMEXIO, EventRouter
from tmexio.types import DataOrTuple, DataType

router = EventRouter()


@router.on("hello")
async def handle_hello(sid: str, *args: DataType) -> DataOrTuple:
    return {
        "sid": sid,
        "args": list(args),
    }


tmex = TMEXIO()
tmex.include_router(router)

app = ASGIApp(socketio_server=tmex.backend)
