#!/usr/bin/env python3
import sys, socket, traceback
import netifaces
import json, yaml, time
import re, uuid
from datetime import datetime
from typing import List, Optional
import importlib
import paho.mqtt.client as mqtt
from threading import Thread
import kvmd
from sensor_types.measurementerror import MeasurementError


def get_rpi_serial():
  cpuserial = "0000000000000000"
  try:
    f = open('/sys/firmware/devicetree/base/serial-number','r')
    cpuserial = f.readline().rstrip('\x00')
    f.close()
  except:
    cpuserial = "ERROR000000000"
  return cpuserial

def get_rpi_model():
  model = "Unknown model"
  try:
    f = open('/sys/firmware/devicetree/base/model','r')
    model = f.readline().rstrip('\x00')
    f.close()
  except:
    model = "Error (unknown model)"
  return model

def get_rpi_hw():
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

def get_rpi_hw_revision():
  rev = "000000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:8]=='Revision':
        rev = line[10:26].strip()
    f.close()
  except:
    rev = "ERROR000000"
  return rev

def get_kvmd_server_host():
  server = "N/A"
  with open("/etc/kvmd/meta.yaml", "r") as kvmd_meta:
    try:
      api_info = yaml.safe_load(kvmd_meta)
      server = api_info['server']['host']
    except yaml.YAMLError as e:
      server = "{host}.local".format(host=socket.gethostname())
  return server


