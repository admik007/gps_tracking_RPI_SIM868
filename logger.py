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

        if not self.init_sd():

            print("SD logger failed")

            # Posledná možnosť:
            # reštartuj celý RP2040
            print("Restarting MCU...")

            time.sleep_ms(500)

            machine.reset()


    # =========================
    # SD INITIALIZATION
    # =========================

    def init_sd(self):

        for attempt in range(1, 4):

            print(
                "SD init attempt {}/3".format(attempt)
            )

            try:

                # -------------------------
                # UNMOUNT
                # -------------------------

                try:
                    os.umount("/sd")
                except:
                    pass

                # -------------------------
                # SPI
                # -------------------------

                self.spi = SPI(
                    0,
                    baudrate=10000000,
                    sck=Pin(18),
                    mosi=Pin(19),
                    miso=Pin(16)
                )

                # -------------------------
                # CS
                # -------------------------

                self.cs = Pin(
                    17,
                    Pin.OUT,
                    value=1
                )

                # -------------------------
                # SPI IDLE
                # -------------------------

                self.spi.write(
                    b"\xff" * 10
                )

                time.sleep_ms(100)

                # -------------------------
                # SD CARD
                # -------------------------

                self.sd = sdcard.SDCard(
                    self.spi,
                    self.cs
                )

                # -------------------------
                # MOUNT
                # -------------------------

                os.mount(
                    self.sd,
                    "/sd"
                )

                print("SD logger ready")

                return True

            except Exception as e:

                print(
                    "SD init failed:",
                    e
                )

                # -------------------------
                # CLEANUP
                # -------------------------

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

        return f"/sd/{year}.{month}.{day}-{hour}.txt"


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
            f"{point['date']},"
            f"{point['ts']},"
            f"{point['lat']},"
            f"{point['lon']},"
            f"{point['spd']},"
            f"{point['dir']},"
            f"{point['alt']},"
            f"{point['sat']},"
            f"{network_info['csq']},"
            f"{network_info['creg']},"
            f"{network_info['cgatt']}\n"
        )


    # =========================
    # PERMANENT LOG
    # =========================

    def write(self, point, network_info=None):

        filename = self.filename(point)

        line = self.point_line(
            point,
            network_info
        )

        with open(filename, "a") as f:
            f.write(line)


    # =========================
    # MQTT CACHE
    # =========================

    def cache(self, point, network_info=None):

        line = self.point_line(
            point,
            network_info
        )

        with open(PENDING_FILE, "a") as f:
            f.write(line)


    # =========================
    # WRITE + CACHE
    # =========================

    def write_and_cache(self, point, network_info=None):

        line = self.point_line(
            point,
            network_info
        )

        filename = self.filename(point)

        with open(filename, "a") as f:
            f.write(line)

        with open(PENDING_FILE, "a") as f:
            f.write(line)


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

                # preskoc odoslane riadky

                skipped = 0

                while skipped < count:

                    line = src.readline()

                    if not line:
                        break

                    skipped += 1

                # vytvor zvysok

                with open(PENDING_TMP, "w") as dst:

                    while True:

                        line = src.readline()

                        if not line:
                            break

                        dst.write(line)

            try:
                os.remove(PENDING_FILE)
            except OSError:
                pass

            os.rename(
                PENDING_TMP,
                PENDING_FILE
            )

            return True

        except Exception as e:

            print(
                "Pending batch remove error:",
                e
            )

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

        import json

        lines = self.read_pending_batch(batch_size)

        if not lines:
            return 0

        points = []
        valid_lines = 0

        for line in lines:

            fields = line.split(",")

            if len(fields) < 11:

                print(
                    "Invalid pending line:",
                    line
                )

                # Nezaradíme ho do batchu
                # a zároveň ho neskôr nebudeme
                # automaticky odstraňovať.
                continue

            try:

                # -------------------------
                # GPS TIME UTC
                # -------------------------

                gps_time = (
                    "20" +
                    fields[0][4:6] + "-" +
                    fields[0][2:4] + "-" +
                    fields[0][0:2] +
                    "T" +
                    fields[1] +
                    "Z"
                )

                # -------------------------
                # POINT
                # -------------------------

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
                valid_lines += 1

            except Exception as e:

                print(
                    "Pending parse error:",
                    e
                )

                # Pri chybe neposielame batch.
                return 0


        if not points:
            return 0


        # =========================
        # BATCH PAYLOAD
        # =========================

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


        # =========================
        # MQTT SEND
        # =========================

        try:

            result = mqtt_publish(
                topic,
                message
            )

        except Exception as e:

            print(
                "Pending MQTT error:",
                e
            )

            return 0


        # =========================
        # SEND FAILED
        # =========================

        if result is not True:

            print(
                "Pending batch MQTT send failed"
            )

            # Cache zostáva nedotknutá.
            return 0


        # =========================
        # SEND OK
        # =========================

        if valid_lines != len(lines):

            print(
                "WARNING: invalid lines in batch."
            )

            print(
                "Batch sent, but cache was NOT modified."
            )

            return 0


        if not self.pending_pop_batch(
            valid_lines
        ):

            print(
                "WARNING: batch sent but cache "
                "could not be updated"
            )

            return 0


        print(
            "Pending batch sent:",
            valid_lines
        )

        return valid_lines


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

            print(
                "Pending count error:",
                e
            )

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

        return os.listdir("/sd")