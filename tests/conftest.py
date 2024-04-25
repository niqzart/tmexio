from collections.abc import AsyncIterator

import pytest

from tests.example import tmex
from tests.utils import AsyncSIOTestClient, AsyncSIOTestServer

pytest_plugins = ("anyio",)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def server() -> AsyncIterator[AsyncSIOTestServer]:
    with AsyncSIOTestServer(server=tmex.backend).patch() as server:
        yield server


@pytest.fixture(scope="session")
async def client(server: AsyncSIOTestServer) -> AsyncIterator[AsyncSIOTestClient]:
    async with server.connect_client() as client:
        yield client
