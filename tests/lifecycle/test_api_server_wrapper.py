import pytest
import pytest_asyncio
import socket
import asyncio
from fastapi import FastAPI
from lifecycle.api_server_wrapper import APIServerWrapper


@pytest_asyncio.fixture
async def api_wrapper():
    app = FastAPI()
    wrapper = APIServerWrapper(app, host="127.0.0.1", port=8010)
    return wrapper


@pytest.mark.asyncio
async def test_start_and_stop(api_wrapper):
    task = asyncio.create_task(api_wrapper.start())
    await asyncio.sleep(0.1)  # give server time to start

    assert api_wrapper.server is not None

    await api_wrapper.stop()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_stop_without_start(api_wrapper):
    # Should not crash
    await api_wrapper.stop()


@pytest.mark.asyncio
async def test_force_exit_releases_port():
    app = FastAPI()
    wrapper = APIServerWrapper(app, host="127.0.0.1", port=8011)

    t = asyncio.create_task(wrapper.start())
    await asyncio.sleep(0.2)

    await wrapper.stop()
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass

    # port must be free now
    s = socket.socket()
    s.bind(("127.0.0.1", 8011))
    s.close()


@pytest.mark.asyncio
async def test_start_cancelled_externally():
    app = FastAPI()
    wrapper = APIServerWrapper(app, host="127.0.0.1", port=8012)

    t = asyncio.create_task(wrapper.start())
    await asyncio.sleep(0.05)

    t.cancel()
    with pytest.raises(asyncio.CancelledError):
        await t

    await wrapper.stop()


@pytest.mark.asyncio
async def test_socket_closed_on_stop(api_wrapper):
    t = asyncio.create_task(api_wrapper.start())
    await asyncio.sleep(0.2)

    await api_wrapper.stop()
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass

    # socket free?
    s = socket.socket()
    s.bind(("127.0.0.1", 8010))
    s.close()
