# pikvm-ha-sensors

A Python script for collecting sensor information running on my PiKVM, and exporting to Home Assistant.

## Setup

Clone the repository, then use the `setup.sh` script to create a Python virtualenv and install the required packages.
Note, run the script using the `kvmd-pstrun` wrapper, which enables and disables write access to the persistent storage area in PiKVM, on-the-fly.

```
kvmd-pstrun -- ./setup.sh
```

## Installation

Use the `install.sh` script to install the script to the persistent storage area, and create a systemd service:

```
kvmd-pstrun -- ./install.sh
```

## Usage

Start/stop the service using systemd:

```
systemctl start pivkm-ha-sensors
```
