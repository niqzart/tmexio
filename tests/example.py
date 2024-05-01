from socketio import ASGIApp  # type: ignore[import-untyped]

from tmexio import TMEXIO, EventRouter
from tmexio.exceptions import EventException
from tmexio.main import Sid
from tmexio.types import DataOrTuple, DataType

router = EventRouter()

parsing_exception = EventException(422, "Parsing Exception")


@router.on("hello", exceptions=[parsing_exception])
async def handle_hello(*args: DataType, sid: Sid, sid2: Sid) -> DataOrTuple:
    if len(args) < 2:
        raise parsing_exception
    return {
        "sid": sid,
        "sid2": sid2,
        "first": args[0],
        "other": list(args[1:]),
    }


@router.on("hello-sync")
def handle_sync_hello(*args: DataType) -> DataOrTuple:
    return {"args": list(args)}


tmex = TMEXIO()
tmex.include_router(router)

app = ASGIApp(socketio_server=tmex.backend)
