export IS_BOOTSTRAP=TRUE
export NODE_URL="http://127.0.0.1:4999"
export CONSISTENCY_MODEL="LINEARIZABLE"
export REPLICATION_FACTOR=2
gunicorn --workers 1 --threads 4 -c gunicorn_conf.py chord:app --bind 127.0.0.1:4999

