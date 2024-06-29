from typing import Annotated, Any

from pydantic import Field

from tests.example.common import ROOM_NAME, not_found_exception
from tests.example.models_db import HelloModel, HelloSchema
from tmexio import Emitter, EventRouter, register_dependency

router = EventRouter(tags=["entries sio"])


@register_dependency()
async def maybe_get_hello_by_id(hello_id: str) -> HelloModel | None:
    return HelloModel.find_first_by_id(hello_id)


MaybeHelloById = Annotated[HelloModel | None, maybe_get_hello_by_id]


@register_dependency(exceptions=[not_found_exception])
async def get_hello_by_id(hello: MaybeHelloById) -> HelloModel:
    if hello is None:
        raise not_found_exception
    return hello


HelloById = Annotated[HelloModel, get_hello_by_id]


@router.on("update-hello")
async def update_hello(
    hello: HelloById,
    hello_data: Annotated[HelloSchema, Field(alias="hello")],
    duplex_emitter: Emitter[HelloModel],
) -> HelloModel:
    hello.update(hello_data)
    await duplex_emitter.emit(hello, target=ROOM_NAME)
    return hello


@router.on("delete-hello", tags=["deleter"])
async def delete_hello(
    hello: MaybeHelloById,
    duplex_emitter: Emitter[dict[str, Any]],
) -> None:
    if hello is not None:
        hello.delete()
        await duplex_emitter.emit({"hello_id": hello.id}, target=ROOM_NAME)


@router.on("retrieve-hello")
async def retrieve_hello(hello: HelloById) -> HelloModel:
    return hello
