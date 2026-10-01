#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
umask 077

apt-get update
apt-get install -y python3 python3-venv curl
mkdir -p /srv/lab5
cd /srv/lab5

fetch_metadata() {
    curl --fail --silent --show-error --retry 5 \
        -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"
}

fetch_metadata service-credentials > service-credentials.json
fetch_metadata config > config.json
fetch_metadata part1-code > part1.py
fetch_metadata vm1-launch-vm2-code > vm1-launch-vm2.py
fetch_metadata vm2-startup-script > vm2-startup-script.sh

python3 -m venv .venv
.venv/bin/pip install google-api-python-client google-auth
.venv/bin/python -u vm1-launch-vm2.py
