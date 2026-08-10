from machine import UART, Pin
import machine
import time
from trackpoint import create


class GPS:

    # =========================================================
    # DATETIME
    # =========================================================

    def gps_datetime(self):

        d = self.point["date"]
        t = self.point["ts"]

        # ---------------------------------
        # GPS TIME
        # ---------------------------------

        if d and t:

            try:
                day = int(d[0:2])
                month = int(d[2:4])
                year = 2000 + int(d[4:6])

                hour = int(t[0:2])
                minute = int(t[2:4])
                second = int(float(t[4:]))

                # GPS has valid date/time
                # 2021 = invalid/default GPS time
                if year != 2021:

                    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                        year,
                        month,
                        day,
                        hour,
                        minute,
                        second
                    )

            except Exception as e:
                print("GPS datetime error:", e)

        # ---------------------------------
        # GPS TIME INVALID
        # USE RPI RTC
        # ---------------------------------

        try:
            dt = machine.RTC().datetime()

            # RTC year 2021 = not synchronized yet
            if dt[0] != 2021:

                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0],
                    dt[1],
                    dt[2],
                    dt[4],
                    dt[5],
                    dt[6]
                )

        except Exception as e:
            print("RTC datetime error:", e)

        # Neither GPS nor RTC has valid time
        return ""


    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):

        self.uart = UART(
            1,
            baudrate=9600,
            tx=Pin(4),
            rx=Pin(5),
            timeout=100
        )

        self.buffer = b""
        self.point = create()


    # =========================================================
    # READ
    # =========================================================

    def read(self):

        if self.uart.any():

            data = self.uart.read()

            if data:
                self.buffer += data

        while b"\n" in self.buffer:

            line, self.buffer = self.buffer.split(b"\n", 1)

            try:
                line = line.decode().strip()
            except Exception:
                continue

            self.parse(line)

        return self.point


    # =========================================================
    # PARSE
    # =========================================================

    def parse(self, line):

        if line.startswith("$GNRMC") or line.startswith("$GPRMC"):
            self.parse_rmc(line)

        elif line.startswith("$GNGGA") or line.startswith("$GPGGA"):
            self.parse_gga(line)

        elif line.startswith("$GNVTG") or line.startswith("$GPVTG"):
            self.parse_vtg(line)


    # =========================================================
    # RMC
    # =========================================================

    def parse_rmc(self, line):

        fields = line.split(",")

        if len(fields) < 10:
            return

        self.point["valid"] = (fields[2] == "A")

        # ---------------------------------
        # NO GPS FIX
        # ---------------------------------

        if not self.point["valid"]:
            return

        # ---------------------------------
        # GPS TIME / DATE
        # ---------------------------------

        self.point["ts"] = fields[1]
        self.point["date"] = fields[9]

        # ---------------------------------
        # GPS POSITION
        # ---------------------------------

        self.point["lat"] = self.convert(
            fields[3],
            fields[4]
        )

        self.point["lon"] = self.convert(
            fields[5],
            fields[6]
        )

        # ---------------------------------
        # SPEED
        # ---------------------------------

        try:
            self.point["spd"] = round(
                float(fields[7]) * 1.852
            )
        except Exception:
            pass

        # ---------------------------------
        # DIRECTION
        # ---------------------------------

        try:
            self.point["dir"] = round(
                float(fields[8])
            )
        except Exception:
            pass

        # ---------------------------------
        # SYNC RPI RTC FROM GPS
        # ---------------------------------

        self.sync_rtc()


    # =========================================================
    # SYNC RTC
    # =========================================================

    def sync_rtc(self):

        d = self.point["date"]
        t = self.point["ts"]

        if not d or not t:
            return False

        try:

            day = int(d[0:2])
            month = int(d[2:4])
            year = 2000 + int(d[4:6])

            hour = int(t[0:2])
            minute = int(t[2:4])
            second = int(float(t[4:]))

            # ---------------------------------
            # 2021 = INVALID GPS TIME
            # ---------------------------------

            if year == 2021:
                return False

            # ---------------------------------
            # GPS timestamp
            # ---------------------------------

            gps_tuple = (
                year,
                month,
                day,
                0,
                hour,
                minute,
                second,
                0
            )

            rtc = machine.RTC()
            rtc_time = rtc.datetime()

            # ---------------------------------
            # RTC NOT SYNCHRONIZED
            # ---------------------------------

            if rtc_time[0] == 2021:

                rtc.datetime(gps_tuple)

                print(
                    "RTC synchronized from GPS:",
                    "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                        year,
                        month,
                        day,
                        hour,
                        minute,
                        second
                    )
                )

                return True

            # ---------------------------------
            # RTC ALREADY VALID
            # ---------------------------------
            #
            # Nechceme RTC prepisovať každú sekundu.
            # Skontrolujeme iba rozdiel medzi GPS a RTC.
            # ---------------------------------

            try:

                gps_seconds = time.mktime((
                    year,
                    month,
                    day,
                    hour,
                    minute,
                    second,
                    0,
                    0
                ))

                rtc_seconds = time.mktime((
                    rtc_time[0],
                    rtc_time[1],
                    rtc_time[2],
                    rtc_time[4],
                    rtc_time[5],
                    rtc_time[6],
                    0,
                    0
                ))

                difference = abs(
                    gps_seconds - rtc_seconds
                )

            except Exception:

                difference = 0

            # ---------------------------------
            # GPS / RTC DIFFERENCE
            # ---------------------------------

            if difference > 5:

                rtc.datetime(gps_tuple)

                print(
                    "RTC corrected from GPS, difference:",
                    difference,
                    "s"
                )

                return True

            return False

        except Exception as e:

            print("RTC sync failed:", e)

            return False

    def gps_datetime(self):
        d = self.point["date"]
        t = self.point["ts"]

        # ---------------------------------
        # GPS TIME
        # ---------------------------------

        if d and t:

            try:

                day = int(d[0:2])
                month = int(d[2:4])
                year = 2000 + int(d[4:6])

                hour = int(t[0:2])
                minute = int(t[2:4])
                second = int(float(t[4:]))

                # GPS time valid
                if year != 2021:

                    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                        year,
                        month,
                        day,
                        hour,
                        minute,
                        second
                    )

            except Exception as e:

                print("GPS datetime error:", e)

        # ---------------------------------
        # GPS INVALID
        # USE RTC
        # ---------------------------------

        try:

            dt = machine.RTC().datetime()

            if dt[0] != 2021:

                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0],
                    dt[1],
                    dt[2],
                    dt[4],
                    dt[5],
                    dt[6]
                )

        except Exception as e:

            print("RTC datetime error:", e)

        # ---------------------------------
        # NO VALID TIME
        # ---------------------------------

        return ""




    def sync_rtc(self):

        d = self.point["date"]
        t = self.point["ts"]

        if not d or not t:
            return False

        try:

            day = int(d[0:2])
            month = int(d[2:4])
            year = 2000 + int(d[4:6])

            hour = int(t[0:2])
            minute = int(t[2:4])
            second = int(float(t[4:]))

            # ---------------------------------
            # 2021 = INVALID GPS TIME
            # ---------------------------------

            if year == 2021:
                return False

            rtc = machine.RTC()

            rtc.datetime((
                year,
                month,
                day,
                0,
                hour,
                minute,
                second,
                0
            ))

            return True

        except Exception as e:

            print("RTC sync failed:", e)

            return False


    # =========================================================
    # GGA
    # =========================================================

    def parse_gga(self, line):

        fields = line.split(",")

        if len(fields) < 10:
            return

        try:
            self.point["sat"] = int(fields[7])
        except Exception:
            pass

        try:
            self.point["alt"] = float(fields[9])
        except Exception:
            pass


    # =========================================================
    # VTG
    # =========================================================

    def parse_vtg(self, line):

        fields = line.split(",")

        if len(fields) < 9:
            return

        try:
            self.point["spd"] = round(
                float(fields[7])
            )
        except Exception:
            pass


    # =========================================================
    # COORDINATES
    # =========================================================

    def convert(self, value, dir):

        if not value:
            return 0.0

        value = float(value)

        degrees = int(value / 100)

        minutes = value - (degrees * 100)

        result = degrees + (minutes / 60)

        if dir in ("S", "W"):
            result *= -1

        return round(result, 6)
