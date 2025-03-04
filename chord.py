from flask import Flask, request, jsonify
import threading
import hashlib
import sys
import json
import requests
import time

# TODO list:
# 1. Join/Depart -- DONE
# 2. Find proper position to insert in ring -- DONE
# 3. Actually implement insert/query/delete -- DONE
# 4. Replication
# 5. Properly handle key exchanges during join/depart -- WIP

# Question: What happens if two nodes hash to the same value? (Exceedingly rare, but still)

# TODO: Maybe do not wait for response by default?

app = Flask(__name__)

def send_request(ip, port, endpoint, data, return_resp=False):
    url = f"http://{ip}:{port}/{endpoint}"
    try:
        response = requests.post(url, json=data)
        if return_resp:
            return response.json()
        else:
            return response.text
    except Exception as e:
        print("Error sending request:", e)
        return None

class ChordNode:
    def __init__(self, ip, port, replication_factor=3, consistency_model='eventual', is_bootstrap=False):
        self.ip = ip
        self.port = port # int(port)
        self.node_id = self.hash_id(f"{ip}:{port}")

        self.successor_ip = self.ip if is_bootstrap else None
        self.successor_port = self.port if is_bootstrap else None
        self.successor_id = self.node_id if is_bootstrap else None

        self.predecessor_ip = self.ip if is_bootstrap else None
        self.predecessor_port = self.port if is_bootstrap else None
        self.predecessor_id = self.node_id if is_bootstrap else None

        self.is_bootstrap = is_bootstrap

        self.keys_start = self.node_id + 1
        self.keys_end = self.node_id

        self.data_store = {}
        self.replication_factor = replication_factor
        self.consistency_model = consistency_model

    def hash_id(self, value):
        return int(hashlib.sha1(value.encode()).hexdigest(), 16)

    def lies_in_range(self, start, end, key_hash):
        return (start <= key_hash <= end) or \
            (end < start <= key_hash) or \
            (key_hash <= end < start)

    def is_responsible(self, key_hash):
        return self.lies_in_range(self.keys_start, self.keys_end, key_hash)
        

    def forward_request(self, initial_ip, initial_port, operation, key, value=None):
        data = {"initial_ip": initial_ip, "initial_port": initial_port, "key": key, "value": value}
        print(f"Forwarding {operation} request for key '{key}' to the next node.")
        return send_request(self.successor_ip, self.successor_port, operation, data)

    def replicate(self, operation, key, value=None):
        pass

    #TODO: Locks?

    def insert(self, initial_ip, initial_port, key, value):
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            if key in self.data_store:
                self.data_store[key] += value
            else:
                self.data_store[key] = value
            
            self.replicate('insert', key, value)
            # Inform initial node of result
            send_request(initial_ip, initial_port, "insert_resp", {})
            return f"Inserted/Updated key '{key}' with value '{self.data_store[key]}' at node {self.node_id}"
        else:
            return self.forward_request(initial_ip, initial_port, "insert", key, value)

    def query_star(self, initial_ip, initial_port, value={}):
        value = value | self.data_store
        if (self.successor_ip == initial_ip and self.successor_port == initial_port):
            # We reached the end, send result back to initial node
            send_request(initial_ip, initial_port, "query_star_resp", {"result": value})
        else:
            self.forward_request(initial_ip, initial_port, "query_star", "*", value)

    def query(self, initial_ip, initial_port, key, value=None):
        # if key == "*":
        #     return str(self.data_store)
        
        # We assume that key != "*" here
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            res = self.data_store.get(key, "Key not found")

            # Inform initial node of result
            send_request(initial_ip, initial_port, "query_resp", {"result": res})
            
        else:
            return self.forward_request(initial_ip, initial_port, "query", key, value)

    def delete(self, initial_ip, initial_port, key, value=None):
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            if key in self.data_store:
                del self.data_store[key]
                self.replicate('delete', key)

                # Inform initial node of result

                send_request(initial_ip, initial_port, "delete_resp", {"status": "success"})
                return f"Deleted key '{key}' from node {self.node_id}"
            else:
                # Inform initial node of result

                send_request(initial_ip, initial_port, "delete_resp", {"status": "key_not_found"})
                return "Key not found"
        else:
            return self.forward_request(initial_ip, initial_port, "delete", key, value)

    def update_pred_and_succ(self, pred_ip, pred_port, succ_ip, succ_port, data_store={}):
        print(f"Entering update pred and succ, data_store={data_store}")
        pred_id = self.hash_id(f"{pred_ip}:{pred_port}")
        self.predecessor_ip = pred_ip
        self.predecessor_port = int(pred_port)
        self.predecessor_id = pred_id

        succ_id = self.hash_id(f"{succ_ip}:{succ_port}")
        self.successor_ip = succ_ip
        self.successor_port = int(succ_port)
        self.successor_id = succ_id

        self.keys_start = self.predecessor_id + 1 # self.keys_end has already been defined
        self.data_store |= data_store # TODO: Maybe plain = instead of |=?

        print(f"Successfully joined chord ring with pred {self.predecessor_id} and succ {self.successor_id}", flush=True)
        print(f"Key range start: {self.keys_start}", flush=True)
        print(f"Key range end: {self.keys_end}", flush=True)

        return "Successfully updated pred and succ"

    def update_pred_info(self, new_node_ip, new_node_port, departing=False, data_store={}):
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        self.predecessor_ip = new_node_ip
        self.predecessor_port = int(new_node_port)
        self.predecessor_id = new_node_id

        old_start = self.keys_start
        self.keys_start = new_node_id + 1

        if departing:
            # In this case, the node before us left, so we have to augment our data_store
            self.data_store |= data_store
            return {"status": "success"}
        else:
            ret_dict = {}
            for key, value in self.data_store.items():
                if self.lies_in_range(old_start, self.keys_start - 1, self.hash_id(key)):
                    ret_dict[key] = value
            for key in list(ret_dict.keys()):
                del self.data_store[key]
            return {"status": "success", "data_store": ret_dict}


    def update_succ_info(self, new_node_ip, new_node_port):
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        self.successor_ip = new_node_ip
        self.successor_port = int(new_node_port)
        self.successor_id = new_node_id

        return "Successfully updated succ info"

    def find_insert_position(self, new_node_ip, new_node_port):
        new_node_port = int(new_node_port)
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        print(f"Trying to insert {new_node_id}")
        if (self.successor_id == self.node_id) or \
        (self.node_id < new_node_id <= self.successor_id) or \
        (self.node_id > self.successor_id and (new_node_id > self.node_id or new_node_id <= self.successor_id)):
            response = f"{self.ip} {self.port} {self.successor_ip} {self.successor_port}"
            resp = send_request(
                self.successor_ip, self.successor_port,
                "update_pred_info",
                {"new_node_ip": new_node_ip, "new_node_port": new_node_port, "departing": False, "data_store": {}},
                return_resp=True
            )
            if resp is not None and resp.get("status") == "success":
                new_data_store = resp.get("data_store", {})
            else:
                new_data_store = {}
            cmd_data = {
                "pred_ip": self.ip,
                "pred_port": self.port,
                "succ_ip": self.successor_ip,
                "succ_port": self.successor_port,
                "data_store": new_data_store
            }
            self.successor_ip = new_node_ip
            self.successor_port = new_node_port
            self.successor_id = new_node_id
            send_request(new_node_ip, new_node_port, "update_pred_and_succ", cmd_data)
            return response
        else:
            data = {"new_node_ip": new_node_ip, "new_node_port": new_node_port}
            send_request(self.successor_ip, self.successor_port, "find_insert_position", data)
            return "Forwarded find_insert_position request"

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

            old_start = self.keys_start

            self.keys_start = new_node_id + 1
            print(response, flush=True)

            ret_dict = {}
            for key, value in self.data_store.items():
                if self.lies_in_range(old_start, self.keys_start - 1, self.hash_id(key)):
                    ret_dict[key] = value
            
            for key in ret_dict.keys():
                del self.data_store[key]
            send_request(
                new_ip, new_port, "update_pred_and_succ",
                {"pred_ip": self.ip, "pred_port": self.port, "succ_ip": self.ip, "succ_port": self.port, "data_store": ret_dict}
            )
            return response
        else:
            # insert_after_ip, insert_after_port, successor_ip, successor_port = self.find_insert_position(new_ip, new_port).split()

            self.find_insert_position(new_ip, new_port)
            # response = f"JOIN_ACCEPTED {insert_after_ip} {insert_after_port} {successor_ip} {successor_port}"
            # print(response, flush=True)

            # Also inform successor to update info
            # cmd = f"update_pred_info {new_ip} {new_port}"
            # print(f"Updating {successor_ip} {successor_port}")
            # resp = send_request(successor_ip, int(successor_port), cmd)
            # print(resp)

            # TODO: ?
            response = f"JOIN_ACCEPTED {self.ip} {self.port} {self.ip} {self.port}"
            return response

    def join_existing(self, bootstrap_ip, bootstrap_port):
        try:
            join_cmd = {"new_node_info": f"{self.ip}:{self.port}"}
            send_request(bootstrap_ip, bootstrap_port, "join", join_cmd)
        except Exception as e:
            print("Error joining chord ring:", e, flush=True)

    def depart(self):
        # All we have to do here is inform our predecessor and successor
        print(f"Node {self.node_id} beginning to depart", flush=True)

        # TODO: Maybe issue a single request if there are only two nodes remaining?        
        resp = send_request(
            self.successor_ip, int(self.successor_port),
            "update_pred_info",
            {"new_node_ip": self.predecessor_ip, "new_node_port": self.predecessor_port, "departing": True, "data_store": self.data_store}
        )
        print(resp, flush=True)
        resp = send_request(
            self.predecessor_ip, int(self.predecessor_port),
            "update_succ_info",
            {"new_node_ip": self.successor_ip, "new_node_port": self.successor_port}
        )
        print(resp, flush=True)

        return f"Node {self.node_id} is departing from the network."

    def print_overlay(self):
        print("Overlay (Chord Ring Topology):", flush=True)
        print(f"Node {self.node_id} -> Successor: {self.successor_id} | Predecessor: {self.predecessor_id}", flush=True)
        print(f"keys_start={self.keys_start}, keys_end={self.keys_end}", flush=True)

    def debug_print_keys(self):
        print("Printing Hash Table:", flush=True)
        for key, value in self.data_store.items():
            print(f"Key: {key}, Value: {value}, hash: {self.hash_id(key)}", flush=True)
        print("Done printing Hash Table", flush=True)


