from collections.abc import Iterable
from typing import Annotated

from pydantic import Field

from tests.example.common import ROOM_NAME
from tests.example.models_db import HelloModel, HelloSchema
from tmexio import AsyncSocket, Emitter, EventRouter, PydanticPackager

router = EventRouter(tags=["collection sio"])


@router.on("list-hellos")
async def list_hellos(
    socket: AsyncSocket,
) -> Annotated[Iterable[HelloModel], PydanticPackager(list[HelloModel])]:
    await socket.enter_room(ROOM_NAME)
    return HelloModel.find_all()


@router.on("create-hello")
async def create_hello(
    hello_data: Annotated[HelloSchema, Field(alias="hello")],
    hello_emitter: Annotated[Emitter[HelloModel], "create-hello"],
) -> Annotated[HelloModel, PydanticPackager(HelloModel, code=201)]:
    hello = HelloModel.create(hello_data)
    await hello_emitter.emit(hello, target=ROOM_NAME)
    return hello


@router.on("close-hellos")
async def close_hellos(socket: AsyncSocket) -> None:
    await socket.leave_room(ROOM_NAME)
