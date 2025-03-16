#!/usr/bin/env python3

import os
import time
import threading
import tqdm

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


def calculate_indexes(node_index):
    physical_idx = 1 + node_index // 2
    logical_idx  = 1 + node_index  % 2

    if physical_idx == 1:
        logical_idx -= 1 # use bootstrap

    return physical_idx, logical_idx


def benchmark_driver(client_factory, consistency_model, replication_factor):
    print("Setting up...")

    client = client_factory()
    for physical in client.physical_urls:
        client.physical = physical
        client.killall()

    with tqdm.tqdm(total=10) as pbar:
        client.physical = "vm1"
        client.spawn_bootstrap(consistency_model, replication_factor)
        pbar.update(1)
        client.spawn()
        pbar.update(1)

        for physical in client.physical_urls:
            if physical == "vm1": continue
            client.physical = physical
            client.spawn()
            pbar.update(1)
            client.spawn()
            pbar.update(1)

    times_bench1 = [None for _ in range(10)]
    times_bench2 = [None for _ in range(10)]

    def node_driver(node_index, pbar):
        nonlocal times_bench1, times_bench2

        physical_idx, logical_idx = calculate_indexes(node_index)

        client = client_factory()
        client.physical = f"vm{physical_idx}"
        client.logical = str(logical_idx)

        t_start = time.time()
        for insert_key in INSERTS[node_index]:
            client.modify("insert", insert_key, INSERT_VALUE)
            pbar.update(1)
        t_end = time.time()
        times_bench1[node_index] = t_end-t_start

        t_start = time.time()
        for query_key in QUERIES[node_index]:
            client.query(query_key)
            pbar.update(1)
        t_end = time.time()
        times_bench2[node_index] = t_end-t_start

    print("Start benchmarking...")
    with tqdm.tqdm(total=sum(len(req) for req in INSERTS) + sum(len(req) for req in QUERIES)) as pbar:
        threads = [threading.Thread(target=node_driver, args=(node_index, pbar), daemon=False) for node_index in range(10)]
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
    import sys
    try:
        import configuration
    except ModuleNotFoundError:
        print("Please create the 'configuration.py' according to the 'configuration_template.py'.")
        sys.exit(1)
    import csv
    import cli

    CHORD_CLI_SSL_VERIFY = os.environ.get("CHORD_CLI_SSL_VERIFY","TRUE") != "FALSE"
    CHORD_DOCKER = os.environ.get("CHORD_DOCKER", None)

    if not CHORD_CLI_SSL_VERIFY:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if CHORD_DOCKER:
        import io


    if CHORD_DOCKER:
        input("Press <Enter> to start benchmarking.")

    client_factory = lambda: cli.Client(
            physical_urls=configuration.physical_urls,
            username=configuration.http_username,
            password=configuration.http_password,
            ssl_verify=CHORD_CLI_SSL_VERIFY
            )

    results = run_benchmarks(client_factory)

    if CHORD_DOCKER:
        f = io.StringIO(newline='')
    else:
        f = open("meas.csv", "w", newline='')
    with f:
        writer = csv.DictWriter(f, fieldnames=["consistency_model", "replication_factor", "time_bench1", "time_bench2"])
        writer.writeheader()
        for (consistency_model, replication_factor), (time_bench1, time_bench2) in results.items():
            writer.writerow({
                "consistency_model": consistency_model,
                "replication_factor": replication_factor,
                "time_bench1": time_bench1,
                "time_bench2": time_bench2
                })
        if CHORD_DOCKER:
            print()
            print(f.getvalue())