@app.route('/insert', methods=['POST'])
def handle_insert():
    data = request.get_json()
    initial_ip = data.get('initial_ip')
    initial_port = data.get('initial_port')
    key = data.get('key')
    value = data.get('value')
    response = chord_node.insert(initial_ip, initial_port, key, value)
    return jsonify({"response": response})

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    initial_ip = data.get('initial_ip')
    initial_port = data.get('initial_port')
    key = data.get('key')
    response = chord_node.query(initial_ip, initial_port, key)
    return jsonify({"response": response})

@app.route('/query_star', methods=['POST'])
def handle_query_star():
    data = request.get_json()
    initial_ip = data.get('initial_ip')
    initial_port = data.get('initial_port')
    value = data.get('value', {})
    response = chord_node.query_star(initial_ip, initial_port, value)
    return jsonify({"response": response})

@app.route('/delete', methods=['POST'])
def handle_delete():
    data = request.get_json()
    initial_ip = data.get('initial_ip')
    initial_port = data.get('initial_port')
    key = data.get('key')
    response = chord_node.delete(initial_ip, initial_port, key)
    return jsonify({"response": response})

@app.route('/join', methods=['POST'])
def handle_join():
    data = request.get_json()
    new_node_info = data.get('new_node_info')
    response = chord_node.join_request(new_node_info)
    return jsonify({"response": response})

