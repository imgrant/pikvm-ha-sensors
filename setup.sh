#!/bin/bash

python3 -m venv --system-site-packages /var/lib/kvmd/pst/data/pikvm-ha-sensors/venv
source /var/lib/kvmd/pst/data/pikvm-ha-sensors/venv/bin/activate
python3 -m pip install -r requirements.txt
