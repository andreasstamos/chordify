import os
from chord import init_app, cleanup_app, app

#bind = [os.environ["NODE_URL"][7:]]

def post_fork(server, worker):
    init_app(app)

def worker_exit(server, worker):
    cleanup_app(app)