@app.route('/depart', methods=['POST'])
def handle_depart():
    response = chord_node.depart()
    return jsonify({"response": response})

@app.route('/find_insert_position', methods=['POST'])
def handle_find_insert_position():
    data = request.get_json()
    new_node_ip = data.get('new_node_ip')
    new_node_port = data.get('new_node_port')
    response = chord_node.find_insert_position(new_node_ip, new_node_port)
    return jsonify({"response": response})

@app.route('/update_pred_info', methods=['POST'])
def handle_update_pred_info():
    data = request.get_json()
    new_node_ip = data.get('new_node_ip')
    new_node_port = data.get('new_node_port')
    departing = data.get('departing', False)
    ds = data.get('data_store', {})
    response = chord_node.update_pred_info(new_node_ip, new_node_port, departing, ds)
    return jsonify(response)


@app.route('/update_succ_info', methods=['POST'])
def handle_update_succ_info():
    data = request.get_json()
    new_node_ip = data.get('new_node_ip')
    new_node_port = data.get('new_node_port')
    response = chord_node.update_succ_info(new_node_ip, new_node_port)
    return jsonify({"response": response})

@app.route('/update_pred_and_succ', methods=['POST'])
def handle_update_pred_and_succ():
    data = request.get_json()
    pred_ip = data.get('pred_ip')
    pred_port = data.get('pred_port')
    succ_ip = data.get('succ_ip')
    succ_port = data.get('succ_port')
    ds = data.get('data_store', {})
    response = chord_node.update_pred_and_succ(pred_ip, pred_port, succ_ip, succ_port, ds)
    return jsonify({"response": response})

