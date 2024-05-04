from typing import Annotated, Any

from pydantic import Field

from tests.example.common import ROOM_NAME
from tests.example.models_db import HelloModel, HelloSchema
from tmexio import AsyncSocket, EventRouter

router = EventRouter()


@router.on("list-hellos")
async def list_hellos(socket: AsyncSocket) -> Any:
    await socket.enter_room(ROOM_NAME)
    return [hello.model_dump(mode="json") for hello in HelloModel.find_all()]


@router.on("create-hello")
async def create_hello(
    hello_data: Annotated[HelloSchema, Field(alias="hello")],
    socket: AsyncSocket,
) -> Any:
    hello = HelloModel.create(hello_data)
    await socket.emit("create-hello", hello.model_dump(mode="json"), target=ROOM_NAME)
    return hello.model_dump(mode="json")


@router.on("close-hellos")
async def close_hellos(socket: AsyncSocket) -> None:
    await socket.leave_room(ROOM_NAME)
