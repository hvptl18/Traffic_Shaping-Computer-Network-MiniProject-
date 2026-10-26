import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


# ==========================================================
# PROJECT: TOKEN BUCKET VS LEAKY BUCKET TRAFFIC SHAPING
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

CONFIG_FILE = BASE_DIR / "config.json"


# ==========================================================
# 1. SIMULATION CONFIGURATION
# ==========================================================

DEFAULT_CONFIG = {
    "duration": 30,
    "baseline_rate": 2,
    "burst_rate": 10,
    "burst_start": 10,
    "burst_end": 15,
    "token_rate": 4,
    "token_capacity": 12,
    "initial_tokens": 12,
    "leaky_rate": 4,
    "queue_capacity": 20
}


def load_config():
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(DEFAULT_CONFIG, file, indent=4)

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


config = load_config()


# ==========================================================
# 2. GENERATE INCOMING TRAFFIC
# ==========================================================

def generate_traffic():
    traffic = []

    for t in range(config["duration"]):
        if config["burst_start"] <= t < config["burst_end"]:
            arrivals = config["burst_rate"]
        else:
            arrivals = config["baseline_rate"]

        traffic.append(arrivals)

    return traffic


# ==========================================================
# 3. SAVE CSV FILE
# ==========================================================

def save_csv(filename, headers, rows):
    path = RESULTS_DIR / filename

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


# ==========================================================
# 4. TOKEN BUCKET SIMULATION
# ==========================================================

def simulate_token_bucket(traffic):
    queue = []
    tokens = config["initial_tokens"]

    rows = []
    queue_sizes = []
    token_levels = []
    output_trace = []
    drop_trace = []

    total_drops = 0

    for t, arrivals in enumerate(traffic):

        # Tokens accumulate up to the bucket capacity.
        tokens = min(
            config["token_capacity"],
            tokens + config["token_rate"]
        )

        # New packets enter the queue.
        for _ in range(arrivals):
            if len(queue) < config["queue_capacity"]:
                queue.append(t)
            else:
                total_drops += 1

        # Record the largest queue before transmission.
        queue_before_transmission = len(queue)

        # Transmit packets while tokens are available.
        sent = min(len(queue), int(tokens))

        for _ in range(sent):
            queue.pop(0)

        tokens -= sent

        queue_sizes.append(len(queue))
        token_levels.append(tokens)
        output_trace.append(sent)
        drop_trace.append(total_drops)

        rows.append([
            t,
            arrivals,
            queue_before_transmission,
            sent,
            len(queue),
            tokens,
            total_drops
        ])

    save_csv(
        "token_bucket_results.csv",
        [
            "time",
            "arrivals",
            "queue_before_transmission",
            "packets_sent",
            "queue_after_transmission",
            "remaining_tokens",
            "cumulative_drops"
        ],
        rows
    )

    return {
        "queue_sizes": queue_sizes,
        "token_levels": token_levels,
        "output_trace": output_trace,
        "drop_trace": drop_trace,
        "total_drops": total_drops
    }


# ==========================================================
# 5. LEAKY BUCKET SIMULATION
# ==========================================================

def simulate_leaky_bucket(traffic):
    queue = []

    rows = []
    queue_sizes = []
    output_trace = []
    drop_trace = []

    total_drops = 0

    for t, arrivals in enumerate(traffic):

        # New packets enter the bounded queue.
        for _ in range(arrivals):
            if len(queue) < config["queue_capacity"]:
                queue.append(t)
            else:
                total_drops += 1

        # Record the queue before transmission.
        queue_before_transmission = len(queue)

        # The bucket releases packets at a fixed rate.
        sent = min(len(queue), config["leaky_rate"])

        for _ in range(sent):
            queue.pop(0)

        queue_sizes.append(len(queue))
        output_trace.append(sent)
        drop_trace.append(total_drops)

        rows.append([
            t,
            arrivals,
            queue_before_transmission,
            sent,
            len(queue),
            total_drops
        ])

    save_csv(
        "leaky_bucket_results.csv",
        [
            "time",
            "arrivals",
            "queue_before_transmission",
            "packets_sent",
            "queue_after_transmission",
            "cumulative_drops"
        ],
        rows
    )

    return {
        "queue_sizes": queue_sizes,
        "output_trace": output_trace,
        "drop_trace": drop_trace,
        "total_drops": total_drops
    }


# ==========================================================
# 6. RUN BOTH SIMULATIONS
# ==========================================================

traffic = generate_traffic()

token_results = simulate_token_bucket(traffic)
leaky_results = simulate_leaky_bucket(traffic)


# ==========================================================
# 7. SAVE COMPARISON METRICS
# ==========================================================

metrics = [
    [
        "Token Bucket",
        sum(token_results["output_trace"]),
        token_results["total_drops"],
        max(token_results["queue_sizes"])
    ],
    [
        "Leaky Bucket",
        sum(leaky_results["output_trace"]),
        leaky_results["total_drops"],
        max(leaky_results["queue_sizes"])
    ]
]

save_csv(
    "performance_metrics.csv",
    [
        "algorithm",
        "total_packets_sent",
        "total_packets_dropped",
        "maximum_queue_after_transmission"
    ],
    metrics
)


# ==========================================================
# 8. GENERATE GRAPHS
# ==========================================================

time = list(range(len(traffic)))


def save_graph(filename, title, ylabel, series):
    plt.figure(figsize=(10, 5))

    for label, values in series:
        plt.plot(time, values, marker="o", label=label)

    plt.title(title)
    plt.xlabel("Time (seconds)")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(RESULTS_DIR / filename, dpi=150)
    plt.close()


save_graph(
    "incoming_traffic.png",
    "Incoming Traffic Pattern",
    "Packets arriving per second",
    [("Incoming traffic", traffic)]
)

save_graph(
    "queue_size.png",
    "Queue Size Comparison",
    "Packets waiting after transmission",
    [
        ("Token Bucket", token_results["queue_sizes"]),
        ("Leaky Bucket", leaky_results["queue_sizes"])
    ]
)

save_graph(
    "burst_output_trace.png",
    "Output Traffic Comparison",
    "Packets transmitted per second",
    [
        ("Token Bucket", token_results["output_trace"]),
        ("Leaky Bucket", leaky_results["output_trace"])
    ]
)

save_graph(
    "packet_drops.png",
    "Cumulative Packet Drops",
    "Total dropped packets",
    [
        ("Token Bucket", token_results["drop_trace"]),
        ("Leaky Bucket", leaky_results["drop_trace"])
    ]
)

save_graph(
    "token_accumulation.png",
    "Token Bucket Remaining Tokens",
    "Remaining tokens",
    [("Token Bucket", token_results["token_levels"])]
)


# ==========================================================
# 9. DISPLAY FINAL SUMMARY
# ==========================================================

print("\n============================================")
print(" TRAFFIC SHAPING SIMULATION COMPLETE")
print("============================================")

print(f"Simulation duration: {config['duration']} seconds")
print(f"Incoming packets: {sum(traffic)}")

print("\nTOKEN BUCKET")
print("Total packets sent:", sum(token_results["output_trace"]))
print("Total packets dropped:", token_results["total_drops"])
print("Maximum queue after transmission:",
      max(token_results["queue_sizes"]))

print("\nLEAKY BUCKET")
print("Total packets sent:", sum(leaky_results["output_trace"]))
print("Total packets dropped:", leaky_results["total_drops"])
print("Maximum queue after transmission:",
      max(leaky_results["queue_sizes"]))

print("\nFiles saved in:", RESULTS_DIR)