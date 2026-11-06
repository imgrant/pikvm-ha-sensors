# pikvm-ha-sensors

A Python script for collecting sensor information running on my PiKVM, and exporting to Home Assistant.

## Prerequisites

This project requires `uv` for dependency management.

To install `uv` on PiKVM (Arch Linux ARM):
```bash
pacman -Sy uv
```

## Installation

Configuration and installation is handled by `install.sh`. This script will:
1. Copy the source code to the persistent storage area (`/var/lib/kvmd/pst/data/pikvm-ha-sensors`).
2. Create/update the virtual environment and sync dependencies using `uv sync`.
3. Install and reload the systemd service.

### Binding the HTU21D at boot

The kernel's `htu21` driver abandons its probe after a single failed I2C
transaction, which happens on most PiKVM boots:

```
htu21 1-0040: Failed to reset device
htu21 1-0040: probe with driver htu21 failed with error -5
```

The chip is fine; it just has no IIO device, so the temperature and humidity
sensors report as unavailable. `bind-sensor.sh` binds the driver by hand, and
the service runs it before each start. Readings resume on the next update
cycle without a restart.

```bash
kvmd-pstrun -- /bin/bash /var/lib/kvmd/pst/data/pikvm-ha-sensors/bind-sensor.sh
```

> [!NOTE]
> Set `DRIVER` and `I2C_DEVICE` to bind something other than the HTU21D at
> `1-0040`. Pass `--dry-run` to report whether a bind is pending.

### Surviving a Python upgrade

A virtual environment is tied to the Python minor version it was built with. When
PiKVM upgrades `python`, the deployed environment stops matching and every import
fails. `sync-venv.sh` detects this and rebuilds the environment; the service runs
it before each start, and `install.sh` runs it during deployment.

The rebuild needs write access to persistent storage and a network connection,
because some dependencies ship interpreter-specific binary wheels. If either is
unavailable the service keeps retrying until the rebuild succeeds.

> [!NOTE]
> Run the script by hand with `--dry-run` to check whether a rebuild is pending:
> ```bash
> kvmd-pstrun -- /bin/bash /var/lib/kvmd/pst/data/pikvm-ha-sensors/sync-venv.sh --dry-run
> ```


Run the script using the `kvmd-pstrun` wrapper to ensure write access to persistent storage:

```bash
kvmd-pstrun -- ./install.sh
```

You can also use `install.sh` to upgrade an existing deployed program after updating the git repo.

## Configuration

The application uses two YAML configuration files:

- `config.yaml`: Contains application-wide settings such as MQTT broker details, update intervals, and authentication.
- `sensors.yaml`: Defines the specific sensors to monitor, including their type, address, and Home Assistant presentation details.

For examples of the available variables and their usage, please refer to `config.sample.yaml` and `sensors.sample.yaml` provided in the repository.

Note, some sensors come from a Prometheus node exporter endpoint running on the host PiKVM is attached to; collecting these metrics obviously requires network connectivity, the host to be up, and the exporter running.

## Usage

After installation, start/stop the service using systemd:

```
systemctl start pivkm-ha-sensors
```

### Removing the entities from Home Assistant

The discovery topics are retained, so deleting the device in the Home Assistant
UI is not enough — Home Assistant recreates it from the retained messages when it
next subscribes. Clear them first, then restart the service to register
everything again:

```
systemctl stop pikvm-ha-sensors
uv run pikvm-ha-sensors.py --purge
systemctl start pikvm-ha-sensors
```

`--purge` asks the broker for every retained topic under the device's discovery
prefix, rather than working from `sensors.yaml`, so it also clears entities left
behind by sensors that have since been removed from the configuration.

> [!NOTE]
> Purging does not rename anything. Home Assistant keeps an entity registry entry
> keyed on `unique_id` and restores the previous entity ID when the same sensor
> reappears, so entity IDs can only be changed in the Home Assistant UI.

Output is logged to the system journal:

```
$ journalctl -u pikvm-ha-sensors
Jan 23 07:15:35 pikvm python[21147]: Timestamp: 2026-01-23T07:15:35
Jan 23 07:15:35 pikvm python[21147]:  ↪ Sensor chassis_temperature: 22.627°C
Jan 23 07:15:35 pikvm python[21147]:  ↪ Sensor chassis_humidity: 41.83%
Jan 23 07:15:36 pikvm python[21147]:  ↪ Sensor water_temperature: 20.75°C
Jan 23 07:15:36 pikvm python[21147]:  ↪ Sensor air_intake_temperature: 18.406°C
Jan 23 07:15:37 pikvm python[21147]:  ↪ Sensor air_exhaust_temperature: 21.625°C
Jan 23 07:15:37 pikvm python[21147]:  ↪ Sensor atx_power: ON
Jan 23 07:15:38 pikvm python[21147]:  ↪ Sensor cpu_temperature: 53.069°C
Jan 23 07:15:38 pikvm python[21147]:  ↪ Sensor boot_time: 2025-12-30T15:01:51+00:00
Jan 23 07:15:38 pikvm python[21147]:  ↪ Sensor loadavg: 4.8%
Jan 23 07:15:38 pikvm python[21147]:  ↪ Sensor update_available: ON
Jan 23 07:15:38 pikvm python[21147]:  ↪ Sensor host_cpu_temperature: 34.125°C
Jan 23 07:15:39 pikvm python[21147]:  ↪ Sensor host_system_temperature: 34.5°C
Jan 23 07:15:39 pikvm python[21147]:  ↪ Sensor host_vrm_temperature: 33.5°C
Jan 23 07:15:39 pikvm python[21147]:  ↪ Sensor host_pch_temperature: 40.5°C
Jan 23 07:15:40 pikvm python[21147]:  ↪ Sensor cpu_fan_speed: 1057RPM
Jan 23 07:15:40 pikvm python[21147]:  ↪ Sensor pump_speed: 1336RPM
Jan 23 07:15:40 pikvm python[21147]:  ↪ Sensor system_fan_speed_1: 670RPM
Jan 23 07:15:40 pikvm python[21147]:  ↪ Sensor system_fan_speed_2: 651RPM
Jan 23 07:15:41 pikvm python[21147]:  ↪ Sensor system_fan_speed_3: 591RPM
```
