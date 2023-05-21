from typing import Optional
from datetime import datetime
from w1thermsensor import W1ThermSensor, Sensor
from w1thermsensor import NoSensorFoundError, SensorNotReadyError, ResetValueError
from .measurementerror import MeasurementError

class ds18b20():

  manufacturer = 'MAXIM'
  model = 'DS18B20'

  def __init__(self, addr: Optional[str] = None, config: Optional[dict] = None):
    self._w1therm = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id=addr)
    self._id = addr

  @property
  def temperature(self):
    try:
      return self._w1therm.get_temperature()
    except (NoSensorFoundError, SensorNotReadyError, ResetValueError) as error:
      raise MeasurementError(str(error))

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    return "{serial:012x}".format(serial=int(self._id, 16))
