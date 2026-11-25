"""Emergency offline queue stored in the Pico's internal filesystem.

Used only when the SD card is unavailable and MQTT is offline.
The queue is append-only and never overwrites unconfirmed records.
"""
import os
import json

QUEUE_FILE = "/flash_pending.txt"
OFFSET_FILE = "/flash_pending.pos"
OFFSET_TMP = "/flash_pending.pos.tmp"
MAX_QUEUE_BYTES = 2 * 1024 * 1024
FLASH_RESERVE_BYTES = 256 * 1024
BATCH_SIZE = 5


class FlashLogger:
    def __init__(self):
        self.enabled = False
        try:
            stats = os.statvfs("/")
            free_bytes = stats[0] * stats[3]
            self.max_bytes = min(
                MAX_QUEUE_BYTES,
                max(0, free_bytes - FLASH_RESERVE_BYTES)
            )
            if self.max_bytes < 4096:
                raise OSError("Not enough free internal flash space")
            self.enabled = True
            print("Flash fallback ready; queue limit:", self.max_bytes)
        except Exception as e:
            self.max_bytes = 0
            print("Flash fallback unavailable:", e)

    def point_line(self, point, network_info=None):
        if network_info is None:
            network_info = {}
        return (
            str(point["date"]) + "," +
            str(point["ts"]) + "," +
            str(point["lat"]) + "," +
            str(point["lon"]) + "," +
            str(point["spd"]) + "," +
            str(point["dir"]) + "," +
            str(point["alt"]) + "," +
            str(point["sat"]) + "," +
            str(network_info.get("csq", 0)) + "," +
            str(network_info.get("creg", 0)) + "," +
            str(network_info.get("cgatt", 0)) + "," +
            str(network_info.get("mcc", "")) + "," +
            str(network_info.get("mnc", "")) + "," +
            str(network_info.get("bsic", 0)) + "," +
            str(network_info.get("cellid", 0)) + "," +
            str(network_info.get("lac", 0)) + "\n"
        )

    def _size(self):
        try:
            return os.stat(QUEUE_FILE)[6]
        except OSError:
            return 0

    def cache(self, point, network_info=None):
        if not self.enabled:
            return False
        try:
            line = self.point_line(point, network_info)
            if self._size() + len(line) > self.max_bytes:
                print("Flash queue full; preserving existing records")
                return False
            stats = os.statvfs("/")
            free_bytes = stats[0] * stats[3]
            if free_bytes < len(line) + FLASH_RESERVE_BYTES:
                print("Flash free-space reserve reached")
                return False
            with open(QUEUE_FILE, "a") as f:
                f.write(line)
                f.flush()
            try:
                os.sync()
            except AttributeError:
                pass
            return True
        except Exception as e:
            print("Flash queue write failed:", e)
            return False

    def _read_offset(self):
        for filename in (OFFSET_TMP, OFFSET_FILE):
            try:
                with open(filename, "r") as f:
                    value = int(f.read().strip())
                if 0 <= value <= self._size():
                    return value
            except Exception:
                pass
        return 0

    def _save_offset(self, offset):
        try:
            with open(OFFSET_TMP, "w") as f:
                f.write(str(offset))
                f.flush()
            try:
                os.sync()
            except AttributeError:
                pass
            try:
                os.remove(OFFSET_FILE)
            except OSError:
                pass
            os.rename(OFFSET_TMP, OFFSET_FILE)
            return True
        except Exception as e:
            print("Flash queue offset error:", e)
            return False

    def pending_exists(self):
        return self._read_offset() < self._size()

    def _cleanup(self):
        if self._size() and self._read_offset() >= self._size():
            for filename in (QUEUE_FILE, OFFSET_FILE, OFFSET_TMP):
                try:
                    os.remove(filename)
                except OSError:
                    pass

    def flush_pending(self, mqtt_publish, topic, device_id,
                      batch_size=BATCH_SIZE):
        if not self.enabled or not self.pending_exists():
            return 0

        start_offset = self._read_offset()
        lines = []
        end_offset = start_offset
        try:
            with open(QUEUE_FILE, "rb") as f:
                f.seek(start_offset)
                while len(lines) < batch_size:
                    raw = f.readline()
                    if not raw:
                        break
                    end_offset = f.tell()
                    try:
                        line = raw.decode().strip()
                    except Exception:
                        line = ""
                    if line:
                        lines.append(line)
        except Exception as e:
            print("Flash queue read failed:", e)
            return 0

        points = []
        for line in lines:
            fields = line.split(",")
            if len(fields) < 11:
                continue
            try:
                gps_time = (
                    "20" + fields[0][4:6] + "-" +
                    fields[0][2:4] + "-" + fields[0][0:2] +
                    "T" + fields[1] + "Z"
                )
                point = {
                    "lat": float(fields[2]),
                    "lon": float(fields[3]),
                    "spd": float(fields[4]),
                    "dir": float(fields[5]),
                    "alt": float(fields[6]),
                    "sat": int(fields[7]),
                    "csq": int(fields[8]),
                    "creg": int(fields[9]),
                    "cgatt": int(fields[10]),
                    "gps_valid": True,
                    "time": gps_time
                }
                if len(fields) >= 16:
                    point["mcc"] = fields[11]
                    point["mnc"] = fields[12]
                    point["bsic"] = int(fields[13] or 0)
                    point["cellid"] = int(fields[14] or 0)
                    point["lac"] = int(fields[15] or 0)
                else:
                    point["mcc"] = ""
                    point["mnc"] = ""
                    point["bsic"] = 0
                    point["cellid"] = 0
                    point["lac"] = 0
                points.append(point)
            except Exception as e:
                print("Flash queue parse error:", e)

        if not points:
            if self._save_offset(end_offset):
                self._cleanup()
            return 0

        payload = json.dumps({"id": device_id, "points": points})
        try:
            result = mqtt_publish(topic, payload)
        except Exception as e:
            print("Flash MQTT send error:", e)
            return 0

        if not result:
            return 0
        if not self._save_offset(end_offset):
            print("Flash batch sent but offset update failed; batch may repeat")
            return 0

        self._cleanup()
        print("Flash batch sent:", len(points))
        return len(points)
