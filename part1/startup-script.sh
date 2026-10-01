#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y python3 python3-pip python3-venv git

mkdir -p /opt
if [ ! -d /opt/flask-tutorial ]; then
    git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial /opt/flask-tutorial
fi

cd /opt/flask-tutorial
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install -e .

export FLASK_APP=flaskr
if [ ! -f instance/flaskr.sqlite ]; then
    .venv/bin/flask init-db
fi

cat > /etc/systemd/system/flaskr.service <<'SERVICE'
[Unit]
Description=Lab 5 Flask application
After=network.target

[Service]
WorkingDirectory=/opt/flask-tutorial
Environment=FLASK_APP=flaskr
ExecStart=/opt/flask-tutorial/.venv/bin/flask run --host=0.0.0.0 --port=5000
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now flaskr
