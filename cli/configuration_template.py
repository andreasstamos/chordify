# This is a the template for "configuration.py".
# It normally contains secrets (therefore not for a git repository).

# The following can be used as is with the Docker setup.
# (If you wish to run the cli and/or the benchmarks without using the relevant cli/benchmark service from Docker.)

physical_urls = {
        "vm1": "https://localhost/vm1",
        "vm2": "https://localhost/vm2",
        "vm3": "https://localhost/vm3",
        "vm4": "https://localhost/vm4",
        "vm5": "https://localhost/vm5",
        }

http_username = "testuser"
http_password = "123456"

# The following is ONLY for the Docker setup, as it uses a self-signed ssl certificate.
import os
os.environ["CHORD_CLI_SSL_VERIFY"] = "FALSE"

