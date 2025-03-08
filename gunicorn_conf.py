import os
from chord import init_app,app

bind = [os.environ["NODE_URL"][7:]]

def post_fork(server, worker):
    init_app(app)

