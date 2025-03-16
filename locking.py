import threading
from flask import Flask, current_app

def create_app():
    app = Flask(__name__)
    with app.app_context():
        current_app.allow_net_changes_cv = threading.Condition()
        current_app.allow_net_changes = True
    return app

app = create_app()

@app.route("/lock-acquire", methods=["POST"])
def acquire_distributed_lock():
    with current_app.allow_net_changes_cv:
        current_app.allow_net_changes_cv.wait_for(lambda: current_app.allow_net_changes)
        current_app.allow_net_changes = False
    return {"status": "ok"}

@app.route("/lock-release", methods=["POST"])
def release_distributed_lock():
    with current_app.allow_net_changes_cv:
        current_app.allow_net_changes = True
        current_app.allow_net_changes_cv.notify()
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5001, threaded=True)

