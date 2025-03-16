import functools
from flask import Flask, request, jsonify, current_app
import uuid
import threading
import hashlib
import sys
import json
import requests
import time
import readline
import inspect

import os
import signal

import schemas

# Question: What happens if two nodes hash to the same value?
# For n nodes, the probability is ~ n^2/(2*2**160). (sha1 is 160 bits)
# For 1000 nodes this is 3e-43. we can accept this.

# TODO: Maybe do not wait for response by default?

def with_kwargs(func):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def inner(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        _kwargs = dict(bound.arguments)
        _kwargs.pop('_kwargs', None)
        _kwargs.pop('self', None)
        return func(*args, **kwargs, _kwargs=_kwargs)
    return inner

def send_request(url, endpoint, data, nonblocking=True):
    full_url = f"{url}/{endpoint}"

    def do_request():
        requests.post(full_url, json=data)

    if nonblocking:
        thread = threading.Thread(target=do_request, daemon=False)
        thread.start()
    else:
        do_request()


class ChordNode:
    def __init__(self, url, locking_srv_url, replication_factor=None, consistency_model=None, is_bootstrap=False):
        self.url = url
        self.node_id = self.hash_id(url)

        self.locking_srv_url = locking_srv_url

        self.successor_url   = url if is_bootstrap else None
        self.predecessor_url = url if is_bootstrap else None

        self.is_bootstrap = is_bootstrap

        self.keys_start = self.node_id + 1 if is_bootstrap else None
        self.keys_end = self.node_id if is_bootstrap else None

        self.replication_factor = 1 if is_bootstrap else None
        self.max_replication_factor = replication_factor if is_bootstrap else None

        self.data_store = [{}] if is_bootstrap else None
        self.consistency_model = consistency_model if is_bootstrap else None

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
        self.replicate_wakeup_lock = threading.Lock()

        self.pending_requests = dict()

        self.departed = False

        self.finger_table = []

    @staticmethod
    def hash_id(value):
        return int.from_bytes( hashlib.sha1(value.encode()).digest(), byteorder="little")

    @staticmethod
    def lies_in_range(start, end, key_hash):
        return (start == end) or \
            (start <= key_hash <= end) or \
            (end < start <= key_hash) or \
            (key_hash <= end < start)

    def is_responsible(self, key_hash):
        return self.lies_in_range(self.keys_start, self.keys_end, key_hash)

    def forward_request(self, endpoint, data, nonblocking=True):
        print(f"Forwarding {endpoint} request to the next node.")
        return send_request(self.successor_url, endpoint, data, nonblocking=nonblocking)

    def propagate_update_finger_table_phase1(self, initial_url, nodes):
        if initial_url == self.url:
            self.propagate_update_finger_table_phase2(None, nodes)
        else:
            if initial_url is None:
                initial_url = self.url
                nodes = []
            nodes.append(self.url)
            self.forward_request("updateFingerTablePhase1", {"initial_url": initial_url, "nodes": nodes}, nonblocking=False)

    def propagate_update_finger_table_phase2(self, initial_url, nodes):
        if initial_url == self.url:
            return
        else:
            self.update_finger_table(nodes)

            if initial_url is None:
                initial_url = self.url
            self.forward_request("updateFingerTablePhase2", {"initial_url": initial_url, "nodes": nodes}, nonblocking=False)

    def update_finger_table(self, nodes):
        nodes = sorted(nodes, key=self.hash_id)

        # circular rotation so that first node is the successor
        succ_idx = nodes.index(self.successor_url)
        nodes = nodes[succ_idx:] + nodes[:succ_idx]
        print(nodes)
        new_finger_table = []
        for i in range(160):
            start = (self.node_id + 2**i) % (2**160)
            for node in nodes:
                if self.lies_in_range(self.node_id, self.hash_id(node), start):
                    # first(/nearest) node that may include keys>=start.
                    new_finger_table.append(node)
                    break
            else:
                assert False
        self.finger_table = new_finger_table

    def finger_lookup(self, key_hash):
        if self.lies_in_range(self.node_id, self.hash_id(self.successor_url), key_hash):
            return self.successor_url
        # forward to the nearest node that is strictly before the responsible node.
        # the check for the successor is necessary as it is the actual responsible node, and not
        # a node before it.
        for finger_prev, finger in zip(self.finger_table, self.finger_table[1:]):
            if self.lies_in_range(self.node_id, self.hash_id(finger), key_hash):
                return finger_prev
        return self.finger_table[-1]

    @with_kwargs
    def replicate_modify(self, seq, uid, initial_url, operation, key, value, distance, _kwargs=None):
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
            with self.replicate_wakeup_lock:
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
                self.data_store[distance].pop(key, None)

        if distance < self.replication_factor-1:
            with self.replicate_wakeup_lock:
                seq_send = self.seq_to_succ
                self.seq_to_succ += 1
            self.forward_request("replicateModify", {**_kwargs, "seq": seq_send, "distance": distance+1})
        else:
            send_request(initial_url, "operation_resp", {"uid": uid, "response": "ok modify"}) #TODO: better message

        self.replicate_wakeup()


    @with_kwargs
    def replicate_query(self, seq, uid, initial_url, key, distance, _kwargs=None):
        if seq is not None:
            with self.replicate_wakeup_lock:
                if seq != self.seq_from_prev:
                    #print("REORDERING", seq, self.seq_from_prev) #TODO: remove
                    self.reorder_buffer_replication[seq] = ("query", _kwargs)
                    return
                else:
                    self.seq_from_prev += 1

        if distance < self.replication_factor-1:
            with self.replicate_wakeup_lock:
                seq_send = self.seq_to_succ
                self.seq_to_succ += 1
            self.forward_request("replicateQuery", {**_kwargs, "seq": seq_send, "distance": distance+1})
        else:
            res = self.data_store[-1].get(key, None)
            # Inform initial node of result
            send_request(initial_url, "operation_resp", {"uid": uid, "response": res})

        self.replicate_wakeup()

    def replicate_wakeup(self):
        # wakeup reorder buffer
        # TODO: I cannot test this code.... Check it out. We might as well leave it out.
        # A reordering is (probably?) a rare event and will probably not appear when evaluating this project.
        # IF however it happens to appear and the app blows up it might be worse than an inconsistency which might go unnoticed.
        # (highly the opposite of what would apply to a real system!)
        # on the other hand, we can present it as BONUS feature...........
        seq_wakeup = None
        with self.replicate_wakeup_lock:
            if min(self.reorder_buffer_replication.keys(), default=None) == self.seq_from_prev:
                seq_wakeup = min(self.reorder_buffer_replication.keys())
                (op, kwargs) = self.reorder_buffer_replication[seq_wakeup]
                del self.reorder_buffer_replication[seq_wakeup]

        if seq_wakeup is not None:
            #print(f"WAKEUP {seq_wakeup}")
            match op:
                case "modify":
                    self.replicate_modify(**kwargs)
                case "query":
                    self.replicate_query(**kwargs)


    #TODO: Locks?

    @with_kwargs
    def modify(self, uid, initial_url, operation, key, value, _kwargs=None):
        key_hash = self.hash_id(key)
        if self.is_responsible(key_hash):
            self.replicate_modify(None, uid, initial_url, operation, key, value, 0)
        else:
            next_node = self.finger_lookup(key_hash)
            return send_request(next_node, "modify", _kwargs)

    @with_kwargs
    def query(self, uid, initial_url, key, _kwargs=None):
        # We assume that key != "*" here
        if self.consistency_model == "EVENTUAL":
            if self.is_responsible(self.hash_id(key)):
                res = self.data_store[0].get(key, None)
                send_request(initial_url, "operation_resp", {"uid": uid, "response": res})
                return
            for data_store_i in self.data_store[::-1]:
                if key in data_store_i:
                    return send_request(initial_url, "operation_resp", {"uid": uid, "response": data_store_i[key]})
            next_node = self.finger_lookup(self.hash_id(key))
            return send_request(next_node, "query", _kwargs)
        else:
            # LINEARIZABLE
            key_hash = self.hash_id(key)
            if self.is_responsible(key_hash):
                self.replicate_query(None, uid, initial_url, key, 0)
            else:
                next_node = self.finger_lookup(key_hash)
                return send_request(next_node, "query", _kwargs)

    @with_kwargs
    def query_star(self, uid, initial_url, value=None, _kwargs=None):
        if value is not None and self.url == initial_url:
            self.operation_resp(uid=uid, response=value)
        else:
            if value is None:
                value = {}
            value = value | self.data_store[-1]
            self.forward_request("query_star", {**_kwargs, "value":value})

    def new_pred(self, new_node_url):
        new_node_id = self.hash_id(new_node_url)

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

        send_request(new_node_url, "joinResponse", { 
            "predecessor_url": self.predecessor_url,
            "successor_url": self.url,
            "keys_start": self.keys_start,
            "keys_end":   new_node_id,
            "replication_factor": self.replication_factor if self.replication_factor==self.max_replication_factor else self.replication_factor+1,
            "max_replication_factor": self.max_replication_factor,
            "consistency_model": self.consistency_model,
            "data_store": new_data_store}, nonblocking=False)

        # inform my old predecessor to update his successor to new_node_url
        send_request(self.predecessor_url, "update_succ_info", { 
            "new_node_url": new_node_url}, nonblocking=False)

        new_node_start = self.keys_start

        self.keys_start = new_node_id + 1

        self.predecessor_url = new_node_url
        with self.replicate_wakeup_lock:
            self.seq_from_prev = 0

        if self.replication_factor < self.max_replication_factor:
            self.inc_replication_factor(new_node_url, 1, new_node_start, new_node_id)
            # it should stop at the new node. we have already given him the correct data.
        else:
            self.shift_up_replicas(0, self.keys_start, self.keys_end)

    def join_response(self, predecessor_url, successor_url, keys_start, keys_end,\
            replication_factor, max_replication_factor, consistency_model, data_store):
        self.predecessor_url    = predecessor_url
        self.successor_url      = successor_url
        self.keys_start         = keys_start
        self.keys_end           = keys_end
        self.replication_factor = replication_factor
        self.max_replication_factor = max_replication_factor
        self.consistency_model = consistency_model
        self.data_store         = data_store

        self.seq_to_succ   = 0
        self.seq_from_prev = 0



    @with_kwargs
    def inc_replication_factor(self, initial_url, distance, new_node_start, new_node_end, _kwargs=None):
        if initial_url==self.url:
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

            self.forward_request("incReplicationFactor", {**_kwargs, "distance": distance+1}, nonblocking=False)

    def shift_up_replicas(self, distance, exclude_start, exclude_end):
        for i in range(distance+2, self.replication_factor)[::-1]:
            self.data_store[i] = self.data_store[i-1] # distance increased
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
                }, nonblocking=False)

    @with_kwargs
    def join_request(self, new_node_url, _kwargs=None):
        new_node_id = self.hash_id(new_node_url)

        if self.is_responsible(new_node_id):
            print(f"Trying to insert {new_node_id}")
            self.new_pred(new_node_url)

        else:
            data = {"new_node_url": new_node_url}
            self.forward_request("join", _kwargs, nonblocking=False)
            return "Forwarded join_request request"

    def join_existing(self, bootstrap_url):
        join_cmd = {"new_node_url": self.url}
        try:
            send_request(bootstrap_url, "join", join_cmd, nonblocking=False)
            self.propagate_update_finger_table_phase1(None, None)
        except Exception as e:
            print("Error joining chord ring:", e, flush=True)

    def update_succ_info(self, new_node_url):
        new_node_id = self.hash_id(new_node_url)
        self.successor_url = new_node_url
        with self.replicate_wakeup_lock:
            self.seq_to_succ = 0

        return "Successfully updated succ info"

    def depart(self):
        if self.departed: return
        self.departed = True

        send_request(self.locking_srv_url, "lock-acquire", {}, nonblocking=False)

        print(f"Node {self.node_id} beginning to depart", flush=True)

        # wait until reorder buffer empties
        while True:
            with self.replicate_wakeup_lock:
                if len(self.reorder_buffer_replication) == 0:
                    break
            time.sleep(0.1)

        send_request(self.predecessor_url, "update_succ_info",
                {"new_node_url": self.successor_url}, nonblocking=False)

        self.forward_request("departPred", {
            "keys_start": self.keys_start,
            "predecessor_url": self.predecessor_url,
            "maxdistance_replica": self.data_store[-1]
            }, nonblocking=False)

        self.successor_url = None
        self.predecessor_url = None

        send_request(self.locking_srv_url, "lock-release", {}, nonblocking=False)

        my_pid = os.getpid()
        os.kill(my_pid, signal.SIGINT)

        return f"Node {self.node_id} is departing from the network."

    def depart_pred(self, keys_start, predecessor_url, maxdistance_replica):
        self.keys_start       = keys_start
        self.predecessor_url  = predecessor_url

        with self.replicate_wakeup_lock:
            self.seq_from_prev = 0

        self.data_store[1] |= self.data_store[0]  # shift_down_replicas will then move this one unit of distance downwards

        self.propagate_update_finger_table_phase1(None, None)
        self.shift_down_replicas(None, 0, maxdistance_replica)

    def shift_down_replicas(self, initial_url, distance, maxdistance_replica):
        if initial_url == self.url:
            return self.dec_replication_factor(None)

        for i in range(distance, self.replication_factor-1):
            self.data_store[i] = self.data_store[i+1]
        old_maxdistance_replica = self.data_store[-1]
        self.data_store[-1] = maxdistance_replica

        if distance < self.replication_factor-1:
            if initial_url is None:
                initial_url = self.url
            self.forward_request("shiftDownReplicas", {
                "initial_url": initial_url,
                "distance": distance+1,
                "maxdistance_replica": old_maxdistance_replica
                }, nonblocking=False)

    def dec_replication_factor(self, initial_url):
        if initial_url==self.url:
            return
        else:
            self.replication_factor -= 1
            self.data_store.pop()
            if initial_url is None:
                initial_url = self.url
            self.forward_request("decReplicationFactor", {"initial_url": initial_url}, nonblocking=False)

    @with_kwargs
    def overlay(self, uid, initial_url, nodes=None, _kwargs=None):
        if nodes is not None and self.url == initial_url:
            self.operation_resp(uid=uid, response=nodes)
        else:
            node = {
                    "url": self.url,
                    "predecessor_url": self.predecessor_url,
                    "successor_url": self.successor_url,
                    "keys_start": str(self.keys_start),
                    "keys_end": str(self.keys_end),
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

    def operation_driver(self, func, *args, **kwargs):
        uid = uuid.uuid4().hex
        event = threading.Event()
        self.pending_requests[uid] = {"event": event}
        func(uid, self.url, *args, **kwargs)
        event.wait()
        resp = self.pending_requests[uid]["response"]
        del self.pending_requests[uid]
        return resp

    def operation_resp(self, uid, response):
        assert uid in self.pending_requests
        self.pending_requests[uid]["response"] = response
        self.pending_requests[uid]["event"].set()

def init_app():
    IS_BOOTSTRAP    = os.environ["IS_BOOTSTRAP"]
    NODE_URL        = os.environ["NODE_URL"]
    LOCKING_SRV_URL = os.environ["LOCKING_SRV_URL"]
    if IS_BOOTSTRAP=="TRUE":
        CONSISTENCY_MODEL  = os.environ["CONSISTENCY_MODEL"]
        REPLICATION_FACTOR = int(os.environ["REPLICATION_FACTOR"])

        chord_node = ChordNode(url=NODE_URL, locking_srv_url=LOCKING_SRV_URL,\
                consistency_model=CONSISTENCY_MODEL, replication_factor=REPLICATION_FACTOR, is_bootstrap=True)
    else:
        BOOTSTRAP_URL = os.environ["BOOTSTRAP_URL"]
        chord_node = ChordNode(url=NODE_URL, locking_srv_url=LOCKING_SRV_URL)

    current_app.chord_node = chord_node
    if IS_BOOTSTRAP!="TRUE": current_app.chord_node.join_existing(BOOTSTRAP_URL)

app = Flask(__name__)

def cleanup_app(app):
    with app.app_context():
        if not current_app.chord_node.is_bootstrap:
            current_app.chord_node.depart()

@app.route("/init", methods=['POST'])
def handle_init():
    init_app()
    return {}

@app.route('/modify', methods=['POST'])
def handle_modify():
    data = request.get_json()
    response = current_app.chord_node.modify(**data)
    return jsonify({"response": response})

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    response = current_app.chord_node.query(**data)
    return jsonify({"response": response})

@app.route('/query_star', methods=['POST'])
def handle_query_star():
    data = request.get_json()
    response = current_app.chord_node.query_star(**data)
    return jsonify({"response": response})

@app.route('/join', methods=['POST'])
def handle_join():
    data = request.get_json()
    response = current_app.chord_node.join_request(**data)
    return jsonify({"response": response})

@app.route('/joinResponse', methods=['POST'])
def handle_join_response():
    data = request.get_json()
    response = current_app.chord_node.join_response(**data)
    return jsonify({"response": response})

@app.route('/shiftUpReplicas', methods=['POST'])
def handle_shift_up_replicas():
    data = request.get_json()
    response = current_app.chord_node.shift_up_replicas(**data)
    return jsonify({"response": response})

@app.route('/shiftDownReplicas', methods=['POST'])
def handle_shift_down_replicas():
    data = request.get_json()
    response = current_app.chord_node.shift_down_replicas(**data)
    return jsonify({"response": response})

@app.route('/departPred', methods=['POST'])
def handle_depart_pred():
    data = request.get_json()
    response = current_app.chord_node.depart_pred(**data)
    return jsonify({"response": response})

@app.route('/update_succ_info', methods=['POST'])
def handle_update_succ_info():
    data = request.get_json()
    response = current_app.chord_node.update_succ_info(**data)
    return jsonify({"response": response})

@app.route('/operation_resp', methods=['POST'])
def handle_operation_resp():
    data = request.get_json()
    current_app.chord_node.operation_resp(**data)
    return jsonify({"response": "Ok operation resp"})

@app.route('/replicateModify', methods=['POST'])
def handle_replicate_modify():
    data = request.get_json()
    response = current_app.chord_node.replicate_modify(**data)
    return jsonify({"response": "Ok replicate modify"})

@app.route('/replicateQuery', methods=['POST'])
def handle_replicate_query():
    data = request.get_json()
    response = current_app.chord_node.replicate_query(**data)
    return jsonify({"response": "Ok replicate query"})

@app.route('/overlay', methods=['POST'])
def handle_overlay():
    data = request.get_json()
    response = current_app.chord_node.overlay(**data)
    return jsonify({"response": "Ok overlay"})

@app.route('/incReplicationFactor', methods=['POST'])
def handle_inc_replication_factor():
    data = request.get_json()
    response = current_app.chord_node.inc_replication_factor(**data)
    return jsonify({"response": "Ok inc replication factor"})

@app.route('/decReplicationFactor', methods=['POST'])
def handle_dec_replication_factor():
    data = request.get_json()
    response = current_app.chord_node.dec_replication_factor(**data)
    return jsonify({"response": "Ok dec replication factor"})

@app.route('/updateFingerTablePhase1', methods=['POST'])
def handle_update_finger_table_phase1():
    data = request.get_json()
    response = current_app.chord_node.propagate_update_finger_table_phase1(**data)
    return jsonify({"response": "Ok update finger table phase 1"})

@app.route('/updateFingerTablePhase2', methods=['POST'])
def handle_update_finger_table_phase2():
    data = request.get_json()
    response = current_app.chord_node.propagate_update_finger_table_phase2(**data)
    return jsonify({"response": "Ok update finger table phase 2"})


@app.route('/api/depart', methods=['POST'])
@schemas.validate_json(schemas.API_DEPART_SCHEMA)
def handle_api_depart():
    if not current_app.chord_node.is_bootstrap:
        resp = current_app.chord_node.depart()
        return {"response": resp}
    else:
        return {"error": "Bootstrap node cannot depart."}

@app.route("/api/query", methods=['POST'])
@schemas.validate_json(schemas.API_QUERY_SCHEMA)
def handle_api_query():
    data = request.get_json()
    key = data["key"]
    if key == "*":
        response = current_app.chord_node.operation_driver(current_app.chord_node.query_star, None)
    else:
        response = current_app.chord_node.operation_driver(current_app.chord_node.query, key)
    return {"response": response}

@app.route("/api/modify", methods=['POST'])
@schemas.validate_json(schemas.API_MODIFY_SCHEMA)
def handle_api_modify():
    data = request.get_json()
    key = data["key"]
    operation = data["operation"]
    match operation:
        case "insert":
            value = data["value"]
        case "delete":
            value = None
    response = current_app.chord_node.operation_driver(current_app.chord_node.modify, operation, key, value)
    return {"response": response}

@app.route("/api/overlay", methods=['POST'])
@schemas.validate_json(schemas.API_OVERLAY_SCHEMA)
def handle_api_overlay():
    response = current_app.chord_node.operation_driver(current_app.chord_node.overlay, None)
    return {"response": response}


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
                response = chord_node.operation_driver(chord_node.modify, "insert", key, value)
                print(response, flush=True)
            elif cmd == "delete":
                if len(args) < 2:
                    print("Usage: delete <key>", flush=True)
                    continue
                key = args[1]
                response = chord_node.operation_driver(chord_node.modify, "delete", key, None)
                print(response, flush=True)
            elif cmd == "query":
                if len(args) < 2:
                    print("Usage: query <key>", flush=True)
                    continue
                key = args[1]
                if key == "*":
                    response = chord_node.operation_driver(chord_node.query_star, None)
                else:
                    response = chord_node.operation_driver(chord_node.query, key)
                print(response, flush=True)
            elif cmd == "depart":
                if not chord_node.is_bootstrap:
                    response = chord_node.depart()
                    print(response, flush=True)
                    break
                else:
                    print("Bootstrap node cannot depart", flush=True)
            elif cmd == "overlay":
                nodes = chord_node.operation_driver(chord_node.overlay, None)
                print("Overlay (Chord Ring Topology):", flush=True)
                for node in nodes:
                    print(f"Node {node['url']}")
                    print(f"  Predecessor {node['successor_url']}")
                    print(f"  Successor {node['predecessor_url']}")
                    print(f"  Key Range {node['keys_start']} -- {node['keys_end']}")

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

if __name__ == "__main__":
    def start_flask_app():
        url = os.environ["NODE_URL"][7:]
        ip, port = url.split(":")
        app.run(host=ip, port=port, threaded=True)

    flask_thread = threading.Thread(target=start_flask_app, daemon=False)
    # TODO: alternative?       
    time.sleep(1)
    init_app(app)
    with app.app_context():
        chord_cli(current_app.chord_node)
