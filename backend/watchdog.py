import asyncio
from time import monotonic


async def monitor(worker, heartbeat: list[float], timeout: float = 3.0):
    while not worker.done():
        await asyncio.sleep(0.05)
        if monotonic() - heartbeat[0] > timeout:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
            raise TimeoutError('Worker heartbeat expired')
    return await worker
