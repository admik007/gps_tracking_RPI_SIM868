import machine
import time
import modem
from trackpoint import create


class GPS:
    """SIM868 GNSS reader using the modem's existing UART0."""

    POLL_INTERVAL_MS = 5000
    RTC_SYNC_INTERVAL_MS = 60 * 60 * 1000

    def __init__(self):
        self.point = create()
        self.last_poll_ticks = None
        self.last_rtc_sync_ticks = None
        self.started = False

    def start(self):
        try:
            response = modem.send_at_get_response("AT+CGNSPWR=1", "OK", 5000)
            text = response.decode("utf-8", "ignore")
            if "OK" not in text:
                print("SIM868 GNSS power-on failed:", text)
                return False
            self.started = True
            print("SIM868 GNSS enabled")
            return True
        except Exception as e:
            print("SIM868 GNSS start error:", e)
            return False

    def rtc_datetime(self):
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
        return self.rtc_datetime()

    def rtc_fields(self):
        try:
            dt = machine.RTC().datetime()
            if not self.rtc_datetime():
                return "", ""
            date = "{:02d}{:02d}{:02d}".format(dt[2], dt[1], dt[0] % 100)
            ts = "{:02d}{:02d}{:02d}.000".format(dt[4], dt[5], dt[6])
            return date, ts
        except Exception as e:
            print("RTC fields error:", e)
            return "", ""

    def read(self):
        if not self.started:
            return self.point
        now = time.ticks_ms()
        if (self.last_poll_ticks is not None and
                time.ticks_diff(now, self.last_poll_ticks) < self.POLL_INTERVAL_MS):
            return self.point
        self.last_poll_ticks = now
        try:
            response = modem.send_at_get_response("AT+CGNSINF", "OK", 3500)
            self.parse_cgnsinf(response.decode("utf-8", "ignore"))
        except Exception as e:
            print("SIM868 GNSS read error:", e)
            self.point["valid"] = False
        return self.point

    def parse_cgnsinf(self, response):
        for line in response.splitlines():
            line = line.strip()
            if not line.startswith("+CGNSINF:"):
                continue
            fields = line.split(":", 1)[1].strip().split(",")
            if len(fields) < 8:
                self.point["valid"] = False
                return
            fix_valid = fields[1].strip() == "1"
            stamp = fields[2].strip()
            if len(stamp) >= 14 and stamp[:14].isdigit():
                self.point["date"] = stamp[6:8] + stamp[4:6] + stamp[2:4]
                self.point["ts"] = stamp[8:10] + stamp[10:12] + stamp[12:14] + ".000"
                self.sync_rtc(stamp)
            self.point["valid"] = fix_valid
            if not fix_valid:
                return
            try:
                lat = float(fields[3])
                lon = float(fields[4])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    self.point["valid"] = False
                    return
                self.point["lat"] = round(lat, 6)
                self.point["lon"] = round(lon, 6)
                self.point["alt"] = float(fields[5]) if fields[5] else 0.0
                self.point["spd"] = round(float(fields[6])) if fields[6] else 0
                self.point["dir"] = round(float(fields[7])) if fields[7] else 0
                if len(fields) > 15 and fields[15]:
                    self.point["sat"] = int(float(fields[15]))
            except (ValueError, IndexError) as e:
                print("CGNSINF parse error:", e)
                self.point["valid"] = False
            return
        self.point["valid"] = False

    def sync_rtc(self, stamp):
        if len(stamp) < 14 or not stamp[:14].isdigit():
            return False
        try:
            year = int(stamp[0:4])
            month = int(stamp[4:6])
            day = int(stamp[6:8])
            hour = int(stamp[8:10])
            minute = int(stamp[10:12])
            second = int(stamp[12:14])
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
            due = (not rtc_valid or self.last_rtc_sync_ticks is None or
                   time.ticks_diff(now, self.last_rtc_sync_ticks) >= self.RTC_SYNC_INTERVAL_MS)
            if not due:
                return False

            gps_tuple = (year, month, day, 0, hour, minute, second, 0)
            if not rtc_valid:
                rtc.datetime(gps_tuple)
                print("RTC initialized from SIM868 GNSS")
                self.last_rtc_sync_ticks = now
                return True

            try:
                gps_seconds = time.mktime((year, month, day, hour, minute, second, 0, 0))
                rtc_seconds = time.mktime((rtc_time[0], rtc_time[1], rtc_time[2],
                                           rtc_time[4], rtc_time[5], rtc_time[6], 0, 0))
                difference = gps_seconds - rtc_seconds
            except Exception:
                difference = 0

            self.last_rtc_sync_ticks = now
            if abs(difference) > 5:
                rtc.datetime(gps_tuple)
                print("RTC corrected from SIM868 GNSS:", difference, "s")
                return True
            return False
        except Exception as e:
            print("SIM868 RTC sync failed:", e)
            return False
