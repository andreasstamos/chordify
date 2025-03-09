export IS_BOOTSTRAP=FALSE
export NODE_URL="http://127.0.0.1:5021"
export BOOTSTRAP_URL="http://127.0.0.1:4999"
gunicorn --workers 1 --threads 4 -c gunicorn_conf.py chord:app --bind 127.0.0.1:5021

