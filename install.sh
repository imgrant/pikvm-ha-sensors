#!/bin/bash

git archive HEAD | tar -x -C /var/lib/kvmd/pst/data/pikvm-ha-sensors \
  --exclude='*sample*' \
  --exclude='pikvm-ha-sensors.service' \
  --exclude='install.sh' \
  --exclude='*.md' \
  --exclude='.vscode' \
&& uv sync --directory /var/lib/kvmd/pst/data/pikvm-ha-sensors
cp pikvm-ha-sensors.service /etc/systemd/system/ && systemctl daemon-reload
