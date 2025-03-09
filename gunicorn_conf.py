try:
    import gevent.monkey
    gevent.monkey.patch_all()
except ImportError:
    pass

import os
import signal
from chord import init_app, cleanup_app, app

def post_fork(server, worker):
    init_app(app)

def worker_exit(server, worker):
    cleanup_app(app)
    my_pid = os.getppid()
    os.kill(my_pid, signal.SIGINT)

