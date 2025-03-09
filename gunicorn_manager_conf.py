try:
    import gevent.monkey
    gevent.monkey.patch_all()
except ImportError:
    pass

from manager import cleanup

def worker_exit(server, worker):
    cleanup()

