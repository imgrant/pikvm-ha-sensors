import time, subprocess, json
from subprocess import CalledProcessError, TimeoutExpired
from json import JSONDecodeError
from typing import Optional
from datetime import datetime
from .measurementerror import MeasurementError

class hostinfo():

  manufacturer = ''
  model = ''
  prom2json_path = "/root/go/bin/prom2json"
  url = ''
  metrics = {}
  metrics_timestamp = datetime.fromisoformat("2023-01-01T00:00")
  metrics_cache_expiry_seconds = 10

  def __init__(self, config, addr: Optional[str] = None):
    self.url = config['prometheus_url']
    self.read_prom_metrics()
    dmi = list(filter(lambda m: m['name'] == 'node_dmi_info', self.metrics))[0]['metrics'][0]['labels']
    self.manufacturer = dmi['system_vendor']
    self.model = dmi['board_name']

  def read_prom_metrics(self):
    try:
      if (datetime.now() - self.metrics_timestamp).total_seconds() > self.metrics_cache_expiry_seconds:
        result = subprocess.run([self.prom2json_path, self.url], timeout=10, capture_output=True, text=True, check=True)
        self.metrics = json.loads(result.stdout)
        self.metrics_timestamp = datetime.now()
    except (FileNotFoundError, TimeoutExpired, CalledProcessError) as error:
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

  @property
  def host_cpu_temperature(self):
    """The host CPU (AMD K10) temperature, in °C."""
    return self.get_temp(sensor="temp1", chip="pci0000:00_0000:00:18_3")

  @property
  def host_system_temperature(self):
    """The host 'system' temperature, in °C."""
    return self.get_temp(sensor="temp2", chip="platform_nct6683_2592")

  @property
  def host_vrm_temperature(self):
    """The host VRM temperature, in °C."""
    return self.get_temp(sensor="temp3", chip="platform_nct6683_2592")

  @property
  def host_pch_temperature(self):
    """The host PCH temperature, in °C."""
    return self.get_temp(sensor="temp4", chip="platform_nct6683_2592")

  def get_fan_speed(self, fan = "fan1", chip: Optional[str] = "platform_nct6683_2592"):
    return self._get_metric_value(fan, chip, 'node_hwmon_fan_rpm')
  
  def get_temp(self, sensor = "temp1", chip: Optional[str] = "pci0000:00_0000:00:18_3"):
    return self._get_metric_value(sensor, chip, 'node_hwmon_temp_celsius')

  def _get_metric_value(self, sensor, chip, metric):
    self.read_prom_metrics()
    node_metrics = list(filter(lambda n: n['name'] == metric, self.metrics))[0]['metrics']
    sensor_metric = list(filter(lambda m: m['labels']['chip'] == chip and m['labels']['sensor'] == sensor, node_metrics))[0]
    return sensor_metric['value']

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    return "0000000000000000"
