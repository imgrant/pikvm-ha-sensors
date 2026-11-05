from pathlib import Path
from typing import Optional
from .measurementerror import MeasurementError

IIO_DEVICES_PATH = Path("/sys/bus/iio/devices")
IIO_DEVICE_NAME = "htu21"
I2C_ADDRESS = 0x40
MILLI_UNITS_PER_UNIT = 1000


class htu21d():

  manufacturer = 'Measurement Specialities'
  model = 'HTU21D'

  def __init__(self, addr: Optional[int] = I2C_ADDRESS, config: Optional[dict] = None):
    self._address = I2C_ADDRESS if addr is None else int(addr)
    self._device = None

  @property
  def temperature(self):
    return self._read_measurement('in_temp_input')

  @property
  def relative_humidity(self):
    return self._read_measurement('in_humidityrelative_input')

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    return "Unknown"

  def _read_measurement(self, attribute):
    path = self._device_path() / attribute
    try:
      return int(path.read_text().strip()) / MILLI_UNITS_PER_UNIT
    except (OSError, ValueError) as error:
      raise MeasurementError("Unable to read {path}: {error}".format(path=path, error=error))

  def _device_path(self):
    if self._device is None:
      self._device = self._find_device()
    return self._device

  def _find_device(self):
    """Locate the IIO device for the htu21 bound at this I2C address."""
    suffix = "-{address:04x}".format(address=self._address)
    for candidate in sorted(IIO_DEVICES_PATH.glob("iio:device*")):
      try:
        if (candidate / "name").read_text().strip() != IIO_DEVICE_NAME:
          continue
        if candidate.resolve().parent.name.endswith(suffix):
          return candidate
      except OSError:
        continue
    raise MeasurementError(
      "No {name} device at I2C address 0x{address:02x} under {path}".format(
        name=IIO_DEVICE_NAME, address=self._address, path=IIO_DEVICES_PATH))
