from typing import Annotated

from pydantic import Field

from tests.example.common import ROOM_NAME, not_found_exception
from tests.example.models_db import HelloModel, HelloSchema
from tmexio import AsyncSocket, Depends, EventRouter

router = EventRouter()


async def maybe_get_hello_by_id(hello_id: str) -> HelloModel | None:
    return HelloModel.find_first_by_id(hello_id)


MaybeHelloById = Annotated[HelloModel | None, Depends(maybe_get_hello_by_id)]


async def get_hello_by_id(hello_id: str) -> HelloModel:
    hello = HelloModel.find_first_by_id(hello_id)
    if hello is None:
        raise not_found_exception
    return hello


HelloById = Annotated[
    HelloModel, Depends(get_hello_by_id, exceptions=[not_found_exception])
]


@router.on("update-hello")
async def update_hello(
    hello: HelloById,
    hello_data: Annotated[HelloSchema, Field(alias="hello")],
    socket: AsyncSocket,
) -> HelloModel:
    hello.update(hello_data)
    await socket.emit("update-hello", hello.model_dump(mode="json"), target=ROOM_NAME)
    return hello


@router.on("delete-hello")
async def delete_hello(hello: MaybeHelloById, socket: AsyncSocket) -> None:
    if hello is not None:
        hello.delete()
        await socket.emit("delete-hello", {"hello_id": hello.id}, target=ROOM_NAME)


@router.on("retrieve-hello")
async def retrieve_hello(hello: HelloById) -> HelloModel:
    return hello
