from tmexio import TMEXIO, AsyncServer, AsyncSocket, EventRouter, Sid
from tmexio.exceptions import EventException
from tmexio.types import DataOrTuple

router = EventRouter()

parsing_exception = EventException(422, "Parsing Exception")


@router.on("hello", exceptions=[parsing_exception])
async def handle_hello(
    args: list[str],
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
def handle_sync_hello(args: list[str], socket: AsyncSocket) -> DataOrTuple:
    return {"args": list(args), "rooms": list(socket.rooms())}


tmex = TMEXIO()
tmex.include_router(router)

app = tmex.build_asgi_app()
