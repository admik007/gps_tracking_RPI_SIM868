from machine import SPI, Pin
import os
import sdcard
import time
import machine


PENDING_FILE = "/sd/pending.txt"
PENDING_TMP = "/sd/pending.tmp"

BATCH_SIZE = 20


class Logger:
    def __init__(self):
        print("Initializing SD logger...")

        self.spi = None
        self.cs = None
        self.sd = None
        self.sd_ok = False

        if self.init_sd():
            self.sd_ok = True
            print("SD logger ready")
        else:
            print("SD logger failed")
            print("SD logging disabled")
            print("MQTT will continue without SD logging")

    # =========================
    # SD INITIALIZATION
    # =========================
    def init_sd(self):
        for attempt in range(1, 4):
            print("SD init attempt {}/3".format(attempt))

            try:
                # UNMOUNT
                try:
                    os.umount("/sd")
                except:
                    pass

                # SPI
                self.spi = SPI(
                    0,
                    baudrate=10000000,
                    sck=Pin(18),
                    mosi=Pin(19),
                    miso=Pin(16)
                )

                # CHIP SELECT
                self.cs = Pin(
                    17,
                    Pin.OUT,
                    value=1
                )

                # SPI IDLE CLOCKS
                self.spi.write(b"\xff" * 10)
                time.sleep_ms(100)

                # SD CARD
                self.sd = sdcard.SDCard(
                    self.spi,
                    self.cs
                )

                # MOUNT
                os.mount(
                    self.sd,
                    "/sd"
                )

                print("SD logger ready")
                return True

            except Exception as e:
                print("SD init failed:", e)

                try:
                    os.umount("/sd")
                except:
                    pass

                if self.cs is not None:
                    self.cs.value(1)

                time.sleep_ms(500)

        return False

    # =========================
    # FILE NAME
    # =========================
    def filename(self, point):
        d = point["date"]
        t = point["ts"]

        year = "20" + d[4:6]
        month = d[2:4]
        day = d[0:2]
        hour = t[0:2]

        return "/sd/{year}.{month}.{day}-{hour}.txt".format(
            year=year,
            month=month,
            day=day,
            hour=hour
        )

    # =========================
    # POINT LINE
    # =========================
    def point_line(self, point, network_info=None):
        if network_info is None:
            network_info = {
                "csq": 0,
                "creg": 0,
                "cgatt": 0
            }

        return (
            "{date},"
            "{ts},"
            "{lat},"
            "{lon},"
            "{spd},"
            "{dir},"
            "{alt},"
            "{sat},"
            "{csq},"
            "{creg},"
            "{cgatt}\n"
        ).format(
            date=point["date"],
            ts=point["ts"],
            lat=point["lat"],
            lon=point["lon"],
            spd=point["spd"],
            dir=point["dir"],
            alt=point["alt"],
            sat=point["sat"],
            csq=network_info["csq"],
            creg=network_info["creg"],
            cgatt=network_info["cgatt"]
        )

    # =========================
    # PERMANENT LOG
    # =========================
    def write(self, point, network_info=None):
        if not self.sd_ok:
            return False

        try:
            filename = self.filename(point)
            line = self.point_line(point, network_info)

            with open(filename, "a") as f:
                f.write(line)

            return True

        except Exception as e:
            print("SD permanent write failed:", e)
            self.sd_ok = False

            try:
                os.umount("/sd")
            except:
                pass

            return False

    # =========================
    # MQTT CACHE
    # =========================
    def cache(self, point, network_info=None):
        if not self.sd_ok:
            return False

        try:
            line = self.point_line(point, network_info)

            with open(PENDING_FILE, "a") as f:
                f.write(line)

            return True

        except Exception as e:
            print("SD cache write failed:", e)
            self.sd_ok = False

            try:
                os.umount("/sd")
            except:
                pass

            return False

    # =========================
    # WRITE + CACHE
    # =========================
    def write_and_cache(self, point, network_info=None):
        if not self.sd_ok:
            return False

        try:
            line = self.point_line(point, network_info)
            filename = self.filename(point)

            with open(filename, "a") as f:
                f.write(line)

            with open(PENDING_FILE, "a") as f:
                f.write(line)

            return True

        except Exception as e:
            print("SD write and cache failed:", e)
            self.sd_ok = False

            try:
                os.umount("/sd")
            except:
                pass

            return False

    # =========================
    # PENDING EXISTS
    # =========================
    def pending_exists(self):
        try:
            os.stat(PENDING_FILE)
            return True
        except OSError:
            return False

    # =========================
    # READ BATCH
    # =========================
    def read_pending_batch(self, count=BATCH_SIZE):
        if not self.pending_exists():
            return []

        lines = []

        try:
            with open(PENDING_FILE, "r") as f:
                for _ in range(count):
                    line = f.readline()

                    if not line:
                        break

                    line = line.strip()

                    if line:
                        lines.append(line)

        except Exception as e:
            print("Pending batch read error:", e)

        return lines

    # =========================
    # REMOVE BATCH
    # =========================
    def pending_pop_batch(self, count):
        if count <= 0:
            return False

        if not self.pending_exists():
            return False

        try:
            with open(PENDING_FILE, "r") as src:
                skipped = 0

                # Preskočí odoslané riadky
                while skipped < count:
                    line = src.readline()

                    if not line:
                        break

                    skipped += 1

                # Zapíše zvyšok do dočasného súboru
                with open(PENDING_TMP, "w") as dst:
                    while True:
                        line = src.readline()

                        if not line:
                            break

                        dst.write(line)

            # Odstránenie pôvodného súboru
            try:
                os.remove(PENDING_FILE)
            except OSError:
                pass

            # Premenovanie dočasného súboru
            os.rename(
                PENDING_TMP,
                PENDING_FILE
            )

            return True

        except Exception as e:
            print("Pending batch remove error:", e)
            return False

    # =========================
    # FLUSH ONE BATCH
    # =========================
    def flush_pending(
        self,
        mqtt_publish,
        topic,
        device_id,
        batch_size=BATCH_SIZE
    ):
        if not self.sd_ok:
            return 0

        import json

        lines = self.read_pending_batch(batch_size)

        if not lines:
            return 0

        points = []

        for line in lines:
            fields = line.split(",")

            # Poškodený riadok preskočíme.
            # Po úspešnom odoslaní sa však odstráni
            # celý načítaný batch, aby nezablokoval frontu.
            if len(fields) < 11:
                print("Invalid pending line, removing:", line)
                continue

            try:
                # GPS TIME UTC
                gps_time = (
                    "20" +
                    fields[0][4:6] + "-" +
                    fields[0][2:4] + "-" +
                    fields[0][0:2] +
                    "T" +
                    fields[1] +
                    "Z"
                )

                # POINT
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
                    "time": gps_time
                }

                points.append(point)

            except Exception as e:
                print("Pending parse error, removing line:", e)

        # Batch obsahoval iba neplatné riadky.
        # Odstránime ich, aby nezablokovali frontu.
        if not points:
            if self.pending_pop_batch(len(lines)):
                print("Removed invalid pending batch:", len(lines))
                return len(lines)

            print("Could not remove invalid pending batch")
            return 0

        # BATCH PAYLOAD
        payload = {
            "id": device_id,
            "points": points
        }

        message = json.dumps(payload)

        print(
            "Sending pending batch:",
            len(points),
            "points"
        )

        print(
            "MQTT payload length:",
            len(message)
        )

        # MQTT SEND
        try:
            result = mqtt_publish(
                topic,
                message
            )

            print(
                "Pending MQTT result:",
                repr(result)
            )

        except Exception as e:
            print("Pending MQTT error:", e)
            return 0

        # SEND FAILED
        if not result:
            print("Pending batch MQTT send failed")
            return 0

        # SEND OK
        # Odstránime celý načítaný batch, vrátane
        # prípadných poškodených riadkov.
        if not self.pending_pop_batch(len(lines)):
            print(
                "WARNING: batch sent but cache "
                "could not be updated"
            )
            return 0

        print(
            "Pending batch sent and removed:",
            len(lines)
        )

        return len(points)

    # =========================
    # PENDING COUNT
    # =========================
    def pending_count(self):
        if not self.pending_exists():
            return 0

        count = 0

        try:
            with open(PENDING_FILE, "r") as f:
                while True:
                    line = f.readline()

                    if not line:
                        break

                    if line.strip():
                        count += 1

        except Exception as e:
            print("Pending count error:", e)

        return count

    # =========================
    # CLEAR PENDING
    # =========================
    def clear_pending(self):
        try:
            os.remove(PENDING_FILE)
        except OSError:
            pass

    # =========================
    # LIST FILES
    # =========================
    def list_files(self):
        if not self.sd_ok:
            return []

        try:
            return os.listdir("/sd")
        except Exception as e:
            print("SD list files failed:", e)
            return []
