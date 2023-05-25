import time, psutil
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import pacman
from .measurementerror import MeasurementError

class sysinfo():

  manufacturer = 'Raspberry Pi'
  model = 'BCMxxxx'
  timezone = 'Europe/London'

  update_check_timestamp = datetime.fromisoformat("2023-01-01T00:00")
  update_check_interval_hours = 12
  update_check_value = "OFF"
  pikvm_arch_packages = [
      'kvmd',
      'kvmd-fan',
      'kvmd-oled',
      'kvmd-webterm',
      'kvmd-cloud',
      'kvmd-platform-v2-hdmi-rpi4',
      'janus-gateway-pikvm',
      'firmware-raspberrypi-pikvm',
      'avrdude-pikvm',
      'pikvm-os-raspberrypi',
      'linux-rpi-pikvm',
      'linux-rpi-headers-pikvm',
      'linux-firmware-whence-pikvm',
      'linux-firmware-pikvm',
      'linux-api-headers-pikvm',
      'raspberrypi-bootloader-pikvm',
      'raspberrypi-bootloader-x-pikvm',
      'raspberrypi-firmware-pikvm',
      'ustreamer',
      'tailscale-pikvm'
    ]

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
  def update_available(self):
    """Whether any OS packages for PiKVM have updates available."""
    try:
      hours_since_last_check = divmod((datetime.now() - self.update_check_timestamp).total_seconds(), 3600)[0]
      if hours_since_last_check > self.update_check_interval_hours:
        pacman.refresh()
        packages = pacman.get_installed()
        upgradable = list(filter(lambda p: p['id'] in self.pikvm_arch_packages and p['upgradable'] is True, packages))
        self.update_check_value = "ON" if len(upgradable) > 0 else "OFF"
        self.update_check_timestamp = datetime.now()
      return self.update_check_value
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
