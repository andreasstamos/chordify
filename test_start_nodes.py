#!/usr/bin/env python3

import requests

response = requests.post("http://127.0.0.1:5000/management/spawnBootstrap", json=
        {"replication_factor": 2, "consistency_model": "LINEARIZABLE"})
print(response.json())

response = requests.post("http://127.0.0.1:5000/management/spawn")
print(response.json())

response = requests.post("http://127.0.0.1:5000/management/list")
print(response.json())

