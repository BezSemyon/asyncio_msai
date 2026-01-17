import csv
import matplotlib.pyplot as plt

def load(path):
    xs, ys = [], []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            xs.append(int(row["workers"]))
            ys.append(float(row["mbps"]))
    return xs, ys

x1, y1 = load("results_gil.csv")
x2, y2 = load("results_free_threading.csv")

plt.figure(figsize=(11, 5))
plt.plot(x1, y1, marker="o", linewidth=2, label="GIL enabled")
plt.plot(x2, y2, marker="o", linewidth=2, label="free-threading")

plt.title("asyncio TCP benchmark")
plt.xlabel("Number of workers")
plt.ylabel("Speed (MB/s)")
plt.xticks(x1)
plt.grid(True, alpha=0.3)

ax = plt.gca()
for x, y in zip(x1, y1):
    ax.annotate(f"{int(y)}", (x, y), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=9, color=ax.lines[0].get_color())
for x, y in zip(x2, y2):
    ax.annotate(f"{int(y)}", (x, y), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=9, color=ax.lines[1].get_color())

plt.legend(loc="upper left")
plt.tight_layout()
plt.savefig('tcp_asyncio.png', dpi=200, bbox_inches="tight")
