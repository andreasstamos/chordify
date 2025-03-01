import socket
import threading
import hashlib
import sys

class ChordNode:
    def __init__(self, ip, port, replication_factor=3, consistency_model='eventual', is_bootstrap=False):
        self.ip = ip
        self.port = port
        self.node_id = self.hash_id(f"{ip}:{port}")
        self.successor = self if is_bootstrap else None
        self.predecessor = self if is_bootstrap else None
        self.data_store = {}
        self.replication_factor = replication_factor
        self.consistency_model = consistency_model
        self.server_ready = threading.Event()

    def hash_id(self, value):
        return int(hashlib.sha1(value.encode()).hexdigest(), 16)

    def start_server(self):
        server_thread = threading.Thread(target=self.server_loop)
        server_thread.daemon = True
        server_thread.start()
        self.server_ready.wait()

    def server_loop(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.ip, self.port))
        s.listen(5)
        print(f"Node {self.node_id} listening on {self.ip}:{self.port}", flush=True)
        self.server_ready.set()
        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()

    def handle_client(self, conn, addr):
        try:
            data = conn.recv(1024).decode().strip()
            if not data:
                return
            args = data.split()
            command = args[0]
            if command == 'insert':
                if len(args) < 3:
                    response = "Error: Missing key or value."
                else:
                    key, value = args[1], args[2]
                    response = self.insert(key, value)
            elif command == 'query':
                if len(args) < 2:
                    response = "Error: Missing key."
                else:
                    key = args[1]
                    response = self.query(key)
            elif command == 'delete':
                if len(args) < 2:
                    response = "Error: Missing key."
                else:
                    key = args[1]
                    response = self.delete(key)
            elif command == 'join':
                if len(args) < 2:
                    response = "Error: Missing join info."
                else:
                    response = self.join_request(args[1])
            elif command == 'depart':
                response = self.depart()
            else:
                response = "Unknown command"
            conn.sendall(response.encode())
        except Exception as e:
            print("Error handling client:", e)
        finally:
            conn.close()

    def is_responsible(self, key_hash):
        return True

    def forward_request(self, operation, key, value=None):
        return f"Forwarding {operation} request for key '{key}' to the next node."

    def replicate(self, operation, key, value=None):
        pass

    #TODO: Locks?

    def insert(self, key, value):
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            if key in self.data_store:
                self.data_store[key] += value
            else:
                self.data_store[key] = value
            self.replicate('insert', key, value)
            return f"Inserted/Updated key '{key}' with value '{self.data_store[key]}' at node {self.node_id}"
        else:
            return self.forward_request('insert', key, value)

    def query(self, key):
        if key == "*":
            return str(self.data_store)
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            return self.data_store.get(key, "Key not found")
        else:
            return self.forward_request('query', key)

    def delete(self, key):
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            if key in self.data_store:
                del self.data_store[key]
                self.replicate('delete', key)
                return f"Deleted key '{key}' from node {self.node_id}"
            else:
                return "Key not found"
        else:
            return self.forward_request('delete', key)

    def find_insert_position(self, new_node_id):
        current = self
        while True:
            if current.successor == current:
                break
            if current.node_id < new_node_id <= current.successor.node_id:
                break
            if current.node_id > current.successor.node_id:
                if new_node_id > current.node_id or new_node_id <= current.successor.node_id:
                    break
            current = current.successor
            if current == self:
                break
        return current

    def join_request(self, new_node_info):
        try:
            new_ip, new_port = new_node_info.split(':')
            new_port = int(new_port)
        except ValueError:
            return "Error: Invalid join information format. Expected 'ip:port'."
        new_node_id = self.hash_id(new_node_info)
        print(f"Received join request from node {new_node_id} ({new_node_info})", flush=True)

        if self.successor == self and self.predecessor == self:
            response = f"JOIN_ACCEPTED {self.node_id} {self.node_id}"
            print(response, flush=True)
            return response
        else:
            insert_after = self.find_insert_position(new_node_id)
            successor = insert_after.successor
            response = f"JOIN_ACCEPTED {insert_after.node_id} {successor.node_id}"
            print(response, flush=True)
            return response

    def join_existing(self, bootstrap_ip, bootstrap_port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((bootstrap_ip, bootstrap_port))
            join_info = f"{self.ip}:{self.port}"
            s.sendall(f"join {join_info}".encode())
            response = s.recv(1024).decode()
            print("Join response:", response, flush=True)
            s.close()
            parts = response.split()
            if parts[0] == "JOIN_ACCEPTED" and len(parts) >= 3:
                pred_id = parts[1]
                succ_id = parts[2]
                self.predecessor = pred_id
                self.successor = succ_id
            else:
                print("Unexpected join response format.", flush=True)
        except Exception as e:
            print("Error joining chord ring:", e, flush=True)

    def depart(self):
        return f"Node {self.node_id} is departing from the network."

    def print_overlay(self):
        print("Overlay (Chord Ring Topology):", flush=True)
        print(f"Node {self.node_id} -> Successor: {self.successor} | Predecessor: {self.predecessor}", flush=True)

def chord_cli(chord_node):
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
                response = chord_node.insert(key, value)
                print(response, flush=True)
            elif cmd == "delete":
                if len(args) < 2:
                    print("Usage: delete <key>", flush=True)
                    continue
                key = args[1]
                response = chord_node.delete(key)
                print(response, flush=True)
            elif cmd == "query":
                if len(args) < 2:
                    print("Usage: query <key>", flush=True)
                    continue
                key = args[1]
                response = chord_node.query(key)
                print(response, flush=True)
            elif cmd == "depart":
                response = chord_node.depart()
                print(response, flush=True)
            elif cmd == "overlay":
                chord_node.print_overlay()
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
        except Exception as e:
            print("Error:", e, flush=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'join':
        if len(sys.argv) != 6:
            print("Usage: python chord.py join <bootstrap_ip> <bootstrap_port> <node_ip> <node_port>", flush=True)
            sys.exit(1)
        bootstrap_ip = sys.argv[2]
        bootstrap_port = int(sys.argv[3])
        node_ip = sys.argv[4]
        node_port = int(sys.argv[5])
        chord_node = ChordNode(node_ip, node_port, replication_factor=3, consistency_model="eventual")
        chord_node.join_existing(bootstrap_ip, bootstrap_port)
        chord_node.start_server()
        chord_cli(chord_node)
    else:
        bootstrap_ip = "127.0.0.1"
        bootstrap_port = 5000
        chord_node = ChordNode(bootstrap_ip, bootstrap_port, replication_factor=3, consistency_model="eventual", is_bootstrap=True)
        chord_node.start_server()
        chord_cli(chord_node)
