import time, subprocess, json
from typing import Optional
from datetime import datetime
from .measurementerror import MeasurementError

class hostinfo():

  manufacturer = ''
  model = ''
  prom2json_path = "prom2json"
  url = ''
  metrics = {}
  metrics_timestamp = datetime.fromisoformat("2023-01-01T00:00")
  metrics_cache_expiry_seconds = 10

  def __init__(self, config, addr: Optional[str] = None):
    self.url = config['prometheus_url']
    self.read_prom_metrics()
    self.manufacturer = self.metrics['node_dmi_info']['metrics'][0]['labels']['system_vendor']
    self.model = self.metrics['node_dmi_info']['metrics'][0]['labels']['board_name']

  def read_prom_metrics(self):
    try:
      if (datetime.now() - self.metrics_timestamp).total_seconds() > self.metrics_cache_expiry_seconds:
        result = subprocess.run([self.prom2json_path, self.url], timeout=10, capture_output=True, text=True)
        self.metrics = json.loads(result.stdout)
        self.metrics_timestamp = datetime.now()
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
      raise MeasurementError(str(error))

  @property
  def cpu_fan_speed(self):
    """The speed of the CPU fan, in rpm."""
    return self.get_fan_speed("fan1")
  
  @property
  def pump_speed(self):
    """The speed of the water pump 'fan', in rpm."""
    return self.get_fan_speed("fan2")
  
  @property
  def system_fan1_speed(self):
    """The speed of system fan 1, in rpm."""
    return self.get_fan_speed("fan3")
  
  @property
  def system_fan2_speed(self):
    """The speed of system fan 2, in rpm."""
    return self.get_fan_speed("fan4")
  
  @property
  def system_fan3_speed(self):
    """The speed of system fan 3, in rpm."""
    return self.get_fan_speed("fan5")

  def get_fan_speed(self, sensor_name="fan1"):
    self.read_prom_metrics()
    fan = list(filter(lambda f: f['labels']['sensor'] == sensor_name, self.metrics['node_hwmon_fan_rpm']['metrics']))
    return fan['value']

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    return "0000000000000000"
