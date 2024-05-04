from datetime import datetime

import pytest
from pydantic_marshals.contains import assert_contains

from tests.example.common import ROOM_NAME
from tests.example.main import tmex
from tests.example.models_db import HelloModel, HelloSchema
from tests.utils import AsyncSIOTestClient
from tmexio.exceptions import EventException

pytestmark = pytest.mark.anyio


async def test_listing(client: AsyncSIOTestClient, some_hello: HelloModel) -> None:
    assert_contains(
        await client.emit("list-hellos", {}), [some_hello.model_dump(mode="json")]
    )
    assert tmex.backend.rooms(client.sid) == [client.sid, ROOM_NAME]


async def test_listing_empty_list(client: AsyncSIOTestClient) -> None:
    assert_contains(await client.emit("list-hellos", {}), [])
    assert tmex.backend.rooms(client.sid) == [client.sid, ROOM_NAME]


async def test_closing(listener_client: AsyncSIOTestClient) -> None:
    assert_contains(await listener_client.emit("close-hellos", {}), None)
    assert tmex.backend.rooms(listener_client.sid) == [listener_client.sid]


async def test_creating(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello_data: HelloSchema,
) -> None:
    ack = await client.emit(
        "create-hello", {"hello": some_hello_data.model_dump(mode="json")}
    )

    assert_contains(ack, {"id": str, "text": "something", "created": datetime})
    assert_contains(listener_client.event_pop("create-hello"), ack)


async def test_retrieving(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello: HelloModel,
) -> None:
    ack = await client.emit("retrieve-hello", {"hello_id": some_hello.id})

    assert_contains(ack, some_hello.model_dump(mode="json"))
    assert listener_client.event_count() == 0


async def test_retrieving_not_found(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
) -> None:
    with pytest.raises(EventException) as exc_info:
        await client.emit("retrieve-hello", {"hello_id": "not-found"})

    assert_contains(
        exc_info.value.ack_data,
        [404, "Hello not found"],
    )
    assert listener_client.event_count() == 0


async def test_updating(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello: HelloModel,
) -> None:
    new_hello_data = HelloSchema(text="wow", created=datetime(2000, 1, 1))
    new_hello = {**new_hello_data.model_dump(mode="json"), "id": some_hello.id}

    ack = await client.emit(
        "update-hello", {"hello_id": some_hello.id, "hello": new_hello}
    )

    assert_contains(ack, new_hello)
    assert_contains(listener_client.event_pop("update-hello"), new_hello)
    assert_contains(HelloModel.find_first_by_id(some_hello.id), new_hello)


async def test_updating_not_found(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello_data: HelloSchema,
) -> None:
    with pytest.raises(EventException) as exc_info:
        await client.emit(
            "update-hello",
            {"hello_id": "not-found", "hello": some_hello_data},
        )

    assert_contains(
        exc_info.value.ack_data,
        [404, "Hello not found"],
    )
    assert listener_client.event_count() == 0


async def test_deleting(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello: HelloModel,
) -> None:
    data = {"hello_id": some_hello.id}

    ack = await client.emit("delete-hello", data)

    assert_contains(ack, None)
    assert_contains(listener_client.event_pop("delete-hello"), data)
    assert HelloModel.find_first_by_id(some_hello.id) is None


async def test_deleting_not_found(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
) -> None:
    ack = await client.emit("delete-hello", {"hello_id": "not-found"})

    assert_contains(ack, None)
    assert listener_client.event_count() == 0
