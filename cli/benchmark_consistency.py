#!/usr/bin/env python3

import os
import copy
import random
from collections import defaultdict
import tqdm

REPLICATION_FACTORS = [1,3,5]
CONSISTENCY_MODELS = ["LINEARIZABLE", "EVENTUAL"]


REQUESTS = [None for _ in range(10)]

for i in range(10):
    with open(f"./benchmark_data/requests_{i:02}.txt") as f:
        REQUESTS[i] = [line.strip().split(',') for line in f.readlines()]
        REQUESTS[i] = [[word.strip() for word in req] for req in REQUESTS[i]]

def calculate_indexes(node_index):
    physical_idx = 1 + node_index // 2
    logical_idx  = 1 + node_index  % 2

    if physical_idx == 1:
        logical_idx -= 1 # use bootstrap

    return physical_idx, logical_idx

def random_schedule(all_requests):
    all_requests = copy.deepcopy(all_requests)
    schedule = []

    def actives():
        return [node_index for node_index, reqs in enumerate(all_requests) if len(reqs) >= 1]

    while True:
        act = actives()
        if not act:
            break
        node_index = random.choice(act)
        schedule.append((node_index, all_requests[node_index].pop(0)))
    return schedule


def benchmark_driver(client_factory, consistency_model, replication_factor, schedule):
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

    dht = defaultdict(lambda: "")
    stale_reads = 0

    print("Start benchmarking...")
    for node_index, event in tqdm.tqdm(schedule):
        physical_idx, logical_idx = calculate_indexes(node_index)

        client.physical = f"vm{physical_idx}"
        client.logical = str(logical_idx)

        match event[0]:
            case "insert":
                client.modify("insert", event[1], event[2])
                dht[event[1]] += event[2]
            case "query":
                val = client.query(event[1])
                if val != dht.get(event[1], None):
                    stale_reads += 1
            case _:
                assert False
    print("Benchmarking done.")

    print("Cleaning up...")
    for physical in client.physical_urls:
        client.physical = physical
        client.killall()

    return stale_reads

def run_benchmarks(client_factory):
    results = {}
    schedule = random_schedule(REQUESTS)

    for replication_factor in REPLICATION_FACTORS:
        for consistency_model in CONSISTENCY_MODELS:
            result = benchmark_driver(client_factory, consistency_model, replication_factor, schedule)
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
        writer = csv.DictWriter(f, fieldnames=["consistency_model", "replication_factor", "stale_reads"])
        writer.writeheader()
        for (consistency_model, replication_factor), stale_reads in results.items():
            writer.writerow({
                "consistency_model": consistency_model,
                "replication_factor": replication_factor,
                "stale_reads": stale_reads
                })
        if CHORD_DOCKER:
            print()
            print(f.getvalue())


