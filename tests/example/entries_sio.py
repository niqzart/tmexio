from typing import Annotated

from pydantic import Field

from tests.example.common import ROOM_NAME, not_found_exception
from tests.example.models_db import HelloModel, HelloSchema
from tmexio import AsyncSocket, EventRouter

router = EventRouter()


@router.on("update-hello", exceptions=[not_found_exception])
async def update_hello(
    hello_id: str,
    hello_data: Annotated[HelloSchema, Field(alias="hello")],
    socket: AsyncSocket,
) -> HelloModel:
    hello = HelloModel.find_first_by_id(hello_id)
    if hello is None:
        raise not_found_exception
    hello.update(hello_data)
    await socket.emit("update-hello", hello.model_dump(mode="json"), target=ROOM_NAME)
    return hello


@router.on("delete-hello")
async def delete_hello(hello_id: str, socket: AsyncSocket) -> None:
    hello = HelloModel.find_first_by_id(hello_id)
    if hello is not None:
        hello.delete()
        await socket.emit("delete-hello", {"hello_id": hello_id}, target=ROOM_NAME)


@router.on("retrieve-hello")
async def retrieve_hello(hello_id: str) -> HelloModel:
    hello = HelloModel.find_first_by_id(hello_id)
    if hello is None:
        raise not_found_exception
    return hello
