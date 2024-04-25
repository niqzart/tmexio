from socketio import ASGIApp  # type: ignore[import-untyped]

from tmexio import TMEXIO
from tmexio.types import DataOrTuple, DataType

tmex = TMEXIO()


@tmex.on("hello")
async def handle_hello(sid: str, *args: DataType) -> DataOrTuple:
    return {
        "sid": sid,
        "args": list(args),
    }


app = ASGIApp(socketio_server=tmex.backend)
