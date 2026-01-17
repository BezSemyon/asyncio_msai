import time
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import matplotlib.pyplot as plt

SLEEP_S = 0.1
n_tasks_list = [100, 1000, 10_000, 100_000]

CPU = os.cpu_count() or 4
CAPPED_WORKERS = min(200, 50 * CPU)

def sync_task(_):
    time.sleep(SLEEP_S)
    return 1

def now() -> float:
    return time.perf_counter()

def run_threadpool(n_tasks: int, max_workers: int) -> float:
    t0 = now()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(sync_task, range(n_tasks)))
    return now() - t0

async def async_task_sleep():
    await asyncio.sleep(SLEEP_S)
    return 1

async def run_asyncio_sleep_coro(n_tasks: int):
    tasks = [asyncio.create_task(async_task_sleep()) for _ in range(n_tasks)]
    return await asyncio.gather(*tasks)

async def run_asyncio_to_thread_coro(n_tasks: int):
    tasks = [asyncio.create_task(asyncio.to_thread(sync_task, i)) for i in range(n_tasks)]
    return await asyncio.gather(*tasks)

def run_asyncio_in_new_loop(coro, *, max_workers: int | None = None) -> float:
    out = {"elapsed": None, "error": None}

    def worker():
        loop = None
        executor = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if max_workers is not None:
                executor = ThreadPoolExecutor(max_workers=max_workers)
                loop.set_default_executor(executor)

            t0 = now()
            loop.run_until_complete(coro)
            out["elapsed"] = now() - t0

        except Exception as e:
            out["error"] = e
        finally:
            try:
                if executor is not None:
                    executor.shutdown(wait=True)
                if loop is not None:
                    loop.close()
            finally:
                asyncio.set_event_loop(None)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join()

    if out["error"] is not None:
        raise out["error"]
    return out["elapsed"]

def run_asyncio_sleep(n_tasks: int) -> float:
    return run_asyncio_in_new_loop(run_asyncio_sleep_coro(n_tasks))

def run_asyncio_to_thread_capped(n_tasks: int) -> float:
    workers = min(CAPPED_WORKERS, n_tasks)
    return run_asyncio_in_new_loop(run_asyncio_to_thread_coro(n_tasks), max_workers=workers)

def run_variant(variant: str, n_tasks: int) -> float:
    if variant == "threadpool_capped":
        return run_threadpool(n_tasks, min(CAPPED_WORKERS, n_tasks))
    if variant == "threadpool_naive":
        return run_threadpool(n_tasks, n_tasks)
    if variant == "asyncio_to_thread_capped":
        return run_asyncio_to_thread_capped(n_tasks)
    if variant == "asyncio_sleep":
        return run_asyncio_sleep(n_tasks)
    raise ValueError(f"Unknown variant: {variant}")

VARIANTS = [
    ("threadpool_capped", f"ThreadPool (workers<= {CAPPED_WORKERS})"),
    ("threadpool_naive", "ThreadPool (workers=n_tasks)"),
    ("asyncio_to_thread_capped", "Asyncio (to_thread(sync_task), capped executor)"),
    ("asyncio_sleep", "Asyncio (await sleep)"),
]

rows = []
for n in n_tasks_list:
    row = {"n_tasks": n}

    for key, _label in VARIANTS:
        try:
            row[f"{key}_time_s"] = run_variant(key, n)
            row[f"{key}_error"] = False
            row[f"{key}_error_msg"] = ""
        except RuntimeError as e:
            row[f"{key}_time_s"] = float("nan")
            row[f"{key}_error"] = True
            row[f"{key}_error_msg"] = str(e)

    row["threadpool_capped_workers"] = min(CAPPED_WORKERS, n)
    row["asyncio_to_thread_capped_workers"] = min(CAPPED_WORKERS, n)
    row["threadpool_naive_workers"] = n

    rows.append(row)

df = pd.DataFrame(rows)

baseline = "threadpool_capped"
for key, _label in VARIANTS:
    if key == baseline:
        continue
    df[f"speedup_{key}_over_{baseline}"] = df[f"{baseline}_time_s"] / df[f"{key}_time_s"]

print(df)

plt.figure()
for key, label in VARIANTS:
    plt.plot(df["n_tasks"], df[f"{key}_time_s"], marker="o", label=label)
plt.xscale("log")
plt.yscale("log")
plt.xlabel("Number of tasks (log)")
plt.ylabel("Elapsed time, seconds (log)")
plt.title("Sleep(0.1s) tasks: 4 variants")
plt.legend()
plt.grid(True, which="both", linestyle="--", linewidth=0.5)
plt.savefig("figure_1ft.png", dpi=200, bbox_inches="tight")

plt.figure()
for key, label in VARIANTS:
    if key == baseline:
        continue
    plt.plot(
        df["n_tasks"],
        df[f"speedup_{key}_over_{baseline}"],
        marker="o",
        label=f"{label} speedup vs {dict(VARIANTS)[baseline]}",
    )
plt.xscale("log")
plt.xlabel("Number of tasks (log)")
plt.ylabel("Speedup (baseline time / variant time)")
plt.title("Relative performance: higher is better than baseline")
plt.legend()
plt.grid(True, which="both", linestyle="--", linewidth=0.5)
plt.savefig("figure_2ft.png", dpi=200, bbox_inches="tight")
