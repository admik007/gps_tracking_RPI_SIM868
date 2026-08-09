from gps import GPS
from logger import Logger
import time, sdcard


gps = GPS()
log = Logger()

last_ts = ""


while True:
 point = gps.read()
 if point["valid"]:
  if point["ts"] != last_ts:
   last_ts = point["ts"]
   log.write(point)
   print("WRITE", point)
 time.sleep(0.1)