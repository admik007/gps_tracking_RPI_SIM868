from machine import UART, Pin
import time
from trackpoint import create

class GPS:
    def gps_datetime(self):
    
        if not self.point["date"] or not self.point["ts"]:
            return ""
        d = self.point["date"]
        t = self.point["ts"]

        # RMC dátum: DDMMYY
        day = d[0:2]
        month = d[2:4]
        year = "20" + d[4:6]

        # čas: HHMMSS.sss
        hour = t[0:2]
        minute = t[2:4]
        second = t[4:]
        return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"


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


    def parse(self, line):
        if line.startswith("$GNRMC") or line.startswith("$GPRMC"):
            self.parse_rmc(line)
        elif line.startswith("$GNGGA") or line.startswith("$GPGGA"):
            self.parse_gga(line)
        elif line.startswith("$GNVTG") or line.startswith("$GPVTG"):
            self.parse_vtg(line)


    def parse_rmc(self, line):
        fields = line.split(",")
        if len(fields) < 10:
            return
        self.point["valid"] = (fields[2] == "A")
        if not self.point["valid"]:
            return
        self.point["ts"] = fields[1]
        self.point["date"] = fields[9]
        self.point["lat"] = self.convert(
            fields[3],
            fields[4]
        )
        self.point["lon"] = self.convert(
            fields[5],
            fields[6]
        )
        try:
            self.point["spd"] = round(
                float(fields[7]) * 1.852
            )
        except Exception:
            pass
        try:
            self.point["dir"] = round(
                float(fields[8])
            )
        except Exception:
            pass


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