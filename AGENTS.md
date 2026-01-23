# AGENTS.md

This file provides guidance to AI coding assistants and agents, when working with code in this repository.

## Project Overview

PiKVM Home Assistant Sensors is a Python daemon that runs on PiKVM (Arch Linux ARM on Raspberry Pi) to collect sensor data and export it to Home Assistant via MQTT. The project reads from various hardware sensors (temperature probes, humidity sensors) and system metrics, then publishes them using MQTT autodiscovery. Some sensor information is also read from a Prometheus node exporter endpoint, which should be running on the parent host to which the PiKVM device is attached.

## Development Commands

### Deployment to PiKVM

The primary installation method uses `install.sh`, which handles dependency setup automatically:

```bash
# Deploy to PiKVM (must be run with kvmd-pstrun wrapper)
# This script copies files, runs uv sync, and installs the systemd service
kvmd-pstrun -- ./install.sh

# Check service status
systemctl status pikvm-ha-sensors

# View logs
journalctl -u pikvm-ha-sensors -f
```

### Manual Dependency Management

For development or troubleshooting, you can manually manage dependencies with uv.

**Activating the Virtual Environment:**
If you want to run commands inside the environment context (or for IDE configuration), you can activate the venv:

```bash
# Create the virtual environment
uv venv

# Activate on macOS/Linux
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate
```

**Running Commands:**
Alternatively, `uv run` will automatically use the project's environment without manual activation:

```bash
# Install/sync dependencies (install.sh does this automatically)
uv sync

# Run the application directly
uv run pikvm-ha-sensors.py [config.yaml] [sensors.yaml]
```

## Architecture

### Core Application Flow

1. **Main Script** (`pikvm-ha-sensors.py`): Entry point that loads YAML configuration and sensor definitions, instantiates `PiKVMHASensors` class, and starts the monitoring loop.

2. **Configuration System**:
   - `config.yaml`: MQTT broker settings, update intervals, authentication credentials
   - `sensors.yaml`: Defines each sensor with properties like device type, address, precision, Home Assistant metadata

3. **Sensor Plugin System**: Each sensor type is a Python module in `sensor_types/` that:
   - Inherits/implements a common interface with properties for sensor readings
   - Raises `MeasurementError` on failure (handled gracefully by main loop)
   - Provides `manufacturer`, `model`, and `serial_number` attributes
   - Main application dynamically imports modules based on `device_type` field in `sensors.yaml`

4. **MQTT Integration**:
   - Uses Home Assistant MQTT autodiscovery protocol
   - Publishes three topics per sensor:
     - `sensors/{id}/config`: Discovery payload (retained)
     - `sensors/{id}/state`: JSON with value and timestamp
     - `sensors/{id}/status`: online/offline availability
     - `sensors/{id}/attributes`: Device metadata (retained)
   - Automatic reconnection with exponential backoff

### Sensor Types

- **`htu21d`**: I2C humidity/temperature sensor (inherits from Adafruit library)
- **`ds18b20`**: 1-Wire temperature sensor (uses w1thermsensor library)
- **`kvmd`**: Queries PiKVM's local API for ATX power state
- **`sysinfo`**: System metrics (CPU temp, load average, boot time, package updates) using psutil and python-pacman
- **`hostinfo`**: Scrapes Prometheus node_exporter metrics from the managed host via HTTP. This is designed around a specific TrueNAS SCALE system (Linux NAS OS), where the Prometheus exporter is expected to expose metrics from motherboard sensors and such.

### Key Design Patterns

**Metrics Caching** (`hostinfo.py:23-44`): Implements a URL-keyed cache with configurable expiry to avoid redundant Prometheus endpoint fetches. The cache is a class-level dictionary shared across instances.

**Sensor Initialization** (`pikvm-ha-sensors.py:224-227`): Uses dynamic module import with `importlib.import_module()` and `getattr()` to instantiate sensor classes based on string configuration.

**Update Loop** (`pikvm-ha-sensors.py:229-253`): Iterates through sensors, calls property accessors via `getattr()`, handles `MeasurementError` exceptions to set sensor status to offline, and publishes values as JSON.

**Device Discovery** (`pikvm-ha-sensors.py:263-291`): Constructs Home Assistant MQTT discovery payloads with device metadata (model, manufacturer, connections) and entity configuration (device class, icons, units).

## Configuration

### config.yaml

Application-wide settings (see `config.sample.yaml` for reference):

