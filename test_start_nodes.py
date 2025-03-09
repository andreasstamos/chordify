#!/usr/bin/env python3
import dotenv
dotenv.load_dotenv("aws_conf")

import os
import requests

BASE_URL = os.environ["BASE_URL"]

if "HTTP_USERNAME" in os.environ:
    auth = requests.auth.HTTPBasicAuth(os.environ["HTTP_USERNAME"], os.environ["HTTP_PASSWORD"])
else:
    auth = None

response = requests.post(f"{BASE_URL}/management/spawnBootstrap", auth=auth, json=
        {"replication_factor": 2, "consistency_model": "LINEARIZABLE"})
print(response.json())

response = requests.post(f"{BASE_URL}/management/spawn", auth=auth)
print(response.json())

response = requests.post(f"{BASE_URL}/management/list", auth=auth)
print(response.text)
print(response.json())

