from collections.abc import AsyncIterator, Iterator
from contextlib import suppress
from datetime import datetime

import pytest

from tests.example.common import ROOM_NAME, SIO_TOKEN
from tests.example.main import tmex
from tests.example.models_db import HelloModel, HelloSchema
from tests.utils import AsyncSIOTestClient, AsyncSIOTestServer

pytest_plugins = ("anyio",)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def server() -> AsyncIterator[AsyncSIOTestServer]:
    with AsyncSIOTestServer(server=tmex.backend).patch() as server:
        yield server


@pytest.fixture()
async def client(server: AsyncSIOTestServer) -> AsyncIterator[AsyncSIOTestClient]:
    async with server.connect_client({"token": SIO_TOKEN}) as client:
        yield client


@pytest.fixture()
async def listener_client(
    server: AsyncSIOTestServer,
) -> AsyncIterator[AsyncSIOTestClient]:
    async with server.connect_client({"token": SIO_TOKEN}) as client:
        await tmex.backend.enter_room(client.sid, ROOM_NAME)
        yield client


@pytest.fixture()
def some_hello_data() -> HelloSchema:
    return HelloSchema(text="something", created=datetime.now())


@pytest.fixture()
def some_hello(some_hello_data: HelloSchema) -> Iterator[HelloModel]:
    entry = HelloModel.create(some_hello_data)
    yield entry
    with suppress(KeyError):
        entry.delete()
