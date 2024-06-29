from datetime import datetime

import pytest
from pydantic_marshals.contains import assert_contains

from tests.example.common import ROOM_NAME, SIO_TOKEN
from tests.example.main import connections, tmex
from tests.example.models_db import HelloModel, HelloSchema
from tests.utils import (
    AsyncSIOTestClient,
    AsyncSIOTestServer,
    assert_ack,
    assert_nodata_ack,
)

pytestmark = pytest.mark.anyio


async def test_connection(client: AsyncSIOTestClient) -> None:
    assert client.sid in connections


async def test_connection_invalid_token(server: AsyncSIOTestServer) -> None:
    async with server.connect_client() as client:
        assert client.sid not in connections


async def test_disconnection(server: AsyncSIOTestServer) -> None:
    async with server.connect_client({"token": SIO_TOKEN}) as client:
        assert client.sid in connections
    assert client.sid not in connections


async def test_unknown(client: AsyncSIOTestClient) -> None:
    assert_ack(
        await client.emit("unknown"),
        expected_body="Unknown event: 'unknown'",
        expected_code=404,
    )


async def test_listing(client: AsyncSIOTestClient, some_hello: HelloModel) -> None:
    assert_ack(
        await client.emit("list-hellos"),
        expected_body=[some_hello.model_dump(mode="json")],
    )
    assert tmex.backend.rooms(client.sid) == [client.sid, ROOM_NAME]


async def test_listing_empty_list(client: AsyncSIOTestClient) -> None:
    assert_ack(await client.emit("list-hellos"), expected_body=[])
    assert tmex.backend.rooms(client.sid) == [client.sid, ROOM_NAME]


async def test_listing_expected_zero_arguments(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
) -> None:
    assert_ack(
        await client.emit("list-hellos", "lol"),
        expected_body="Event expects zero arguments",
        expected_code=422,
    )
    assert listener_client.event_count() == 0


async def test_closing(listener_client: AsyncSIOTestClient) -> None:
    assert_nodata_ack(await listener_client.emit("close-hellos"))
    assert tmex.backend.rooms(listener_client.sid) == [listener_client.sid]


async def test_creating(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello_data: HelloSchema,
) -> None:
    ack = assert_ack(
        await client.emit(
            "create-hello",
            {"hello": some_hello_data.model_dump(mode="json")},
        ),
        expected_body={"id": str, "text": "something", "created": datetime},
        expected_code=201,
    )
    assert_contains(listener_client.event_pop("create-hello"), ack)


@pytest.mark.parametrize("argument_count", [0, 2], ids=["nothing", "too_many"])
async def test_creating_expected_one_argument(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    argument_count: int,
) -> None:
    arguments = ["lol" for _ in range(argument_count)]
    assert_ack(
        await client.emit("create-hello", *arguments),
        expected_body="Event expects one argument",
        expected_code=422,
    )
    assert listener_client.event_count() == 0


async def test_creating_wrong_arguments(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
) -> None:
    assert_ack(
        await client.emit("create-hello", "lol"),
        expected_body=[
            {
                "type": "model_type",
                "loc": [],
                "msg": "Input should be a valid dictionary or instance of create-hello.InputModel",
            }
        ],
        expected_code=422,
    )
    assert listener_client.event_count() == 0


async def test_retrieving(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello: HelloModel,
) -> None:
    assert_ack(
        await client.emit("retrieve-hello", {"hello_id": some_hello.id}),
        expected_body=some_hello.model_dump(mode="json"),
    )
    assert listener_client.event_count() == 0


async def test_retrieving_not_found(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
) -> None:
    assert_ack(
        await client.emit("retrieve-hello", {"hello_id": "not-found"}),
        expected_body="Hello not found",
        expected_code=404,
    )
    assert listener_client.event_count() == 0


async def test_updating(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello: HelloModel,
) -> None:
    new_hello_data = HelloSchema(text="wow", created=datetime(2000, 1, 1))
    new_hello = HelloModel.model_validate(new_hello_data, from_attributes=True)
    new_hello.id = some_hello.id

    ack = assert_ack(
        await client.emit(
            "update-hello", {"hello_id": some_hello.id, "hello": new_hello_data}
        ),
        expected_body=new_hello.model_dump(mode="json"),
    )

    assert_contains(listener_client.event_pop("update-hello"), ack)
    real_hello = HelloModel.find_first_by_id(some_hello.id)
    assert_contains(real_hello, new_hello.model_dump())


async def test_updating_not_found(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello_data: HelloSchema,
) -> None:
    assert_ack(
        await client.emit(
            "update-hello",
            {"hello_id": "not-found", "hello": some_hello_data},
        ),
        expected_body="Hello not found",
        expected_code=404,
    )
    assert listener_client.event_count() == 0


async def test_deleting(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
    some_hello: HelloModel,
) -> None:
    data = {"hello_id": some_hello.id}

    assert_nodata_ack(await client.emit("delete-hello", data))

    assert_contains(listener_client.event_pop("delete-hello"), data)
    assert HelloModel.find_first_by_id(some_hello.id) is None


async def test_deleting_not_found(
    client: AsyncSIOTestClient,
    listener_client: AsyncSIOTestClient,
) -> None:
    assert_nodata_ack(await client.emit("delete-hello", {"hello_id": "not-found"}))
    assert listener_client.event_count() == 0
