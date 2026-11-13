from machine import UART, Pin
import machine
import time
from trackpoint import create


class GPS:

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
        self.last_rtc_sync_ticks = None

    # =========================================================
    # DATETIME
    # =========================================================
    RTC_SYNC_INTERVAL_MS = 60 * 60 * 1000

    def rtc_datetime(self):
        """Return the Pico RTC time in UTC, or an empty string if invalid."""
        try:
            dt = machine.RTC().datetime()
            year, month, day = dt[0], dt[1], dt[2]
            hour, minute, second = dt[4], dt[5], dt[6]

            if year < 2022 or not (1 <= month <= 12):
                return ""
            if not (1 <= day <= 31 and 0 <= hour <= 23):
                return ""
            if not (0 <= minute <= 59 and 0 <= second <= 59):
                return ""

            return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                year, month, day, hour, minute, second
            )
        except Exception as e:
            print("RTC datetime error:", e)
            return ""

    def gps_datetime(self):
        # Pico RTC is the single time source for MQTT and application logs.
        return self.rtc_datetime()

    def rtc_fields(self):
        """Return RTC date/time in the format expected by the SD logger."""
        try:
            dt = machine.RTC().datetime()
            if not self.rtc_datetime():
                return "", ""

            date = "{:02d}{:02d}{:02d}".format(
                dt[2], dt[1], dt[0] % 100
            )
            ts = "{:02d}{:02d}{:02d}.000".format(
                dt[4], dt[5], dt[6]
            )
            return date, ts
        except Exception as e:
            print("RTC fields error:", e)
            return "", ""

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

        # RMC carries UTC date/time even when navigation status is V.
        # Capture and use it to maintain the Pico RTC independently of fix.
        self.point["ts"] = fields[1]
        self.point["date"] = fields[9]
        self.sync_rtc()

        # Keep the last known coordinates and movement values when the
        # receiver loses its fix. app.py marks them with gps_valid=False.
        if not self.point["valid"]:
            return

        self.point["lat"] = self.convert(fields[3], fields[4])
        self.point["lon"] = self.convert(fields[5], fields[6])

        try:
            self.point["spd"] = round(float(fields[7]) * 1.852)
        except Exception:
            pass

        try:
            self.point["dir"] = round(float(fields[8]))
        except Exception:
            pass

    # =========================================================
    # SYNC RTC
    # =========================================================
    def sync_rtc(self):
        d = self.point.get("date", "")
        t = self.point.get("ts", "")

        if not d or not t or len(d) < 6 or len(t) < 6:
            return False

        try:
            day = int(d[0:2])
            month = int(d[2:4])
            year = 2000 + int(d[4:6])

            hour = int(t[0:2])
            minute = int(t[2:4])
            second = int(float(t[4:]))

            # Reject missing/obviously invalid GNSS time.
            if year < 2022 or year > 2099:
                return False
            if not (1 <= month <= 12 and 1 <= day <= 31):
                return False
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                return False

            now = time.ticks_ms()
            rtc = machine.RTC()
            rtc_time = rtc.datetime()
            rtc_valid = rtc_time[0] >= 2022

            # Set RTC immediately if it has not yet been initialized.
            # Otherwise compare/correct at most once per hour.
            due = (
                not rtc_valid
                or self.last_rtc_sync_ticks is None
                or time.ticks_diff(now, self.last_rtc_sync_ticks)
                    >= self.RTC_SYNC_INTERVAL_MS
            )

            if not due:
                return False

            gps_tuple = (
                year, month, day, 0,
                hour, minute, second, 0
            )

            if not rtc_valid:
                rtc.datetime(gps_tuple)
                print(
                    "RTC initialized from GNSS:",
                    "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                        year, month, day, hour, minute, second
                    )
                )
                self.last_rtc_sync_ticks = now
                return True

            try:
                gps_seconds = time.mktime((
                    year, month, day, hour, minute, second, 0, 0
                ))
                rtc_seconds = time.mktime((
                    rtc_time[0], rtc_time[1], rtc_time[2],
                    rtc_time[4], rtc_time[5], rtc_time[6], 0, 0
                ))
                difference = gps_seconds - rtc_seconds
            except Exception:
                difference = 0

            self.last_rtc_sync_ticks = now

            if abs(difference) > 5:
                rtc.datetime(gps_tuple)
                print("RTC corrected from GNSS, difference:", difference, "s")
                return True

            print("RTC hourly check OK, difference:", difference, "s")
            return False

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
            self.point["spd"] = round(float(fields[7]))
        except Exception:
            pass

    # =========================================================
    # COORDINATES
    # =========================================================
    def convert(self, value, direction):
        if not value:
            return 0.0

        value = float(value)
        degrees = int(value / 100)
        minutes = value - (degrees * 100)
        result = degrees + (minutes / 60)

        if direction in ("S", "W"):
            result *= -1

        return round(result, 6)