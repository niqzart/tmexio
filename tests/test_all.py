import pytest
from pydantic_marshals.contains import assert_contains

from tests.utils import AsyncSIOTestClient
from tmexio.exceptions import EventException

pytestmark = pytest.mark.anyio


async def test_happy(client: AsyncSIOTestClient) -> None:
    args = {"something": "wow"}, ["hello"]
    assert_contains(
        await client.emit("hello", *args),
        {
            "sid": client.sid,
            "sid2": client.sid,
            "first": args[0],
            "other": [args[1]],
            "rooms": [client.sid],
        },
    )


async def test_parsing_exception(client: AsyncSIOTestClient) -> None:
    with pytest.raises(EventException) as exc_info:
        await client.emit("hello")
    assert_contains(
        exc_info.value.ack_data,
        [422, "Parsing Exception"],
    )


async def test_happy_sync(client: AsyncSIOTestClient) -> None:
    args = [{"something": "wow"}, ["hello"]]
    assert_contains(
        await client.emit("hello-sync", *args),
        {"args": args, "rooms": [client.sid]},
    )
