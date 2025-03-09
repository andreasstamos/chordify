import requests
import readline

class CLI:
    def __init__(self, url):
        self.url = url

    def send_request(self, endpoint, data):
        response = requests.post(f"{self.url}/api/{endpoint}", json=data)
        print(response)
        return response.json()["response"]
    
    def modify(self, operation, key, value):
        return self.send_request("modify", {"operation": operation, "key": key, "value": value})

    def query(self, key):
        return self.send_request("query", {"key": key})

    def depart(self):
        return self.send_request("depart", None)

    def overlay(self):
        return self.send_request("overlay", None)
    
    def run(self):
        print("Chord DHT Client. Type 'help' for available commands.", flush=True)
        while True:
            try:
                command = input("\033[96mChord> \033[0m").strip()
                if not command:
                    continue
                args = command.split()
                cmd = args[0].lower()
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
                    response = self.modify("delete", key, None)
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
                    break
                elif cmd == "overlay":
                    nodes = self.overlay()
                    print("Overlay (Chord Ring Topology):", flush=True)
                    for node in nodes:
                        print(f"Node {node['url']}")
                        print(f"  Predecessor {node['successor_url']}")
                        print(f"  Successor {node['predecessor_url']}")
                        print(f"  Key Range {node['keys_start']} -- {node['keys_end']}")
                elif cmd == "exit":
                    break

#                elif cmd == "debug_print_keys":
#                    chord_node.debug_print_keys()
                elif cmd == "help":
                    print("Available commands:", flush=True)
                    print(" insert <key> <value>  - Insert or update a <key,value> pair", flush=True)
                    print(" delete <key>          - Delete the specified key", flush=True)
                    print(" query <key>           - Query for the specified key (use '*' for all keys)", flush=True)
                    print(" depart                - Gracefully depart from the DHT", flush=True)
                    print(" overlay               - Print the network topology", flush=True)
                    print(" help                  - Show this help message", flush=True)
                else:
                    print("Unknown command. Type 'help' for available commands.", flush=True)
            except KeyboardInterrupt:
                print("\nExiting CLI.", flush=True)
                break
    #        except Exception as e:
    #            print("Error:", e, flush=True)

if __name__ == "__main__":
    import os
    NODE_URL = os.environ["NODE_URL"]
    cli = CLI(url=NODE_URL)
    cli.run()

