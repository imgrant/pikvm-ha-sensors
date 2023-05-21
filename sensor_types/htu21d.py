from typing import Optional
from datetime import datetime
from busio import I2C
from board import SCL, SDA
import adafruit_htu21d
from .measurementerror import MeasurementError

I2C_ADDRESS = 0x40
_ID1_CMD = bytearray([0xFA, 0x0F])
_ID2_CMD = bytearray([0xFC, 0xC9])

bus = I2C(SCL, SDA)

def _convert_to_integer(bytes_to_convert):
    """Use bitwise operators to convert the bytes into integers."""
    integer = None
    for chunk in bytes_to_convert:
        if not integer:
            integer = chunk
        else:
            integer = integer << 8
            integer = integer | chunk
    return integer


class htu21d(adafruit_htu21d.HTU21D):

  manufacturer = 'Measurement Specialities'
  model = 'HTU21D'

  def __init__(self, i2c_dev=bus, addr=I2C_ADDRESS, config: Optional[dict] = None):
    super().__init__(i2c_bus=i2c_dev, address=addr)

  # N.B. 'temperature' and 'relative_humidity' properties
  # are provided by the super class
  
  @property
  def serial_number(self):
    """The hardware identifier (serial number) for the device."""
    # The registers and format of the serial number is the same as for Si7021
    # See also: getSerialNumber() from https://www.espruino.com/modules/HTU21D.js
    try:
      # Serial 1st half
      data = _ID1_CMD
      id1 = bytearray(8)
      with self.i2c_device as i2c:
          i2c.write_then_readinto(data, id1)
      # Serial 2nd half
      data = _ID2_CMD
      id2 = bytearray(6)
      with self.i2c_device as i2c:
          i2c.write_then_readinto(data, id2)
      # Common/fixed bytes for all HTU21D sensors
      if id2[3] != 0x48 or id2[4] != 0x54 or id1[0] != 0x00 or id2[0] != 0x32:
        raise RuntimeError("Invalid serial number")
      # The unique serial number part is formed from the remaining bytes
      serial = (id1[2] << 24) | (id1[4] << 16) | (id1[6] << 8) | id2[1]
      return str(serial)
    except Exception as e:
      return "Unknown"
