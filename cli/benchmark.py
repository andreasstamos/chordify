import time
import cli
import copy
import threading

REPLICATION_FACTORS = [1,3,5]
CONSISTENCY_MODELS = ["LINEARIZABLE", "EVENTUAL"]


INSERTS  = [None for _ in range(10)]
QUERIES  = [None for _ in range(10)]
REQUESTS = [None for _ in range(10)]

INSERT_VALUE = ""

for i in range(10):
    with open(f"./benchmark_data/insert_{i:02}_part.txt") as f:
        INSERTS[i] = [line.strip() for line in f.readlines()]
    with open(f"./benchmark_data/query_{i:02}.txt") as f:
        QUERIES[i] = [line.strip() for line in f.readlines()]
    with open(f"./benchmark_data/requests_{i:02}.txt") as f:
        REQUESTS[i] = [line.strip().split(maxsplit=1) for line in f.readlines()]


def benchmark_driver(client_factory, consistency_model, replication_factor):
    print("Setting up...")

    client = client_factory()
    for physical in client.physical_urls:
        client.physical = physical
        client.killall()

    client.physical = "vm1"
    client.spawn_bootstrap(consistency_model, replication_factor)
    client.spawn()

    for physical in client.physical_urls:
        if physical == "vm1": continue
        client.physical = physical
        client.spawn()
        client.spawn()

    times_bench1 = [None for _ in range(10)]
    times_bench2 = [None for _ in range(10)]

    def node_driver(node_index):
        nonlocal times_bench1, times_bench2

        physical_idx = 1 + node_index // 2
        logical_idx  = 1 + node_index  % 2

        if physical_idx == 1:
            logical_idx -= 1 # use bootstrap

        client = client_factory()
        client.physical = f"vm{physical_idx}"
        client.logical = str(logical_idx)
        
        t_start = time.time()
        for insert_key in INSERTS[node_index]:
            client.modify("insert", insert_key, INSERT_VALUE)
        t_end = time.time()
        times_bench1[node_index] = t_end-t_start

        t_start = time.time()
        for query_key in QUERIES[node_index]:
            client.query(query_key)
        t_end = time.time()
        times_bench2[node_index] = t_end-t_start

    print("Start benchmarking...")
    threads = [threading.Thread(target=node_driver, args=(node_index,), daemon=False) for node_index in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print("Benchmarking done.")

    time_bench1 = max(times_bench1)
    time_bench2 = max(times_bench2)

    print("Cleaning up...")
    for physical in client.physical_urls:
        client.physical = physical
        client.killall()

    return time_bench1, time_bench2

def run_benchmarks(client_factory):
    results = {}
    for replication_factor in REPLICATION_FACTORS:
        for consistency_model in CONSISTENCY_MODELS:
            result = benchmark_driver(client_factory, consistency_model, replication_factor)
            results[(consistency_model, replication_factor)] = result
    return results


if __name__ == "__main__":
    import configuration
    import csv

    client_factory = lambda: cli.Client(
            physical_urls=configuration.physical_urls,
            username=configuration.http_username,
            password=configuration.http_password)
    results = run_benchmarks(client_factory)

    with open("meas.csv", "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["consistency_model", "replication_factor", "time_bench1", "time_bench2"])
        writer.writeheader()
        for (consistency_model, replication_factor), (time_bench1, time_bench2) in results.items():
            writer.writerow({
                "consistency_model": consistency_model,
                "replication_factor": replication_factor,
                "time_bench1": time_bench1,
                "time_bench2": time_bench2
                })

