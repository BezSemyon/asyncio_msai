from __future__ import annotations

import argparse
import asyncio
import queue
import threading
import time
from typing import List, Dict

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None


def now() -> float:
    return time.perf_counter()


def parse_pairs(s: str) -> List[int]:
    vals: List[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        v = int(part)
        if v <= 0:
            raise ValueError("pairs must be > 0")
        vals.append(v)
    if not vals:
        raise ValueError("empty pairs list")
    return vals


async def pingpong_asyncio(iters: int, pairs: int) -> float:
    async def one_pair() -> None:
        q1: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
        q2: asyncio.Queue[int] = asyncio.Queue(maxsize=1)

        async def pinger() -> None:
            for i in range(iters):
                await q1.put(i)
                await q2.get()

        async def ponger() -> None:
            for _ in range(iters):
                v = await q1.get()
                await q2.put(v)

        await asyncio.gather(pinger(), ponger())

    t0 = now()
    await asyncio.gather(*[one_pair() for _ in range(pairs)])
    return now() - t0


def pingpong_threads(iters: int, pairs: int) -> float:
    threads: List[threading.Thread] = []
    start = threading.Barrier(2 * pairs + 1) 

    def add_pair() -> None:
        q1: "queue.Queue[int]" = queue.Queue(maxsize=1)
        q2: "queue.Queue[int]" = queue.Queue(maxsize=1)

        def pinger() -> None:
            start.wait()
            for i in range(iters):
                q1.put(i)
                q2.get()

        def ponger() -> None:
            start.wait()
            for _ in range(iters):
                v = q1.get()
                q2.put(v)

        threads.append(threading.Thread(target=pinger, daemon=True))
        threads.append(threading.Thread(target=ponger, daemon=True))

    for _ in range(pairs):
        add_pair()

    for th in threads:
        th.start()

    t0 = now()
    start.wait()
    for th in threads:
        th.join()
    return now() - t0


def plot_speedup(xs: List[int], ys: List[float]) -> None:
    if plt is None:
        raise RuntimeError("matplotlib not installed (pip install matplotlib)")
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("pairs")
    plt.ylabel("asyncio / threads")
    plt.title("Asyncio speedup vs threads (ping-pong)")
    plt.tight_layout()
    plt.savefig("pingpong_speedup_ft.png")  # saved in current directory
    plt.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Ping-pong benchmark: one plot (asyncio/threads speedup).")
    ap.add_argument("--iters", type=int, default=300_000, help="iterations per pair")
    ap.add_argument("--pairs", type=str, default="1,2,4,8", help='comma list, e.g. "1,2,4,8,12"')
    ap.add_argument("--plot", action="store_true", help="save pingpong_speedup.png")
    args = ap.parse_args()

    pairs_list = parse_pairs(args.pairs)

    rps_async: Dict[int, float] = {}
    rps_thr: Dict[int, float] = {}

    for p in pairs_list:
        dt_a = asyncio.run(pingpong_asyncio(args.iters, p))
        rps_a = (args.iters * p) / dt_a if dt_a > 0 else 0.0
        rps_async[p] = rps_a
        print(f"asyncio  pairs={p:<3d} time={dt_a:.6f}s rps={int(rps_a)}")

        dt_t = pingpong_threads(args.iters, p)
        rps_t = (args.iters * p) / dt_t if dt_t > 0 else 0.0
        rps_thr[p] = rps_t
        print(f"threads  pairs={p:<3d} time={dt_t:.6f}s rps={int(rps_t)} (threads={2*p})")

    xs = sorted(set(rps_async.keys()) & set(rps_thr.keys()))
    ys = [(rps_async[x] / rps_thr[x]) if rps_thr[x] > 0 else 0.0 for x in xs]

    if args.plot:
        plot_speedup(xs, ys)
        print("Wrote: pingpong_speedup.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