class PiKVMHASensors:

  default_config = {      
    'update_period':          30,
    'valid_time':             600,
    'verbose':                False,
    'mqtt_broker':            None,  # Must be overridden
    'mqtt_port':              1883,
    'mqtt_transport':         'tcp',  # 'tcp' or 'websockets'
    'mqtt_use_tls':           False,
    'mqtt_username':          None,
    'mqtt_password':          None,
    'mqtt_ha_prefix':         'homeassistant',
    'pikvm_username':         'admin',
    'pikvm_password':         None  # Must be overridden (unless auth is disabled)
  }

  unique_id = 'pikvm_{}'.format(get_rpi_serial()[-6:]) # suffix is last six digits of serial number
  device_info = {
    'identifiers':        [
                            socket.gethostname(),
                            unique_id,
                            get_rpi_serial()
                          ],
    'connections':        [],
    'manufacturer':       "pikvm.org",
    'model':              "PiKVM ({rpi_model})".format(rpi_model=get_rpi_model()),
    'hw_version':         "{hardware} (rev {revision})".format(hardware=get_rpi_hw(), revision=get_rpi_hw_revision()),
    'sw_version':         "kvmd v{kvmd_version}".format(kvmd_version=kvmd.__version__),
    'name':               "PiKVM - open-source DIY IP-KVM",
    'configuration_url':  "https://{host}".format(host=get_kvmd_server_host())
  }

  sensors = []
  sensor_template = {
    'name':               None,
    'id':                 None,
    'instance':           None,
    'device_type':        None,
    'device_address':     None,
    'device_property':    None,
    'device_offset':      None,
    'units':              None,
    'output_precision':   None,
    'display_precision':  None,
    'ha_component_type':  None,
    'ha_device_class':    None,
    'ha_entity_category': None,
    'ha_icon':            None,
    'ha_title':           None
  } 


  def __init__(self, user_config, sensors):
    # Merge user config with base config parameters;
    self.config = { **self.default_config, **user_config }
    # Overlay sensors dict on base sensor template dict
    for sensor in sensors:
      s = self.sensor_template | sensor
      self.sensors.append(s)
    self.mqtt_client     = None
    self.mqtt_connected  = False
    self.ha_registered   = False
    self.worker          = None
    self.device_info['connections'] = [
                                        [ "mac_address", ':'.join(re.findall('..', '%012x' % uuid.getnode())).lower() ],
                                        [ "ipv4_address", netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr'] ],
                                        [ "ipv6_address", netifaces.ifaddresses('eth0')[netifaces.AF_INET6][0]['addr'] ],
                                        [ "fqdn",         socket.getfqdn() ],
                                        [ "server_host",  get_kvmd_server_host() ]
                                      ]

  def info(self, message):
    if self.config['verbose'] == True:
      print("INFO: {}".format(message))

  def error(self, message):
    sys.exit("ERROR: {}".format(message))

  @staticmethod
  def transport_to_protocol(transport):
    match transport:
      case 'tcp':
        return "http"
      case 'websockets':
        return "ws"
      case _:
        return transport

  def mqtt_connect(self):
    broker = "{}:{}".format(self.config['mqtt_broker'], str(self.config['mqtt_port']))
    protocol = "{p}{t}://".format(
      p=self.transport_to_protocol(self.config['mqtt_transport']),
      t="s" if self.config['mqtt_use_tls'] else ""
    )
    if self.mqtt_broker_reachable():
      self.info("Connecting to MQTT broker at {p}{h} ...".format(p=protocol, h=broker))
      self.mqtt_client = mqtt.Client(client_id=self.unique_id, transport=self.config['mqtt_transport'])
      if self.config['mqtt_username'] is not None and self.config['mqtt_password'] is not None:
        self.mqtt_client.username_pw_set(self.config['mqtt_username'], self.config['mqtt_password'])
      if self.config['mqtt_use_tls'] is True:
        self.mqtt_client.tls_set()
      self.mqtt_client.on_connect = self.mqtt_on_connect
      self.mqtt_client.on_disconnect = self.mqtt_on_disconnect
      try:
        self.mqtt_client.connect(self.config['mqtt_broker'], int(self.config['mqtt_port']), 30)
        self.mqtt_client.loop_forever()
        time.sleep(1)
      except:
        self.info(traceback.format_exc())
        self.mqtt_client = None
    else:
      self.error("Unable to reach MQTT broker at {}".format(broker))

  def mqtt_on_connect(self, mqtt_client, userdata, flags, rc):
    self.mqtt_connected = True
    self.info('MQTT broker connected!')
    if self.ha_registered is False:
      for sensor in self.sensors:
        self.publish_ha_discovery(sensor)
      for sensor in self.sensors:
        self.publish_attributes(sensor)
      self.ha_registered = True

  def mqtt_on_disconnect(self, mqtt_client, userdata, rc):
    self.mqtt_connected = False
    self.info('MQTT broker disconnected! Will reconnect ...')
    if rc == 0:
      self.mqtt_connect()
    else:
      time.sleep(5)
      while not self.mqtt_broker_reachable():
        time.sleep(10)
      self.mqtt_client.reconnect()

  def mqtt_broker_reachable(self):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
      s.connect((self.config['mqtt_broker'], int(self.config['mqtt_port'])))
      s.close()
      return True
    except socket.error:
      return False

  def publish_message(self, topic, payload, qos=0, retain=False):
    if self.mqtt_connected:
      self.mqtt_client.publish(topic=topic, payload=str(payload), qos=qos, retain=retain)
    else:
      self.info("Message publishing is unavailable when the MQTT broker is not connected")

  def init_sensor(self, sensor):
    self.info("Initialising sensor {name} (type: {module})".format(name=sensor['name'], module=sensor['device_type']))
    SensorClass = getattr(importlib.import_module("sensor_types.{}".format(sensor['device_type'])), sensor['device_type'])
    sensor['instance'] = SensorClass(addr=sensor['device_address'], config=self.config)

  def update(self):
    while True:
      for sensor in self.sensors:
        status_topic = "sensors/{}/status".format(sensor['id'])
        reading = {}
        try:
          # Read the measurement value from the sensor
          value = getattr(sensor['instance'], sensor['device_property'])
        except MeasurementError as error:
          self.publish_message(topic=status_topic, payload="offline")
          self.info("Failed to update measurements for sensor {} ({}). Sensor status will be set to offline.".format(sensor['id'], str(error)))
        else:
          self.publish_message(topic=status_topic, payload="online")
          reading['timestamp'] = datetime.now().isoformat(timespec='seconds')
          # Apply any offset correction and round value for output
          if value is not None and not isinstance(value, (bool, str)):
            if sensor['device_offset'] is not None:
              value += sensor['device_offset']
            reading['value'] = round(value, sensor['output_precision'])
          else:
            reading['value'] = value
          self.info("Publishing reading for sensor {}: {}".format(sensor['id'], ", ".join(['{0}={1}'.format(k, v) for k,v in reading.items()])))
          self.publish_message(topic="sensors/{}/state".format(sensor['id']), payload=json.dumps(reading))
      time.sleep(self.config['update_period'])

  def publish_attributes(self, sensor):
    self.info("Publishing attributes for sensor {}".format(sensor['name']))
    attr_data = {}
    attr_data['serial_number']  = sensor['instance'].serial_number
    attr_data['type']           = sensor['instance'].model
    attr_data['manufacturer']   = sensor['instance'].manufacturer
    self.publish_message(topic="sensors/{}/attributes".format(sensor['id']), payload=json.dumps(attr_data, indent=2), qos=1, retain=True)

  def publish_ha_discovery(self, sensor):
    self.info("Registering sensor {} with Home Assistant".format(sensor['name']))
    config_topic = "{prefix}/{component}/{node}/{object}/config".format(
                                                          prefix=self.config['mqtt_ha_prefix'],
                                                          component=sensor['ha_component_type'],
                                                          node=self.unique_id,
                                                          object=sensor['name'])
    config_data = {}
    config_data['unique_id']              = sensor['id']
    config_data['state_topic']            = "sensors/{}/state".format(sensor['id'])
    config_data['availability_topic']     = "sensors/{}/status".format(sensor['id'])
    config_data['json_attributes_topic']  = "sensors/{}/attributes".format(sensor['id']) # See publish_attributes() above
    config_data['device']                 = self.device_info
    if sensor['ha_device_class'] is not None:
      config_data['device_class']           = sensor['ha_device_class']
    if sensor['ha_icon'] is not None:
      config_data['icon']                   = sensor['ha_icon']
    if sensor['ha_entity_category'] is not None:
      config_data['entity_category']        = sensor['ha_entity_category']
    if sensor['units'] is not None:
      config_data['unit_of_measurement']    = sensor['units']
    config_data['name']                   = "{}".format(sensor['ha_title'])
    config_data['object_id']              = "{}".format(sensor['id'])
    if sensor['display_precision'] is not None:
      config_data['suggested_display_precision'] = sensor['display_precision']
    config_data['value_template']         = "{{{{ value_json.{field} }}}}".format(field='value')
    config_data['force_update']           = True
    config_data['expire_after']           = self.config['valid_time']
    self.publish_message(topic=config_topic, payload=json.dumps(config_data, indent=2), qos=1, retain=True)


  def start(self):
    for sensor in self.sensors:
      self.init_sensor(sensor)
    self.worker = Thread(target=self.update)
    self.worker.daemon = True
    self.worker.start()
    self.mqtt_connect()


def main(args):
  config = {}
  if len(args) > 0:
    file = args[0]
  else:
    file = "config.yaml"
  try:
    with open(file, 'r') as yamlconfig:
      config = yaml.safe_load(yamlconfig)
  except Exception as e:
    sys.exit("ERROR: {}".format(str(e)))

  sensors = []
  if len(args) > 1:
    file = args[1]
  else:
    file = "sensors.yaml"
  try:
    with open(file, 'r') as yamlsensors:
      sensors = yaml.safe_load(yamlsensors)
  except Exception as e:
    sys.exit("ERROR: {}".format(str(e)))
  
  pikvmha = PiKVMHASensors(config, sensors)
  pikvmha.start()

if __name__ == "__main__":
  main(sys.argv[1:])
