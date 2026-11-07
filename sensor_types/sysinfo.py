import os, time, psutil
from glob import glob
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import pacman
from .measurementerror import MeasurementError

PACMAN_DB_LOCK = '/var/lib/pacman/db.lck'
CPU_THERMAL_ZONE_TYPE = 'cpu-thermal'


def cpu_thermal_zone_path():
  """Path of the CPU thermal zone's temperature file.

  psutil.sensors_temperatures() builds a reading for every hwmon device, which on
  a PiKVM includes the 1-Wire probes and so triggers a conversion on each of them.
  """
  for zone in sorted(glob('/sys/class/thermal/thermal_zone*')):
    try:
      with open(os.path.join(zone, 'type')) as handle:
        if handle.read().strip() == CPU_THERMAL_ZONE_TYPE:
          return os.path.join(zone, 'temp')
    except OSError:
      continue
  return None


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
    self.cpu_temp_path = cpu_thermal_zone_path()

  @property
  def cpu_temperature(self):
    """The system CPU temperature in °C."""
    if self.cpu_temp_path is None:
      raise MeasurementError("no {} thermal zone found".format(CPU_THERMAL_ZONE_TYPE))
    try:
      with open(self.cpu_temp_path) as handle:
        return int(handle.read().strip()) / 1000
    except (OSError, ValueError) as error:
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

  @staticmethod
  def clear_stale_pacman_lock():
    """Remove a database lock left behind by a pacman run that was killed.

    A restart during the update check kills pacman with its lock held, and
    the lock outlives reboots because it sits on the root filesystem.
    """
    if not os.path.exists(PACMAN_DB_LOCK):
      return

    for process in psutil.process_iter(['name']):
      if process.info['name'] == 'pacman':
        return

    try:
      os.remove(PACMAN_DB_LOCK)
      print("Removed stale pacman database lock {}".format(PACMAN_DB_LOCK))
    except OSError as error:
      print("Unable to remove stale pacman database lock {}: {}".format(PACMAN_DB_LOCK, error))

  @property
  def update_available(self):
    """Whether any OS packages for PiKVM have updates available."""
    try:
      hours_since_last_check = divmod((datetime.now() - self.update_check_timestamp).total_seconds(), 3600)[0]
      if hours_since_last_check > self.update_check_interval_hours:
        os.system('rw')
        try:
          self.clear_stale_pacman_lock()
          pacman.refresh()
          packages = pacman.get_installed()
          upgradable = list(filter(lambda p: p['id'] in self.pikvm_arch_packages and p['upgradable'] is not False, packages))
          self.update_check_value = "ON" if len(upgradable) > 0 else "OFF"
          self.update_check_timestamp = datetime.now()
        finally:
          os.system('ro')
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
