#!/bin/bash

set -e

INSTALL_DIR="/var/lib/kvmd/pst/data/pikvm-ha-sensors"
export UV_WORKING_DIR="$INSTALL_DIR"
export UV_CACHE_DIR="$INSTALL_DIR/.cache/uv"

git archive HEAD | tar -x -C $INSTALL_DIR \
  --exclude='*sample*' \
  --exclude='pikvm-ha-sensors.service' \
  --exclude='install.sh' \
  --exclude='*.md' \
  --exclude='.vscode' \

PSTRUN="" /bin/bash "$INSTALL_DIR/sync-venv.sh"
uv sync

install_service() {
  cp pikvm-ha-sensors.service /etc/systemd/system/
  systemctl daemon-reload
}

# kvmd-pstrun grants write access to persistent storage only, not to the root
# filesystem holding /etc.
if [ -w /etc/systemd/system ]; then
  install_service
else
  rw
  install_service
  ro
fi
