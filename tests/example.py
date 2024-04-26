from socketio import ASGIApp  # type: ignore[import-untyped]

from tmexio import TMEXIO, EventRouter
from tmexio.exceptions import EventException
from tmexio.types import DataOrTuple, DataType

router = EventRouter()

parsing_exception = EventException(422, "Parsing Exception")


@router.on("hello", exceptions=[parsing_exception])
async def handle_hello(sid: str, *args: DataType) -> DataOrTuple:
    if len(args) < 2:
        raise parsing_exception
    return {
        "sid": sid,
        "first": args[0],
        "other": list(args[1:]),
    }


tmex = TMEXIO()
tmex.include_router(router)

app = ASGIApp(socketio_server=tmex.backend)
