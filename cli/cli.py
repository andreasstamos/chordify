#!/usr/bin/env python3
import readline
import sys
import os
import requests

COMMANDS = [
    "insert", "delete", "query", "depart", "overlay",
    "exit", "list-physicals", "set-physical", "list-logicals", "set-logical",
    "show-selected", "spawn", "spawn-bootstrap", "killall", "help"
]

def autocompleter(text, state):
    options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

class Client:
    def __init__(self, physical_urls, username=None, password=None):
        self.physical_urls = physical_urls
        self.physical = None
        self.logical = None

        if username is not None:
            self.auth = requests.auth.HTTPBasicAuth(username, password)
        else:
            self.auth = None

    def send_request(self, endpoint, data={}, manager=False):
        if manager:
            response = requests.post(f"{self.physical_url}/management/{endpoint}", auth=self.auth, json=data)
        else:
            response = requests.post(f"{self.url}/api/{endpoint}", auth=self.auth, json=data)
        response = response.json()
        if "error" in response:
            print(f"Response Error: {response['error']}", flush=True)
            print(f"Exiting CLI.", flush=True)
            sys.exit(1)

        if manager:
            return response
        else:
            return response["response"]

    @property
    def url(self):
        return f"{self.physical_url}/{self.logical}"

    @property
    def physical_url(self):
        return self.physical_urls[self.physical]

    def list_logicals(self):
        return self.send_request("list", manager=True)

    def spawn(self):
        return self.send_request("spawn", manager=True)

    def spawn_bootstrap(self, consistency_model, replication_factor):
        return self.send_request("spawnBootstrap", manager=True, data={
            "consistency_model": consistency_model,
            "replication_factor": replication_factor
            })

    def killall(self):
        return self.send_request("killall", manager=True)
  

    def modify(self, operation, key, value=None):
        return self.send_request("modify", {"operation": operation, "key": key, **({"value":value} if value is not None else {})})

    def query(self, key):
        return self.send_request("query", {"key": key})

    def depart(self):
        resp = self.send_request("depart")
        self.logical = None
        return resp

    def overlay(self):
        return self.send_request("overlay")

    def cli(self):
        print("Chord DHT Client. Type 'help' for available commands.", flush=True)
        while True:
            try:
                command = input("\033[96mChord> \033[0m").strip()
                if not command:
                    continue
                args = command.split()
                cmd = args[0].lower()
                if cmd in ["insert", "delete", "query", "depart", "overlay"]:
                    if self.physical is None:
                        print("Please set a physical node.", flush=True)
                        continue
                    if self.logical is None:
                        print("Please set a logical node.", flush=True)
                        continue
                if cmd == "insert":
                    if len(args) < 3:
                        print("Usage: insert <key> <value>", flush=True)
                        continue
                    key, value = args[1], args[2]
                    response = self.modify("insert", key, value)
                    print(response, flush=True)
                elif cmd == "delete":
                    if len(args) < 2:
                        print("Usage: delete <key>", flush=True)
                        continue
                    key = args[1]
                    response = self.modify("delete", key)
                    print(response, flush=True)
                elif cmd == "query":
                    if len(args) < 2:
                        print("Usage: query <key>", flush=True)
                        continue
                    key = args[1]
                    response = self.query(key)
                    print(response, flush=True)
                elif cmd == "depart":
                    response = self.depart()
                    print(response, flush=True)
                elif cmd == "overlay":
                    nodes = self.overlay()
                    print("Overlay (Chord Ring Topology):", flush=True)
                    for node in nodes:
                        print(f"Node {node['url']}", flush=True)
                        print(f"  Predecessor {node['successor_url']}", flush=True)
                        print(f"  Successor {node['predecessor_url']}", flush=True)
                        print(f"  Key Range {node['keys_start']} -- {node['keys_end']}", flush=True)
                elif cmd == "exit":
                    break
                elif cmd == "list-physicals":
                    print("Physical Node ID   -   Physical Node URL", flush=True)
                    for physical_id, physical_url in self.physical_urls.items():
                        print(f"{physical_id}   -   {physical_url}")
                elif cmd == "set-physical":
                    if len(args) < 2:
                        print("Usage: set-physical <Physical Node ID>", flush=True)
                        continue
                    if args[1] not in self.physical_urls:
                        print("Physical Node ID does not exist.", flush=True)
                        continue
                    self.physical = args[1]
                    self.logical = None
                elif cmd == "list-logicals":
                    if self.physical is None:
                        print("Please set a physical node.", flush=True)
                        continue
                    resp = self.list_logicals()
                    print(resp)
                elif cmd == "set-logical":
                    if len(args) < 2:
                        print("Usage: set-logical <Logical Node ID>", flush=True)
                        continue
                    if self.physical is None:
                        print("Please set a physical node.", flush=True)
                        continue
                    self.logical = args[1]
                elif cmd == "show-selected":
                    print("Physical Node:", flush=True)
                    print(f"  ID: {self.physical}", flush=True)
                    print(f"  URL: {self.physical_url}", flush=True)
                    print("Logical Node:", flush=True)
                    print(f"  ID: {self.logical}", flush=True)
                    print(f"  URL: {self.url}", flush=True)
                elif cmd == "spawn":
                    if self.physical is None:
                        print("Please set a physical node.", flush=True)
                        continue
                    resp = self.spawn()
                    print(resp, flush=True)
                elif cmd == "spawn-bootstrap":
                    if len(args) < 3:
                        print("Usage: spawn-bootstrap <Consistency Model> <Replication Factor>", flush=True)
                        continue
                    if args[1] not in ["LINEARIZABLE", "EVENTUAL"]:
                        print("Unsupported Consistency Model.", flush=True)
                        continue
                    try:
                        rf = int(args[2])
                        if rf < 1:
                            print("Replication Factor must be a positive interger.", flush=True)
                            continue
                    except ValueError:
                        print("Replication Factor must be a positive interger.", flush=True)
                        continue
                    if self.physical is None:
                        print("Please set a physical node.", flush=True)
                        continue
                    resp = self.spawn_bootstrap(consistency_model=args[1], replication_factor=int(args[2]))
                    print(resp, flush=True)
                elif cmd == "killall":
                    if self.physical is None:
                        print("Please set a physical node.", flush=True)
                        continue
                    resp = self.killall()
                    print(resp, flush=True)
                elif cmd == "help":
                    print("Available commands:", flush=True)
                    print("-- Node Selection --", flush=True)
                    print(" list-physicals        - Lists Physical nodes", flush=True)
                    print(" set-physical          - Sets current Physical node", flush=True)
                    print(" list-logicals         - Lists Logical Nodes (in the current Physical Node)", flush=True)
                    print(" set-logical           - Sets current Logical node (in the current Physical Node)", flush=True)
                    print(" show-selected         - Shows currently selected Physical and Logical node", flush=True)
                    print("-- Physical Node Management -- ")
                    print(" spawn-bootstrap       - Spawns a new Bootstrap Logical node (at the current Physical Node - if it the designated node)",
                          flush=True)
                    print(" spawn                 - Spawns a new Logical node (at the current Physical Node)", flush=True)
                    print(" killall               - Kills all Logical nodes (in the current Physical Node)", flush=True)
                    print("-- Chord Operations -- ")

                    print(" insert <key> <value>  - Insert or update a <key,value> pair", flush=True)
                    print(" delete <key>          - Delete the specified key", flush=True)
                    print(" query <key>           - Query for the specified key (use '*' for all keys)", flush=True)
                    print(" depart                - Gracefully depart from the DHT", flush=True)
                    print(" overlay               - Print the network topology", flush=True)
                    print("-- CLI Operations -- ")
                    print(" exit                  - Exit the CLI", flush=True)
                    print(" help                  - Show this help message", flush=True)
                else:
                    print("Unknown command. Type 'help' for available commands.", flush=True)
            except KeyboardInterrupt:
                print("\nExiting CLI.", flush=True)
                break

if __name__ == "__main__":
    import configuration
    client = Client(
            physical_urls=configuration.physical_urls,
            username=configuration.http_username,
            password=configuration.http_password)

    readline.set_completer(autocompleter)
    delims = readline.get_completer_delims()
    readline.set_completer_delims(delims.replace('-', ''))
    readline.parse_and_bind("tab: complete")

    client.cli()

