import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

def cpu_bound_task(n):
    """CPU intensive"""
    return sum(i * i for i in range(n))

async def main():
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=8))

    async with asyncio.TaskGroup() as tg:
        for _ in range(10):
            tg.create_task(asyncio.to_thread(cpu_bound_task, 5_000_000))

if __name__ == '__main__':
    start = time.perf_counter()
    asyncio.run(main())
    elapsed = time.perf_counter() - start
    print(f"Elapsed: {elapsed:.3f} seconds")
