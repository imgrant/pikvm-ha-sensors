import requests
from urllib3.exceptions import InsecureRequestWarning
from typing import Optional, Required
from .measurementerror import MeasurementError
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class kvmd():

  manufacturer = 'pikvm.org'
  model = 'PiKVM'

  def __init__(self, config: Required[dict], addr: Optional[str] = None):
    self.config = config

  @property
  def atx_power(self):
    """The state of power applied to the host."""
    try:
      res = requests.get(
        url="http://localhost/api/atx",
        verify=False,
        headers={
          "X-KVMD-User":   self.config['pikvm_username'],
          "X-KVMD-Passwd": self.config['pikvm_password']
        }
      ).json()
      return "ON" if res['result']['leds']['power'] else "OFF"
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

