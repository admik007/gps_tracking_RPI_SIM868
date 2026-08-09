from buffer import Buffer
from gps import GPS
import time


gps = GPS()
buf = Buffer()

last_ts = ""


while True:

    point = gps.read()

    if point["valid"]:

        # uloz iba novy GPS bod
        if point["ts"] != last_ts:

            last_ts = point["ts"]

            buf.add(point)

            print("BUFFER:", buf.count())
            print(point)
            print(gps.gps_datetime())

    # po 10 bodoch vypis cely buffer
    if buf.count() >= 10:

        print("========== SEND BLOCK ==========")

        points = buf.get()

        for p in points:
            print(p)

        print("================================")

        buf.clear()


    time.sleep(0.1)