import time
import os
import tempfile
import subprocess
import urllib.parse
import threading
import signal
import psutil

from flask import Flask, request, Response
import requests_unixsocket
import requests

import schemas

app = Flask(__name__)

workers = {}
workers_lock = threading.Lock()
next_id = 1


HAVE_BOOTSTRAP = True if os.environ["HAVE_BOOTSTRAP"]=="TRUE" else False
BASE_URL = os.environ["BASE_URL"]
BOOTSTRAP_URL = os.environ["BOOTSTRAP_URL"]
LOCKING_SRV_URL = os.environ["LOCKING_SRV_URL"]

def monitor_worker(worker_id, proc):
    proc.wait()
    with workers_lock:
        workers.pop(worker_id, None)

def is_bootstrap_alive():
    resp = requests.post(f"{BOOTSTRAP_URL}/healthcheck", json={})
    return resp.status_code == 404

@app.route("/management/spawn", methods=["POST"])
@schemas.validate_json(schemas.SPAWN_SCHEMA)
def spawn_worker():
    global next_id

    requests.post(f"{LOCKING_SRV_URL}/lock-acquire", json={})

    if not is_bootstrap_alive():
        requests.post(f"{LOCKING_SRV_URL}/lock-release", json={})
        return {"error": "Bootstrap Node is not running."}

    worker_id = next_id
    next_id += 1

    socket_path = os.path.join(tempfile.gettempdir(), f"worker_{worker_id}.sock")
    if os.path.exists(socket_path):
        os.remove(socket_path)

    cmd = [
        "gunicorn",
        "-m",
        "777",
        "--bind",
        f"unix:{socket_path}",
        "--workers",
        "1",
        "--worker-class",
        "gevent",
        "-c",
        "gunicorn_conf.py",
        "chord:app",
    ]

    env = {
        "IS_BOOTSTRAP": "FALSE",
        "NODE_URL": f"{BASE_URL}/{worker_id}",
        "BOOTSTRAP_URL": BOOTSTRAP_URL,
        "LOCKING_SRV_URL": LOCKING_SRV_URL
    }
    proc = subprocess.Popen(cmd, env={**os.environ, **env})
    workers[worker_id] = {"process": proc, "socket_path": socket_path}

    monitor_thread = threading.Thread(target=monitor_worker, args=(worker_id, proc), daemon=False)
    monitor_thread.start()

    while not os.path.exists(socket_path):
        time.sleep(0.1)
    time.sleep(0.1)

    requests.post(f"{BASE_URL}/{worker_id}/init", json={})

    requests.post(f"{LOCKING_SRV_URL}/lock-release", json={})

    return {"id": worker_id}


@app.route("/management/spawnBootstrap", methods=["POST"])
@schemas.validate_json(schemas.SPAWN_BOOTSTRAP_SCHEMA)
def spawn_bootstrap():

    data = request.get_json()

    if not HAVE_BOOTSTRAP:
        return {"error": "This node cannot have a bootstrap node."}


    if 0 in workers:
        return {"error": "Bootstrap node is currently running."}

    requests.post(f"{LOCKING_SRV_URL}/lock-acquire", json={})

    socket_path = os.path.join(tempfile.gettempdir(), "worker_bootstrap.sock")
    if os.path.exists(socket_path):
        os.remove(socket_path)

    cmd = [
        "gunicorn",
        "-m",
        "777",
        "--bind",
        f"unix:{socket_path}",
        "--workers",
        "1",
        "--worker-class",
        "gevent",
        "-c",
        "gunicorn_conf.py",
        "chord:app",
    ]

    env = {
        "IS_BOOTSTRAP": "TRUE",
        "NODE_URL": f"{BASE_URL}/0",
        "CONSISTENCY_MODEL": data["consistency_model"],
        "REPLICATION_FACTOR": str(data["replication_factor"]),
        "LOCKING_SRV_URL": LOCKING_SRV_URL
    }
    proc = subprocess.Popen(cmd, env={**os.environ, **env})
    workers[0] = {"process": proc, "socket_path": socket_path}

    monitor_thread = threading.Thread(target=monitor_worker, args=(0, proc), daemon=False)
    monitor_thread.start()

    while not os.path.exists(socket_path):
        time.sleep(0.1)
    time.sleep(0.1)

    requests.post(f"{BASE_URL}/0/init", json={})

    requests.post(f"{LOCKING_SRV_URL}/lock-release", json={})

    return {"id": 0}

@app.route("/management/list", methods=["POST"])
@schemas.validate_json(schemas.LIST_WORKERS_SCHEMA)
def list_workers():
    return list(workers.keys())

@app.route("/management/killall", methods=["POST"])
@schemas.validate_json(schemas.KILLALL_SCHEMA)
def killall_workers():
    global workers, next_id
    for _, worker in workers.items():
        try:
            parent = psutil.Process(worker["process"].pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        if os.path.exists(worker["socket_path"]):
            os.remove(worker["socket_path"])
    workers = {}
    next_id = 1
    return {}

@app.route('/<int:worker_id>/', defaults={'path': ''}, methods=["GET", "POST"])
@app.route('/<int:worker_id>/<path:path>', methods=["GET", "POST"])
def proxy(worker_id, path):
    if worker_id not in workers:
        return {"error": "Worker not found"}

    socket_path = workers[worker_id]["socket_path"]
    socket_path_enc = urllib.parse.quote(socket_path, safe='')

    query = request.query_string.decode('utf-8')
    target_url = f"http+unix://{socket_path_enc}/{path}"

    if query:
        target_url += "?" + query

    session = requests_unixsocket.Session()
    method = request.method
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    data = request.get_data()

    resp = session.request(
        method,
        target_url,
        headers=headers,
        data=data,
        allow_redirects=False
    )

    response = Response(resp.content, status=resp.status_code)
    HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
                  "te", "trailers", "transfer-encoding", "upgrade"}
    for key, value in resp.headers.items():
        if key.lower() not in HOP_BY_HOP:
            response.headers[key] = value
    return response

def cleanup():
    with workers_lock:
        worker_ids = [worker_id for worker_id in workers if worker_id != 0]
        if 0 in workers: worker_ids.append(0)

        for worker_id in worker_ids:
            worker = workers[worker_id]
            proc = worker["process"]
            try:
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=3)
            except Exception:
                print(f"Force killing (SIGKILL) subprocess with id {worker_id}...")
                proc.kill()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)

