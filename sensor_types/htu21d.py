from pathlib import Path
from typing import Optional
from .measurementerror import MeasurementError

IIO_DEVICES_PATH = Path("/sys/bus/iio/devices")
IIO_DEVICE_NAME = "htu21"
MILLI_UNITS_PER_UNIT = 1000


class htu21d():

  manufacturer = 'Measurement Specialities'
  model = 'HTU21D'

  def __init__(self, addr: Optional[int] = None, config: Optional[dict] = None):
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

  @staticmethod
  def _find_device():
    for candidate in sorted(IIO_DEVICES_PATH.glob("iio:device*")):
      try:
        if (candidate / "name").read_text().strip() == IIO_DEVICE_NAME:
          return candidate
      except OSError:
        continue
    raise MeasurementError(
      "No {name} device found under {path}".format(name=IIO_DEVICE_NAME, path=IIO_DEVICES_PATH))
