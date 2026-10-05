import asyncio
import time

import pytest


@pytest.mark.asyncio
async def test_blocking_operation_does_not_block_event_loop_when_run_in_thread():
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        deadline = asyncio.get_running_loop().time() + 0.15
        while asyncio.get_running_loop().time() < deadline:
            ticks += 1
            await asyncio.sleep(0.01)

    def blocking_operation():
        time.sleep(0.1)
        return "done"

    result, _ = await asyncio.gather(
        asyncio.to_thread(blocking_operation),
        heartbeat(),
    )

    assert result == "done"
    assert ticks >= 5


@pytest.mark.asyncio
async def test_blocking_operation_blocks_event_loop_without_thread():
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        deadline = asyncio.get_running_loop().time() + 0.15
        while asyncio.get_running_loop().time() < deadline:
            ticks += 1
            await asyncio.sleep(0.01)

    def blocking_operation():
        time.sleep(0.1)
        return "done"

    async def blocking_wrapper():
        return blocking_operation()

    result, _ = await asyncio.gather(
        blocking_wrapper(),
        heartbeat(),
    )

    assert result == "done"
    assert ticks <= 2
