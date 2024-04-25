import pytest
from pydantic_marshals.contains import assert_contains

from tests.utils import AsyncSIOTestClient

pytestmark = pytest.mark.anyio


async def test_all(client: AsyncSIOTestClient) -> None:
    args = {"something": "wow"}, ["hello"]
    assert_contains(
        await client.emit("hello", *args),
        {
            "sid": client.sid,
            "args": list(args),
        },
    )
