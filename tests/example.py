from tmexio import TMEXIO, EventRouter
from tmexio.exceptions import EventException
from tmexio.main import Sid
from tmexio.server import AsyncServer, AsyncSocket
from tmexio.types import DataOrTuple, DataType

router = EventRouter()

parsing_exception = EventException(422, "Parsing Exception")


@router.on("hello", exceptions=[parsing_exception])
async def handle_hello(
    *args: DataType,
    sid: Sid,
    sid2: Sid,
    socket: AsyncSocket,
    server: AsyncServer,
) -> DataOrTuple:
    if len(args) < 2:
        raise parsing_exception
    await server.enter_room(sid, "new")
    await socket.leave_room("new")
    return {
        "sid": sid,
        "sid2": sid2,
        "first": args[0],
        "other": list(args[1:]),
        "rooms": list(socket.rooms()),
    }


@router.on("hello-sync")
def handle_sync_hello(*args: DataType, socket: AsyncSocket) -> DataOrTuple:
    return {"args": list(args), "rooms": list(socket.rooms())}


tmex = TMEXIO()
tmex.include_router(router)

app = tmex.build_asgi_app()
