import time, requests
from typing import Optional
from datetime import datetime
from prometheus_client import parser
from .measurementerror import MeasurementError

CPU_CHIP = "pci0000:00_0000:00:18_3"
SUPERIO_CHIP = "platform_nct6683_2592"


class hostinfo():

  url = ''
  metrics_cache_expiry_seconds = 5
  _metrics_cache = {}

  def __init__(self, config, addr: Optional[str] = None):
    self.url = config['prometheus_url']
    self.metrics = {}

  @property
  def manufacturer(self):
    return self._dmi_label('system_vendor')

  @property
  def model(self):
    return self._dmi_label('board_name')

  def _dmi_label(self, label):
    try:
      self.read_prom_metrics()
      return self.metrics['node_dmi_info'].samples[0].labels[label]
    except (MeasurementError, KeyError, IndexError):
      return ''

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
    return self.get_temp(sensor="temp1", chip=CPU_CHIP)

  @property
  def host_system_temperature(self):
    """The host 'system' temperature, in °C."""
    return self.get_temp(sensor="temp2", chip=SUPERIO_CHIP)

  @property
  def host_vrm_temperature(self):
    """The host VRM temperature, in °C."""
    return self.get_temp(sensor="temp3", chip=SUPERIO_CHIP)

  @property
  def host_pch_temperature(self):
    """The host PCH temperature, in °C."""
    return self.get_temp(sensor="temp4", chip=SUPERIO_CHIP)

  @property
  def host_socket_temperature(self):
    """The host CPU socket temperature, in °C."""
    return self.get_temp(sensor="temp5", chip=SUPERIO_CHIP)

  @property
  def host_pcie_temperature(self):
    """The host PCIe x1 slot temperature, in °C."""
    return self.get_temp(sensor="temp6", chip=SUPERIO_CHIP)

  def get_fan_speed(self, fan = "fan1", chip: Optional[str] = SUPERIO_CHIP):
    return self._get_metric_value(fan, chip, 'node_hwmon_fan_rpm')
  
  def get_temp(self, sensor = "temp1", chip: Optional[str] = CPU_CHIP):
    return self._get_metric_value(sensor, chip, 'node_hwmon_temp_celsius')

  def get_voltage(self, sensor = "in0", chip: Optional[str] = SUPERIO_CHIP, scale = 1):
    """Read a voltage rail, applying the board's divider ratio.

    node_exporter reports the raw sysfs reading, so the ratios that
    /etc/sensors.d applies for the `sensors` command are not in the metric.
    """
    return self._get_metric_value(sensor, chip, 'node_hwmon_in_volts') * scale

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
  def host_12v_voltage(self):
    """The host +12V rail, in V."""
    return self.get_voltage("in0", scale=12)

  @property
  def host_5v_voltage(self):
    """The host +5V rail, in V."""
    return self.get_voltage("in1", scale=5)

  @property
  def host_3v3_voltage(self):
    """The host +3.3V rail, in V."""
    return self.get_voltage("in8")

  @property
  def host_soc_voltage(self):
    """The host CPU northbridge/SoC voltage, in V."""
    return self.get_voltage("in2")

  @property
  def host_dram_voltage(self):
    """The host DRAM voltage, in V."""
    return self.get_voltage("in3", scale=2)

  @property
  def host_vcore_voltage(self):
    """The host CPU core voltage, in V."""
    return self.get_voltage("in4")

  @property
  def host_chipset_voltage(self):
    """The host chipset voltage, in V."""
    return self.get_voltage("in5")

  @property
  def host_vddp_voltage(self):
    """The host CPU VDDP voltage, in V."""
    return self.get_voltage("in7")

  @property
  def host_cpu_1v8_voltage(self):
    """The host CPU 1.8V rail, in V."""
    return self.get_voltage("in9")

  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    return "0000000000000000"
