try:
    import gevent.monkey
    gevent.monkey.patch_all()
except ImportError:
    pass

import os
import signal
from chord import cleanup_app, app

def worker_exit(server, worker):
    cleanup_app(app)
    my_pid = os.getppid()
    os.kill(my_pid, signal.SIGINT)

