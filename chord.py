import socket
import threading
import hashlib
import sys

# TODO list:
# 1. Join/Depart -- WIP
# 2. Find proper position to insert in ring
# 3. Actually implement insert/query/delete
# 4. Replication

# Question: What happens if two nodes hash to the same value? (Exceedingly rare, but still)

def send_request(ip, port, msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    s.sendall(msg.encode())
    response = s.recv(1024).decode()
    s.close()
    return response

class ChordNode:
    def __init__(self, ip, port, replication_factor=3, consistency_model='eventual', is_bootstrap=False):
        self.ip = ip
        self.port = port
        self.node_id = self.hash_id(f"{ip}:{port}")

        self.successor_ip = self.ip if is_bootstrap else None
        self.successor_port = self.port if is_bootstrap else None
        self.successor_id = self.node_id if is_bootstrap else None

        self.predecessor_ip = self.ip if is_bootstrap else None
        self.predecessor_port = self.port if is_bootstrap else None
        self.predecessor_id = self.node_id if is_bootstrap else None

        self.is_bootstrap = is_bootstrap

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
        print("Entered here")
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
            elif command == 'find_insert_position':
                response = self.find_insert_position(args[1], args[2])
            elif command == 'update_pred_info':
                response = self.update_pred_info(args[1], args[2])
            elif command == 'update_succ_info':
                response = self.update_succ_info(args[1], args[2])
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
                self.data_store[key] += value # TODO: Concat instead of +=
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

    def update_pred_info(self, new_node_ip, new_node_port):
        print("Entered update_pred_info")
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        self.predecessor_ip = new_node_ip
        self.predecessor_port = int(new_node_port)
        self.predecessor_id = new_node_id

        return "Successfully updated pred info"
    
    def update_succ_info(self, new_node_ip, new_node_port):
        print("Entered update_succ_info")
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        self.successor_ip = new_node_ip
        self.successor_port = int(new_node_port)
        self.successor_id = new_node_id

        return "Successfully updated succ info"

    def find_insert_position(self, new_node_ip, new_node_port):
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        print(f"Trying to insert {new_node_id}")
        # In any of these cases, we are the predecessor of the new node
        if (self.successor_id == self.node_id) or \
            (self.node_id < new_node_id <= self.successor_id) or \
                (self.node_id > self.successor_id and (new_node_id > self.node_id or new_node_id <= self.successor_id)):
            response = f"{self.ip} {self.port} {self.successor_ip} {self.successor_port}"
            self.successor_ip = new_node_ip
            self.successor_port = new_node_port
            self.successor_id = new_node_id

            return response
        
        # Otherwise, we have to forward the request to our successor
        cmd = f"find_insert_position {new_node_ip} {new_node_port}"
        return send_request(self.successor_id, self.successor_port, cmd)

    def join_request(self, new_node_info):
        try:
            new_ip, new_port = new_node_info.split(':')
            new_port = int(new_port)
        except ValueError:
            return "Error: Invalid join information format. Expected 'ip:port'."
        new_node_id = self.hash_id(new_node_info)
        print(f"Received join request from node {new_node_id} ({new_node_info})", flush=True)

        if self.successor_id == self.node_id and self.predecessor_id == self.node_id:
            response = f"JOIN_ACCEPTED {self.ip} {self.port} {self.ip} {self.port}"
            self.predecessor_ip = self.successor_ip = new_ip
            self.predecessor_port = self.successor_port = new_port
            self.predecessor_id = self.successor_id = new_node_id
            print(response, flush=True)
            return response
        else:
            insert_after_ip, insert_after_port, successor_ip, successor_port = self.find_insert_position(new_ip, new_port).split()
            response = f"JOIN_ACCEPTED {insert_after_ip} {insert_after_port} {successor_ip} {successor_port}"
            print(response, flush=True)

            # Also inform successor to update info
            cmd = f"update_pred_info {new_ip} {new_port}"
            print(f"Updating {successor_ip} {successor_port}")
            resp = send_request(successor_ip, int(successor_port), cmd)
            print(resp)

            return response

    def join_existing(self, bootstrap_ip, bootstrap_port):
        try:
            join_cmd = f"join {self.ip}:{self.port}"
            response = send_request(bootstrap_ip, bootstrap_port, join_cmd)
            print("Join response:", response, flush=True)

            parts = response.split()
            if parts[0] == "JOIN_ACCEPTED" and len(parts) >= 5:
                pred_ip = parts[1]
                pred_port = parts[2]
                succ_ip = parts[3]
                succ_port = parts[4]

                self.predecessor_ip = pred_ip
                self.predecessor_port = pred_port
                self.predecessor_id = self.hash_id(f"{pred_ip}:{pred_port}")

                self.successor_ip = succ_ip
                self.successor_port = succ_port
                self.successor_id = self.hash_id(f"{succ_ip}:{succ_port}")

                print(f"Successfully joined chord ring with pred {self.predecessor_id} and succ {self.successor_id}")
            else:
                print("Unexpected join response format.", flush=True)
        except Exception as e:
            print("Error joining chord ring:", e, flush=True)

    def depart(self):
        # All we have to do here is inform our predecessor and successor
        print(f"Node {self.node_id} beginning to depart")

        # TODO: Maybe issue a single request if there are only two nodes remaining?

        cmd = f"update_pred_info {self.predecessor_ip} {self.predecessor_port}"
        print(f"Updating {self.successor_ip} {self.successor_port}")
        resp = send_request(self.successor_ip, int(self.successor_port), cmd)
        print(resp)

        cmd = f"update_succ_info {self.successor_ip} {self.successor_port}"
        print(f"Updating {self.predecessor_ip} {self.predecessor_port}")
        resp = send_request(self.predecessor_ip, int(self.predecessor_port), cmd)
        print(resp)

        return f"Node {self.node_id} is departing from the network."

    def print_overlay(self):
        print("Overlay (Chord Ring Topology):", flush=True)
        print(f"Node {self.node_id} -> Successor: {self.successor_id} | Predecessor: {self.predecessor_id}", flush=True)

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
                if not chord_node.is_bootstrap:
                    response = chord_node.depart()
                    print(response, flush=True)
                    break
                else:
                    print("Bootstrap node cannot depart")
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
