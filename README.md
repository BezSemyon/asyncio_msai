**file 1_free_thread.py** is for demonstration that free-threading version of Python runs faster that with GIL
**file 2_bench_sync_async.py** runs 4 types: asyncio (sync and async), thread (limit workers and workers equal to number of tasks)
**file 3_pingpong.py** creates pairs of 2 queues. Run this file on Python with GIL and with free-threading