@app.route('/insert_resp', methods=['POST'])
def handle_insert_resp():
    print("Successful insertion")
    return jsonify({"response": "Ok insert"})

@app.route('/query_resp', methods=['POST'])
def handle_query_resp():
    data = request.get_json()
    result = data.get('result')
    print("Query result:", result)
    return jsonify({"response": "Ok query"})

@app.route('/query_star_resp', methods=['POST'])
def handle_query_star_resp():
    data = request.get_json()
    result = data.get('result')
    print("Query star result:", result)
    return jsonify({"response": "Ok query_star"})

@app.route('/delete_resp', methods=['POST'])
def handle_delete_resp():
    data = request.get_json()
    status = data.get('status')
    if status == "success":
        print("Successful deletion")
    else:
        print("Key not found")
    return jsonify({"response": "Ok delete"})

def chord_cli(chord_node, ip, port):
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
                response = chord_node.insert(ip, port, key, value)
                print(response, flush=True)
            elif cmd == "delete":
                if len(args) < 2:
                    print("Usage: delete <key>", flush=True)
                    continue
                key = args[1]
                response = chord_node.delete(ip, port, key)
                print(response, flush=True)
            elif cmd == "query":
                if len(args) < 2:
                    print("Usage: query <key>", flush=True)
                    continue
                key = args[1]
                if key == "*":
                    response = chord_node.query_star(ip, port, {})
                else:
                    response = chord_node.query(ip, port, key)
                print(response, flush=True)
            elif cmd == "depart":
                if not chord_node.is_bootstrap:
                    response = chord_node.depart()
                    print(response, flush=True)
                    break
                else:
                    print("Bootstrap node cannot depart", flush=True)
            elif cmd == "overlay":
                chord_node.print_overlay()
            elif cmd == "debug_print_keys":
                chord_node.debug_print_keys()
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

def start_flask_app(ip, port):
    app.run(host=ip, port=port, threaded=True)

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
        flask_thread = threading.Thread(target=start_flask_app, args=(node_ip, node_port))
        flask_thread.daemon = True
        flask_thread.start()
        # TODO: alternative?       
        time.sleep(1)
        chord_node.join_existing(bootstrap_ip, bootstrap_port)
        chord_cli(chord_node, node_ip, node_port)
    else:
        bootstrap_ip = "127.0.0.1"
        bootstrap_port = 5000
        chord_node = ChordNode(bootstrap_ip, bootstrap_port, replication_factor=3, consistency_model="eventual", is_bootstrap=True)
        flask_thread = threading.Thread(target=start_flask_app, args=(bootstrap_ip, bootstrap_port))
        flask_thread.daemon = True
        flask_thread.start()
        chord_cli(chord_node, bootstrap_ip, bootstrap_port)