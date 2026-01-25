#!/bin/bash

set -e

INSTALL_DIR="/var/lib/kvmd/pst/data/pikvm-ha-sensors"

if [ ! -d "$INSTALL_DIR/.venv" ]; then
  uv venv --system-site-packages --directory $INSTALL_DIR
fi

git archive HEAD | tar -x -C $INSTALL_DIR \
  --exclude='*sample*' \
  --exclude='pikvm-ha-sensors.service' \
  --exclude='install.sh' \
  --exclude='*.md' \
  --exclude='.vscode' \

uv sync --no-dev --directory $INSTALL_DIR

cp pikvm-ha-sensors.service /etc/systemd/system/
systemctl daemon-reload
