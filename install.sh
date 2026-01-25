#!/bin/bash

set -e

INSTALL_DIR="/var/lib/kvmd/pst/data/pikvm-ha-sensors"
export UV_WORKING_DIR="$INSTALL_DIR"
export UV_CACHE_DIR="$INSTALL_DIR/.cache/uv"

if [ ! -d "$INSTALL_DIR/.venv" ]; then
  uv venv --system-site-packages
fi

git archive HEAD | tar -x -C $INSTALL_DIR \
  --exclude='*sample*' \
  --exclude='pikvm-ha-sensors.service' \
  --exclude='install.sh' \
  --exclude='*.md' \
  --exclude='.vscode' \

uv sync

cp pikvm-ha-sensors.service /etc/systemd/system/
systemctl daemon-reload
