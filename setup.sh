#!/bin/bash

kvmd-pstrun -- python3 -m venv /var/lib/kvmd/pst/data/pikvm-ha-sensors/venv
source /var/lib/kvmd/pst/data/pikvm-ha-sensors/venv/bin/activate
kvmd-pstrun -- python3 -m pip install -r requirements.txt
