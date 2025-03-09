#!/bin/bash

# Warning! systemd .service file calls me. Edit me with caution at production.

export HAVE_BOOTSTRAP=TRUE
export BOOTSTRAP_URL="http://127.0.0.1:5000/0"
export BASE_URL="http://127.0.0.1:5000"

source venv/bin/activate
gunicorn --workers 1 --worker-class gevent -c gunicorn_manager_conf.py --bind unix:./chordify.sock -m 777 manager:app

