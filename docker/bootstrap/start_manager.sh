#!/bin/bash

# Warning! systemd .service file calls me. Edit me with caution at production.

export HAVE_BOOTSTRAP=TRUE
export BOOTSTRAP_URL="http://vm1:5000/0"
export BASE_URL="http://vm1:5000"
export LOCKING_SRV_URL="http://vm1:5000/locking"

nginx -g "daemon off;" &

source venv/bin/activate

# Enable the following only in vm1
gunicorn --workers 1 --worker-class gevent --bind unix:./chordify_locking.sock -m 777 locking:app &

gunicorn --workers 1 --worker-class gevent -c gunicorn_manager_conf.py --bind unix:./chordify.sock -m 777 manager:app

