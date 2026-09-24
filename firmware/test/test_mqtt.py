from gps import GPS
from logger import Logger

import time
import modem
import mqtt
import json
modem.modem_init()
if mqtt.mqtt_connect():
 mqtt_ok = True
 print(mqtt.CLIENT_ID)
  
 mqtt.mqtt_publish("gps/"+mqtt.CLIENT_ID+"/status",'"id": mqtt.CLIENT_ID,"msg": "online"')
 mqtt.mqtt_publish("gps/"+mqtt.CLIENT_ID+"/status",{"id": mqtt.CLIENT_ID,"msg": "online"})                      
 mqtt.mqtt_publish("gps/bd6718189a7ba68a/status",{"lon": 21.20827, "dir": 120.0, "lat": 48.719, "alt": 353.6, "spd": 1.0, "sat": 14, "creg": 0, "cgatt": 0, "csq": 0, "time": "2026-08-08T131928.000Z"}) 
