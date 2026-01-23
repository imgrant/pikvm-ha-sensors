import time, requests
from typing import Optional
from datetime import datetime
from prometheus_client import parser
from .measurementerror import MeasurementError

class hostinfo():

  manufacturer = ''
  model = ''
  url = ''
  metrics_cache_expiry_seconds = 5
  _metrics_cache = {}

  def __init__(self, config, addr: Optional[str] = None):
    self.url = config['prometheus_url']
    self.read_prom_metrics()
    dmi_family = self.metrics['node_dmi_info']
    dmi_labels = dmi_family.samples[0].labels
    self.manufacturer = dmi_labels['system_vendor']
    self.model = dmi_labels['board_name']

  def read_prom_metrics(self):
    try:
      if self.url not in self._metrics_cache:
        self._metrics_cache[self.url] = {
          'timestamp': datetime.fromisoformat("2023-01-01T00:00"),
          'data': {}
        }
      
      cache = self._metrics_cache[self.url]
      
      if (datetime.now() - cache['timestamp']).total_seconds() > self.metrics_cache_expiry_seconds:
        response = requests.get(self.url, timeout=10)
        response.raise_for_status()
        parsed_metrics = {
            family.name: family 
            for family in parser.text_string_to_metric_families(response.text)
        }
        cache['data'] = parsed_metrics
        cache['timestamp'] = datetime.now()
      
      self.metrics = cache['data']

    except (requests.RequestException, StopIteration) as error:
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
    if metric not in self.metrics:
        raise MeasurementError(f"Metric {metric} not found")
        
    family = self.metrics[metric]
    for sample in family.samples:
        if sample.labels.get('chip') == chip and sample.labels.get('sensor') == sensor:
            return sample.value
            
    raise MeasurementError(f"Metric {metric} with chip={chip} sensor={sensor} not found")

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    return "0000000000000000"
