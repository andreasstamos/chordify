export HAVE_BOOTSTRAP=TRUE
export BOOTSTRAP_URL="http://127.0.0.1:5000/0"
export BASE_URL="http://127.0.0.1:5000"
gunicorn --workers 1 --worker-class gevent -c gunicorn_manager_conf.py --bind 127.0.0.1:5000 manager:app

