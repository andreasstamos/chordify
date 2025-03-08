from flask import Flask, request, jsonify
import threading
import hashlib
import sys
import json
import requests
import time
import readline
import inspect

# Question: What happens if two nodes hash to the same value?
# For n nodes, the probability is ~ n^2/(2*2**160). (sha1 is 160 bits)
# For 1000 nodes this is 3e-43. we can accept this.

# TODO: Maybe do not wait for response by default?

def with_kwargs(func):
    sig = inspect.signature(func)
    def inner(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        _kwargs = dict(bound.arguments)
        _kwargs.pop('_kwargs', None)
        _kwargs.pop('self', None)
        return func(*args, **kwargs, _kwargs=_kwargs)
    return inner

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
    def __init__(self, ip, port, replication_factor, consistency_model, is_bootstrap=False):
        self.ip = ip
        self.port = port # int(port)
        self.node_id = self.hash_id(f"{ip}:{port}")

        self.successor_ip = self.ip if is_bootstrap else None
        self.successor_port = self.port if is_bootstrap else None

        self.predecessor_ip = self.ip if is_bootstrap else None
        self.predecessor_port = self.port if is_bootstrap else None

        self.is_bootstrap = is_bootstrap

        self.keys_start = self.node_id + 1 if is_bootstrap else None
        self.keys_end = self.node_id if is_bootstrap else None

        self.replication_factor = 1 if is_bootstrap else None
        self.max_replication_factor = replication_factor if is_bootstrap else None

        self.data_store = [{}] if is_bootstrap else None
        self.consistency_model = consistency_model

        # Replication Example: Let the node No.4 be responsible for a key k and let replication factor be 3.
        # Then replicas must exist at nodes No.5 and No.6. The chain for chain replication is 4->5->6.
        # Writes are propagated to node No.4 and Reads are propagated to node No.6.
        # Node 6 must know for which keys it can answer requests.

        # README: join/depart. 
        # when join/depart we must ensure that replication factor is kept at k.
        # data_store[i] is the replica in distance i from the node responsible for a key.
        # reads are performed at data_store[-1].
        # when join the new node takes a complete 


        self.seq_to_succ = 0
        self.seq_from_prev = 0
        self.reorder_buffer_replication = dict()


    @staticmethod
    def hash_id(value):
        return int.from_bytes( hashlib.sha1(value.encode()).digest(), byteorder="little")

    @staticmethod
    def lies_in_range(start, end, key_hash):
        return (start <= key_hash <= end) or \
            (end < start <= key_hash) or \
            (key_hash <= end < start)

    def is_responsible(self, key_hash):
        return self.lies_in_range(self.keys_start, self.keys_end, key_hash)
        
    def forward_request(self, endpoint, data):
        print(f"Forwarding {endpoint} request to the next node.")
        return send_request(self.successor_ip, self.successor_port, endpoint, data)

    @with_kwargs
    def replicate_modify(self, seq, uid, initial_ip, initial_port, operation, key, value, distance, _kwargs=None):
        # chain replication
        # This function is called for "insert" operations.
        # It applies the change, then forwards the request if necessary, then returns.
        # The Sequence Number is required because the network might reorder the requests...
        # Chain replication assumes FIFO channels. This does not hold (necessarily) for HTTP Requests which might
        # end up in different TCP connections.
        # For a fact, modern versions of HTTP have been designed so as to avoid this "FIFOness". (aka if a browser requests two images in
        # different requests, it doesnt really care when rendering if they appear on the (random?) order they were asked, just that the
        # user sees images as fast as possible)
        # 
        # Seq=None is given by the initial caller (call that doesnt come from the network)

        if seq is not None:
            if seq != self.seq_from_prev:
                #print("REORDERING", seq, self.seq_from_prev) #TODO: remove
                self.reorder_buffer_replication[seq] = ("modify", _kwargs)
                return
            else:
                self.seq_from_prev += 1
       
        match operation:
            case "insert":
                if key in self.data_store[distance]:
                    self.data_store[distance][key] += value
                else:
                    self.data_store[distance][key] = value
            case "delete":
                del self.data_store[distance][key]

        if distance < self.replication_factor-1:
            self.forward_request("replicateModify", {**_kwargs, "seq": self.seq_to_succ, "distance": distance+1})
            self.seq_to_succ += 1
        else:
            send_request(initial_ip, initial_port, "modify_resp", {"uid": uid, "response": "ok modify"}) #TODO: better message
        
        self.replicate_wakeup()


    @with_kwargs
    def replicate_query(self, seq, uid, initial_ip, initial_port, key, distance, _kwargs=None):
        if seq is not None:
            if seq != self.seq_from_prev:
                #print("REORDERING", seq, self.seq_from_prev) TODO: remove
                self.reorder_buffer_replication[seq] = ("query", _kwargs)
                return
            else:
                self.seq_from_prev += 1
        
        if distance < self.replication_factor-1:
            self.forward_request("replicateQuery", {**_kwargs, "seq": self.seq_to_succ, "distance": distance+1})
            self.seq_to_succ += 1
        else:
            res = self.data_store[-1].get(key, None)
            # Inform initial node of result
            send_request(initial_ip, initial_port, "query_resp", {"uid": uid, "result": res})

        self.replicate_wakeup()

    def replicate_wakeup(self):
        # wakeup reorder buffer
        # TODO: I cannot test this code.... Check it out. We might as well leave it out.
        # A reordering is (probably?) a rare event and will probably not appear when evaluating this project.
        # IF however it happens to appear and the app blows up it might be worse than an inconsistency which might go unnoticed.
        # (highly the opposite of what would apply to a real system!)
        # on the other hand, we can present it as BONUS feature...........
        if min(self.reorder_buffer_replication.keys(), default=None) == self.seq_from_prev:
            seq_wakeup = min(self.reorder_buffer_replication.keys())
            (op, kwargs) = self.reorder_buffer_replication[seq_wakeup]
            del self.reorder_buffer_replication[seq_wakeup]
            match op:
                case "modify":
                    self.replicate_modify(seq_wakeup, **kwargs)
                case "query":
                    self.replicate_query(seq_wakeup, **kwargs)

    #TODO: Locks?

    @with_kwargs
    def modify(self, uid, initial_ip, initial_port, operation, key, value, _kwargs=None):
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            self.replicate_modify(None, uid, initial_ip, initial_port, operation, key, value, 0)
        else:
            return self.forward_request("modify", _kwargs)
           
    @with_kwargs
    def query(self, uid, initial_ip, initial_port, key, _kwargs=None):
        # We assume that key != "*" here
        if self.consistency_model == "EVENTUAL":
            for data_store_i in self.data_store[::-1]:
                if key in data_store_i:
                    return send_request(initial_ip, initial_port, "query_resp", {"uid": uid, "result": data_store_i[key]})
            if self.successor_ip == initial_ip and self.successor_port == initial_port:
                return send_request(initial_ip, initial_port, "query_resp", {"uid": uid, "result": None})
            self.forward_request("query", _kwargs)
        else:
            # LINEARIZABLE
            key_hash = self.hash_id(key)
            if self.is_responsible(key_hash):
                self.replicate_query(None, uid, initial_ip, initial_port, key, 0)
            else:
                return self.forward_request("query", _kwargs)

    @with_kwargs
    def query_star(self, uid, initial_ip, initial_port, value=None, _kwargs=None):
        if (value is not None and self.ip == initial_ip and self.port == initial_port):
            print("Query star result:", value)
        else:
            if value is None:
                value = {}
            value = value | self.data_store[-1]
            self.forward_request("query_star", {**_kwargs, "value":value})
 
    def new_pred(self, new_node_ip, new_node_port):
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")

        ret_dict = {}
        for key, value in self.data_store[0].items():
            if self.lies_in_range(self.keys_start, new_node_id, self.hash_id(key)):
                ret_dict[key] = value

        new_data_store = [None for _ in range(self.replication_factor)]
        new_data_store[0] = ret_dict
        new_data_store[1:] = self.data_store[1:]

        if self.replication_factor < self.max_replication_factor:
            # increasing replication factor. preparing the appropriate for the new node.
            # max distance backwards from new node is the current node.
            new_data_store.append({k:v for k,v in self.data_store[0].items() if k not in ret_dict})

        send_request(new_node_ip, new_node_port, "joinResponse", { 
            "predecessor_ip": self.predecessor_ip,
            "predecessor_port": self.predecessor_port,
            "successor_ip": self.ip,
            "successor_port": self.port,
            "keys_start": self.keys_start,
            "keys_end":   new_node_id,
            "replication_factor": self.replication_factor if self.replication_factor==self.max_replication_factor else self.replication_factor+1,
            "max_replication_factor": self.max_replication_factor,
            "data_store": new_data_store})

        # inform my old predecessor to update his successor to new_node_ip
        send_request(self.predecessor_ip, self.predecessor_port, "update_succ_info", { 
            "new_node_ip": new_node_ip,
            "new_node_port": new_node_port})
        
        new_node_start = self.keys_start

        self.keys_start = new_node_id + 1

        self.predecessor_ip = new_node_ip
        self.predecessor_port = int(new_node_port)

        if self.replication_factor < self.max_replication_factor:
            self.inc_replication_factor(new_node_ip, new_node_port, 1, new_node_start, new_node_id)
            # it should stop at the new node. we have already given him the correct data.
        else:
            self.shift_up_replicas(0, self.keys_start, self.keys_end)

    def join_response(self, predecessor_ip, predecessor_port, successor_ip, successor_port, keys_start, keys_end,\
            replication_factor, max_replication_factor, data_store):
        self.predecessor_ip     = predecessor_ip
        self.predecessor_port   = predecessor_port
        self.successor_ip       = successor_ip
        self.successor_port     = successor_port
        self.keys_start         = keys_start
        self.keys_end           = keys_end
        self.replication_factor = replication_factor
        self.max_replication_factor = max_replication_factor
        self.data_store         = data_store

    @with_kwargs
    def inc_replication_factor(self, initial_ip, initial_port, distance, new_node_start, new_node_end, _kwargs=None):
        if initial_ip==self.ip and initial_port==self.port:
            return
        else:
            self.replication_factor += 1
            self.data_store.append({})
            for i in range(distance+1, self.replication_factor)[::-1]:
                self.data_store[i] = self.data_store[i-1] # distance increases
            self.data_store[distance] = self.data_store[distance-1]
            self.data_store[distance-1] = {k:v for k,v in self.data_store[distance].items() \
                    if not self.lies_in_range(new_node_start, new_node_end, self.hash_id(k))}
            self.data_store[distance] = {k:v for k,v in self.data_store[distance].items() \
                    if self.lies_in_range(new_node_start, new_node_end, self.hash_id(k))}

            self.forward_request("incReplicationFactor", {**_kwargs, "distance": distance+1})

    def shift_up_replicas(self, distance, exclude_start, exclude_end):
        for i in range(distance+2, self.replication_factor)[::-1]:
            self_data_store[i] = self_data_store[i-1] # distance increased
        if distance+1 < self.replication_factor:
            self.data_store[distance+1] =\
                    {k:v for k,v in self.data_store[distance].items() if\
                    not self.lies_in_range(exclude_start, exclude_end, self.hash_id(k))}
        self.data_store[distance] =\
                {k:v for k,v in self.data_store[distance].items() if\
                self.lies_in_range(exclude_start, exclude_end, self.hash_id(k))}

        if distance < self.replication_factor-1:
           self.forward_request("shiftUpReplicas", {
                "distance": distance+1,
                "exclude_start": exclude_start,
                "exclude_end":   exclude_end
                })

    @with_kwargs
    def join_request(self, new_node_ip, new_node_port, _kwargs=None):
        new_node_port = int(new_node_port)
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")

        if self.is_responsible(new_node_id):
            print(f"Trying to insert {new_node_id}")
            self.new_pred(new_node_ip, new_node_port)
        else:
            data = {"new_node_ip": new_node_ip, "new_node_port": new_node_port}
            self.forward_request("join", _kwargs)
            return "Forwarded join_request request"
    
    def join_existing(self, bootstrap_ip, bootstrap_port):
        join_cmd = {"new_node_ip": self.ip, "new_node_port": self.port}
        try:
            send_request(bootstrap_ip, bootstrap_port, "join", join_cmd)
        except Exception as e:
            print("Error joining chord ring:", e, flush=True)

    def update_succ_info(self, new_node_ip, new_node_port):
        new_node_id = self.hash_id(f"{new_node_ip}:{new_node_port}")
        self.successor_ip = new_node_ip
        self.successor_port = int(new_node_port)

        return "Successfully updated succ info"

    def depart(self):
        print(f"Node {self.node_id} beginning to depart", flush=True)

        send_request(self.predecessor_ip, self.predecessor_port, "update_succ_info",
                {"new_node_ip": self.successor_ip, "new_node_port": self.successor_port}
        )

        self.forward_request("departPred", {
            "keys_start": self.keys_start,
            "predecessor_ip": self.predecessor_ip,
            "predecessor_port": self.predecessor_port,
            "maxdistance_replica": self.data_store[-1]
            })

        exiting = True
        return f"Node {self.node_id} is departing from the network."

    def depart_pred(self, keys_start, predecessor_ip, predecessor_port, maxdistance_replica):
        self.keys_start       = keys_start
        self.predecessor_port = predecessor_port
        self.predecessor_ip   = predecessor_ip

        self.data_store[1] |= self.data_store[0]  # shift_down_replicas will then move this one unit of distance downwards
        return self.shift_down_replicas(None, None, 0, maxdistance_replica)
    
    def shift_down_replicas(self, initial_ip, initial_port, distance, maxdistance_replica):
        if initial_ip == self.ip and initial_port == self.port:
            return self.dec_replication_factor(None, None)

        for i in range(distance, self.replication_factor-1):
            self.data_store[i] = self.data_store[i+1]
        old_maxdistance_replica = self.data_store[-1]
        self.data_store[-1] = maxdistance_replica
   
        if distance < self.replication_factor-1:
            if initial_ip is None:
                initial_ip = self.ip
                initial_port = self.port
            self.forward_request("shiftDownReplicas", {
                "initial_ip": initial_ip,
                "initial_port": initial_port,
                "distance": distance+1,
                "maxdistance_replica": old_maxdistance_replica
                })

    def dec_replication_factor(self, initial_ip, initial_port):
        if initial_ip==self.ip and initial_port==self.port:
            return
        else:
            self.replication_factor -= 1
            self.data_store.pop()
            if initial_ip is None:
                initial_ip = self.ip
                initial_port = self.port
            self.forward_request("decReplicationFactor", {"initial_ip": initial_ip, "initial_port": initial_port})

    @with_kwargs
    def overlay(self, initial_ip, initial_port, nodes=None, _kwargs=None):
        if (nodes is not None and self.ip == initial_ip and self.port == initial_port):
            print("Overlay (Chord Ring Topology):", flush=True)
            for node in nodes:
                print(f"Node {node['ip']}:{node['port']}")
                print(f"  Predecessor {node['predecessor_ip']}:{node['predecessor_port']}")
                print(f"  Successor {node['successor_ip']}:{node['successor_port']}")
#            print(f"keys_start={self.keys_start}, keys_end={self.keys_end}", flush=True)
        else:
            node = {
                    "ip": self.ip,
                    "port": self.port,
                    "predecessor_ip": self.predecessor_ip,
                    "predecessor_port": self.predecessor_port,
                    "successor_ip": self.successor_ip,
                    "successor_port": self.successor_port
                    }
            if nodes is None:
                nodes = [node]
            else:
                nodes.append(node)
            self.forward_request("overlay", {**_kwargs, "nodes": nodes})
 
    def debug_print_keys(self):
        print("Printing Hash Table:", flush=True)
        for i, data_store_replica in enumerate(self.data_store):
            for key, value in data_store_replica.items():
                print(f"Key: {key}, Value: {value}, hash: {self.hash_id(key)} in data_store[{i}]", flush=True)
        print("Done printing Hash Table", flush=True)


@app.route('/modify', methods=['POST'])
def handle_modify():
    data = request.get_json()
    response = chord_node.modify(**data)
    return jsonify({"response": response})

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    response = chord_node.query(**data)
    return jsonify({"response": response})

@app.route('/query_star', methods=['POST'])
def handle_query_star():
    data = request.get_json()
    response = chord_node.query_star(**data)
    return jsonify({"response": response})

@app.route('/join', methods=['POST'])
def handle_join():
    data = request.get_json()
    response = chord_node.join_request(**data)
    return jsonify({"response": response})

@app.route('/joinResponse', methods=['POST'])
def handle_join_response():
    data = request.get_json()
    response = chord_node.join_response(**data)
    return jsonify({"response": response})

@app.route('/shiftUpReplicas', methods=['POST'])
def handle_shift_up_replicas():
    data = request.get_json()
    response = chord_node.shift_up_replicas(**data)
    return jsonify({"response": response})

@app.route('/shiftDownReplicas', methods=['POST'])
def handle_shift_down_replicas():
    data = request.get_json()
    response = chord_node.shift_down_replicas(**data)
    return jsonify({"response": response})

@app.route('/depart', methods=['POST'])
def handle_depart():
    response = chord_node.depart()
    return jsonify({"response": response})

@app.route('/departPred', methods=['POST'])
def handle_depart_pred():
    data = request.get_json()
    response = chord_node.depart_pred(**data)
    return jsonify({"response": response})

@app.route('/update_succ_info', methods=['POST'])
def handle_update_succ_info():
    data = request.get_json()
    response = chord_node.update_succ_info(**data)
    return jsonify({"response": response})

@app.route('/modify_resp', methods=['POST'])
def handle_modify_resp():
    data = request.get_json()
    print(data["response"])
    return jsonify({"response": "Ok modify response"})

@app.route('/query_resp', methods=['POST'])
def handle_query_resp():
    data = request.get_json()
    print("Query result:", data["result"])
    return jsonify({"response": "Ok query"})

@app.route('/replicateModify', methods=['POST'])
def handle_replicate_modify():
    data = request.get_json()
    response = chord_node.replicate_modify(**data)
    return jsonify({"response": "Ok replicate modify"})

@app.route('/replicateQuery', methods=['POST'])
def handle_replicate_query():
    data = request.get_json()
    response = chord_node.replicate_query(**data)
    return jsonify({"response": "Ok replicate query"})

@app.route('/overlay', methods=['POST'])
def handle_overlay():
    data = request.get_json()
    response = chord_node.overlay(**data)
    return jsonify({"response": "Ok overlay"})

@app.route('/incReplicationFactor', methods=['POST'])
def handle_inc_replication_factor():
    data = request.get_json()
    response = chord_node.inc_replication_factor(**data)
    return jsonify({"response": "Ok inc replication factor"})

@app.route('/decReplicationFactor', methods=['POST'])
def handle_dec_replication_factor():
    data = request.get_json()
    response = chord_node.dec_replication_factor(**data)
    return jsonify({"response": "Ok dec replication factor"})

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
                response = chord_node.modify(42, ip, port, "insert", key, value)
                print(response, flush=True)
            elif cmd == "delete":
                if len(args) < 2:
                    print("Usage: delete <key>", flush=True)
                    continue
                key = args[1]
                response = chord_node.modify(42, ip, port, "delete", key, None)
                print(response, flush=True)
            elif cmd == "query":
                if len(args) < 2:
                    print("Usage: query <key>", flush=True)
                    continue
                key = args[1]
                if key == "*":
                    response = chord_node.query_star(42, ip, port, None)
                else:
                    response = chord_node.query(42, ip, port, key)
                print(response, flush=True)
            elif cmd == "depart":
                if not chord_node.is_bootstrap:
                    response = chord_node.depart()
                    print(response, flush=True)
                    break
                else:
                    print("Bootstrap node cannot depart", flush=True)
            elif cmd == "overlay":
                chord_node.overlay(ip, port, None)
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
#        except Exception as e:
#            print("Error:", e, flush=True)

def start_flask_app(ip, port):
    app.run(host=ip, port=port, threaded=True)

if __name__ == "__main__":
    #CONSISTENCY_MODEL = "LINEARIZABLE"
    CONSISTENCY_MODEL = "EVENTUAL"
    REPLICATION_FACTOR = 2

    if len(sys.argv) > 1 and sys.argv[1] == 'join':
        if len(sys.argv) != 6:
            print("Usage: python chord.py join <bootstrap_ip> <bootstrap_port> <node_ip> <node_port>", flush=True)
            sys.exit(1)
        bootstrap_ip = sys.argv[2]
        bootstrap_port = int(sys.argv[3])
        node_ip = sys.argv[4]
        node_port = int(sys.argv[5])
        chord_node = ChordNode(node_ip, node_port, replication_factor=REPLICATION_FACTOR, consistency_model=CONSISTENCY_MODEL)
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
        chord_node = ChordNode(bootstrap_ip, bootstrap_port, replication_factor=REPLICATION_FACTOR, consistency_model=CONSISTENCY_MODEL, is_bootstrap=True)
        flask_thread = threading.Thread(target=start_flask_app, args=(bootstrap_ip, bootstrap_port))
        flask_thread.daemon = True
        flask_thread.start()
        chord_cli(chord_node, bootstrap_ip, bootstrap_port)
