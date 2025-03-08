export IS_BOOTSTRAP=TRUE
export NODE_URL="http://127.0.0.1:5000"
export CONSISTENCY_MODEL="LINEARIZABLE"
export REPLICATION_FACTOR=2
gunicorn --worker-class gevent -c gunicorn_conf.py chord:app

