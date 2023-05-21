import time, psutil
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from .measurementerror import MeasurementError

class sysinfo():

  manufacturer = 'Raspberry Pi'
  model = 'BCMxxxx'
  timezone = 'Europe/London'

  def __init__(self, addr: Optional[str] = None, config: Optional[dict] = None):
    self.model = "{bcm_model} ({rpi_model})".format(bcm_model=self.bcm_model, rpi_model=self.rpi_model)

  @property
  def cpu_temperature(self):
    """The system CPU temperature in °C."""
    try:
      return psutil.sensors_temperatures()['cpu_thermal'][0].current
    except Exception as error:
      raise MeasurementError(str(error))
  
  @property
  def uptime(self):
    """The system uptime in seconds."""
    try:
      uptime = time.time() - psutil.boot_time()
      return int(uptime)
    except Exception as error:
      raise MeasurementError(str(error))
  
  @property
  def boot_time(self):
    """Timestamp (ISO 8601) of when the system was booted."""
    try:
      t = psutil.boot_time()
      return datetime.fromtimestamp(t, ZoneInfo(self.timezone)).isoformat()
    except Exception as error:
      raise MeasurementError(str(error))
  
  @property
  def loadavg_1min(self):
    """The average system load over the last minute, in %."""
    try:
      return psutil.getloadavg()[0] / psutil.cpu_count() * 100
    except Exception as error:
      raise MeasurementError(str(error))

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    cpuserial = "0000000000000000"
    try:
      f = open('/sys/firmware/devicetree/base/serial-number','r')
      cpuserial = f.readline().rstrip('\x00')
      f.close()
    except:
      cpuserial = "ERROR000000000"
    return cpuserial
  
  @property
  def rpi_model(self):
    model = "Unknown model"
    try:
      f = open('/sys/firmware/devicetree/base/model','r')
      model = f.readline().rstrip('\x00')
      f.close()
    except:
      model = "Error (unknown model)"
    return model

  @property
  def bcm_model(self):
    hw = "Unknown"
    try:
      f = open('/proc/cpuinfo','r')
      for line in f:
        if line[0:8]=='Hardware':
          hw = line[10:26].strip()
      f.close()
    except:
      hw = "Error (unknown hardware)"
    return hw
