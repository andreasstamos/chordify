import time
import cli
import copy
import threading

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


def benchmark_driver(client, consistency_model, replication_factor):
    # setup
    
    print("Setting up...")

    for physical in client.physical_urls:
        client.physical = physical
        client.killall()

    client.physical = "vm1"
    client.spawn_bootstrap(consistency_model, replication_factor)
    time.sleep(1)
    client.spawn()

    for physical in client.physical_urls:
        if physical == "vm1": continue
        client.physical = physical
        client.spawn()
        client.spawn()

    times = [None for _ in range(10)]
    def node_driver(node_index):
        nonlocal client, times

        physical_idx = 1 + node_index // 2
        logical_idx  = 1 + node_index  % 2

        if physical_idx == 1:
            logical_idx -= 1 # use bootstrap

        client = copy.deepcopy(client)
        client.physical = f"vm{physical_idx}"
        client.logical = str(logical_idx)
        
        t_start = time.time()

        for insert_key in INSERTS[node_index]:
            client.modify("insert", insert_key, INSERT_VALUE)

        t_end = time.time()

        times[node_index] = t_end-t_start

    print("Start benchmarking...")
    threads = [threading.Thread(target=node_driver, args=(node_index,), daemon=False) for node_index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print("Benchmarking done.")

    print("Cleaning up...")
    for physical in client.physical_urls:
        client.physical = physical
        client.killall()

if __name__ == "__main__":
    import configuration
    client = cli.Client(
            physical_urls=configuration.physical_urls,
            username=configuration.http_username,
            password=configuration.http_password)
    benchmark_driver(client, "LINEARIZABLE", 2)