- **`update_period`** (int): Seconds between sensor reading cycles (default: 30)
- **`valid_time`** (int): Seconds before Home Assistant marks sensor unavailable if no updates (default: 600)
- **`verbose`** (bool): Enable detailed logging output (default: false)
- **`mqtt_broker`** (string): MQTT broker hostname or IP address (required)
- **`mqtt_port`** (int): MQTT broker port (default: 1883)
- **`mqtt_transport`** (string): Transport protocol - `"tcp"` or `"websockets"` (default: "tcp")
- **`mqtt_use_tls`** (bool): Enable TLS/SSL for MQTT connection (default: false)
- **`mqtt_username`** (string): MQTT authentication username (optional, null for anonymous)
- **`mqtt_password`** (string): MQTT authentication password (optional, null for anonymous)
- **`mqtt_ha_prefix`** (string): Home Assistant MQTT discovery prefix (default: "homeassistant")
- **`pikvm_username`** (string): Username for PiKVM API authentication (default: "admin")
- **`pikvm_password`** (string): Password for PiKVM API authentication (required for `kvmd` sensor type)
- **`prometheus_url`** (string): URL to Prometheus node_exporter metrics endpoint (required for `hostinfo` sensor type)

The application reads `config.yaml` by default, or accepts a path as the first command-line argument.

### sensors.yaml

Array of sensor definitions (see `sensors.sample.yaml` for annotated reference). Each sensor has:

**Required Fields:**
- **`name`** (string): Unique identifier for the sensor (e.g., "chassis_temperature"). Used to generate entity IDs.
- **`device_type`** (string): Module name in `sensor_types/` directory (e.g., "htu21d", "ds18b20", "sysinfo")
- **`device_property`** (string): Property name to read from the sensor class instance (e.g., "temperature", "relative_humidity")
- **`ha_component_type`** (string): Home Assistant component type - `"sensor"` for numeric values, `"binary_sensor"` for on/off states
- **`ha_device_class`** (string): Home Assistant device class (e.g., "temperature", "humidity", "power", "timestamp")
- **`ha_title`** (string): Friendly name displayed in Home Assistant UI

**Optional Fields:**
- **`device_address`** (string/int/null): Hardware address - I2C address (e.g., 0x40), 1-Wire ID (e.g., "0621b1925673"), or null if not applicable
- **`device_offset`** (float/null): Calibration offset added to raw sensor value (e.g., 0.281 for temperature correction)
- **`units`** (string/null): Unit of measurement (e.g., "°C", "%", "RPM")
- **`output_precision`** (int/null): Decimal places to round published value. Use null to avoid rounding (e.g., for integers like RPM)
- **`display_precision`** (int/null): Suggested decimal places for Home Assistant frontend display
- **`ha_entity_category`** (string/null): Entity category - null for primary sensors, `"diagnostic"` for system info, `"config"` for settings
- **`ha_icon`** (string/null): Material Design icon (e.g., "mdi:thermometer-lines", "mdi:fan"). Null uses device class default.

The application reads `sensors.yaml` by default, or accepts a path as the second command-line argument.

### Adding a New Sensor Type

1. Create a module in `sensor_types/` (e.g., `newsensor.py`)
2. Implement class with:
   - `manufacturer` and `model` class attributes
   - `__init__(self, addr: Optional[str], config: Optional[dict])`
   - Properties for each measurement (raise `MeasurementError` on failure)
   - `serial_number` property
3. Add sensor definition to `sensors.yaml` with `device_type: "newsensor"`

## Platform-Specific Notes

- This project is designed to run on PiKVM (Arch Linux ARM on Raspberry Pi), most sensor types require specific hardware and cannot be tested on development machines(must be mocked, or untested).
- The 'hostinfo' sensor can be pointed at any Prometheus endpoint, but is intended to be the host Linux system to which the PiKVM is attached.
- Persistent storage is at `/var/lib/kvmd/pst/data/pikvm-ha-sensors`
- The PiKVM filesystem is read-only, use `kvmd-pstrun --` wrapper to run commands in a write-access-enabled window. Alternatively, manual `rw`/`ro` commands can be used to make the filesystem read-write or read-only.
- `install.sh` uses `git archive` to deploy (excludes samples and itself, including the .git dir) the code from a checked out git repo to the persistent location (both must be on the PiKVM).
- `pyproject.toml` enables `system-site-packages = true` to access system-installed hardware libraries (the `kvmd` Python module is installed via PiKVM OS packages, not PyPI).
- Some dependencies (RPi.GPIO, python-pacman) are Linux-only via platform markers.
- Several functions like `get_rpi_serial()`, `get_rpi_model()`, `get_rpi_hw()` read hardware information from `/sys/firmware/devicetree/base/` and `/proc/cpuinfo`.
- `/etc/kvmd/meta.yaml` is parsed for PiKVM configuration information such as hostname.
