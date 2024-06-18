#!/bin/bash

git archive HEAD | tar -x -C /var/lib/kvmd/pst/data/pikvm-ha-sensors \
  --exclude='*sample*' \
  --exclude='pikvm-ha-sensors.service' \
  --exclude='install.sh' \
  --exclude='setup.sh' \
  --exclude='requirements.txt'
cp pikvm-ha-sensors.service /etc/systemd/system/
systemctl daemon-reload
