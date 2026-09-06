from machine import SPI, Pin
import os
import sdcard
import time


PENDING_FILE = "/sd/pending.txt"
PENDING_POS_FILE = "/sd/pending.pos"
PENDING_POS_TMP = "/sd/pending.pos.tmp"

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
                    try:
                        self.cs.value(1)
                    except:
                        pass

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

        return (
            "/sd/" +
            year + "." +
            month + "." +
            day + "-" +
            hour + ".txt"
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
            str(point["date"]) + "," +
            str(point["ts"]) + "," +
            str(point["lat"]) + "," +
            str(point["lon"]) + "," +
            str(point["spd"]) + "," +
            str(point["dir"]) + "," +
            str(point["alt"]) + "," +
            str(point["sat"]) + "," +
            str(network_info["csq"]) + "," +
            str(network_info["creg"]) + "," +
            str(network_info["cgatt"]) + "\n"
        )

    # =========================
    # PERMANENT LOG
    # =========================
    def write(self, point, network_info=None):
        if not self.sd_ok:
            return False

        try:
            filename = self.filename(point)

            line = self.point_line(
                point,
                network_info
            )

            with open(filename, "a") as f:
                f.write(line)

            return True

        except Exception as e:
            print(
                "SD permanent write failed:",
                e
            )

            self._disable_sd()
            return False

    # =========================
    # MQTT CACHE
    # =========================
    def cache(self, point, network_info=None):
        if not self.sd_ok:
            return False

        try:
            # Ak zostal kompletne spracovany
            # pending subor po predoslom restarte,
            # vycistime ho pred pridanim noveho bodu.
            self._cleanup_consumed_pending()

            line = self.point_line(
                point,
                network_info
            )

            with open(PENDING_FILE, "a") as f:
                f.write(line)

            return True

        except Exception as e:
            print(
                "SD cache write failed:",
                e
            )

            self._disable_sd()
            return False

    # =========================
    # WRITE + CACHE
    # =========================
    def write_and_cache(self, point, network_info=None):
        if not self.sd_ok:
            return False

        try:
            line = self.point_line(
                point,
                network_info
            )

            filename = self.filename(point)

            with open(filename, "a") as f:
                f.write(line)

            self._cleanup_consumed_pending()

            with open(PENDING_FILE, "a") as f:
                f.write(line)

            return True

        except Exception as e:
            print(
                "SD write and cache failed:",
                e
            )

            self._disable_sd()
            return False

    # =========================
    # DISABLE SD
    # =========================
    def _disable_sd(self):
        self.sd_ok = False

        try:
            os.umount("/sd")
        except:
            pass

    # =========================
    # FILE SIZE
    # =========================
    def _pending_file_size(self):
        try:
            stat = os.stat(PENDING_FILE)
            return stat[6]
        except:
            return 0

    # =========================
    # READ OFFSET FILE
    # =========================
    def _read_offset_file(self, filename):
        try:
            with open(filename, "r") as f:
                value = f.read().strip()

            if not value:
                return None

            offset = int(value)

            if offset < 0:
                return None

            return offset

        except:
            return None

    # =========================
    # LOAD PENDING OFFSET
    # =========================
    def _load_pending_offset(self):
        if not self.pending_file_exists():
            return 0

        size = self._pending_file_size()

        # TMP kontrolujeme ako prve.
        # Ak zariadenie spadlo pocas aktualizacie
        # pending.pos, TMP moze obsahovat novsi offset.
        offset = self._read_offset_file(
            PENDING_POS_TMP
        )

        if offset is None:
            offset = self._read_offset_file(
                PENDING_POS_FILE
            )

        if offset is None:
            return 0

        # Offset mimo suboru nie je platny.
        if offset > size:
            print(
                "Invalid pending offset:",
                offset,
                "file size:",
                size
            )

            return 0

        return offset

    # =========================
    # SAVE PENDING OFFSET
    # =========================
    def _save_pending_offset(self, offset):
        try:
            # Najprv zapiseme novy offset
            # do docasneho suboru.
            with open(PENDING_POS_TMP, "w") as f:
                f.write(str(offset))

            # Potom odstranime stary offset.
            try:
                os.remove(PENDING_POS_FILE)
            except OSError:
                pass

            # TMP sa stane aktualnym offsetom.
            os.rename(
                PENDING_POS_TMP,
                PENDING_POS_FILE
            )

            return True

        except Exception as e:
            print(
                "Pending offset write error:",
                e
            )

            return False

    # =========================
    # REMOVE OFFSET FILES
    # =========================
    def _clear_pending_offset(self):
        try:
            os.remove(PENDING_POS_FILE)
        except OSError:
            pass

        try:
            os.remove(PENDING_POS_TMP)
        except OSError:
            pass

    # =========================
    # PENDING FILE EXISTS
    # =========================
    def pending_file_exists(self):
        try:
            os.stat(PENDING_FILE)
            return True
        except OSError:
            return False

    # =========================
    # PENDING EXISTS
    # =========================
    def pending_exists(self):
        if not self.pending_file_exists():
            return False

        size = self._pending_file_size()

        if size <= 0:
            return False

        offset = self._load_pending_offset()

        return offset < size

    # =========================
    # CLEANUP CONSUMED FILE
    # =========================
    def _cleanup_consumed_pending(self):
        if not self.pending_file_exists():
            self._clear_pending_offset()
            return

        size = self._pending_file_size()

        if size <= 0:
            self.clear_pending()
            return

        offset = self._load_pending_offset()

        if offset >= size:
            print(
                "Pending file fully processed, clearing"
            )

            self.clear_pending()

    # =========================
    # READ BATCH + END OFFSET
    # =========================
    def _read_pending_batch_with_offset(
        self,
        count=BATCH_SIZE
    ):
        if count <= 0:
            return [], 0

        if not self.pending_file_exists():
            return [], 0

        start_offset = self._load_pending_offset()
        lines = []
        end_offset = start_offset

        try:
            with open(PENDING_FILE, "rb") as f:
                f.seek(start_offset)

                read_count = 0

                while read_count < count:
                    raw_line = f.readline()

                    if not raw_line:
                        break

                    # Riadok bol precitany.
                    # Offset sa musi posunut aj ked
                    # je riadok prazdny alebo chybny.
                    end_offset = f.tell()

                    try:
                        line = raw_line.decode().strip()
                    except:
                        line = ""

                    if line:
                        lines.append(line)
                        read_count += 1

            return lines, end_offset

        except Exception as e:
            print(
                "Pending batch read error:",
                e
            )

            return [], start_offset

    # =========================
    # READ BATCH
    # =========================
    def read_pending_batch(
        self,
        count=BATCH_SIZE
    ):
        lines, end_offset = (
            self._read_pending_batch_with_offset(
                count
            )
        )

        return lines

    # =========================
    # ADVANCE PENDING
    # =========================
    def pending_pop_batch(self, count):
        if count <= 0:
            return False

        if not self.pending_exists():
            return False

        lines, end_offset = (
            self._read_pending_batch_with_offset(
                count
            )
        )

        if not lines:
            return False

        if not self._save_pending_offset(
            end_offset
        ):
            return False

        self._cleanup_consumed_pending()

        return True

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

        # ---------------------------------
        # READ NEXT BATCH FROM OFFSET
        # ---------------------------------
        lines, end_offset = (
            self._read_pending_batch_with_offset(
                batch_size
            )
        )

        if not lines:
            self._cleanup_consumed_pending()
            return 0

        points = []

        # ---------------------------------
        # PARSE BATCH
        # ---------------------------------
        for line in lines:
            fields = line.split(",")

            if len(fields) < 11:
                print(
                    "Invalid pending line, skipping:",
                    line
                )
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

            except Exception as e:
                print(
                    "Pending parse error, skipping:",
                    e
                )

        # ---------------------------------
        # ONLY INVALID LINES
        # ---------------------------------
        if not points:
            print(
                "Pending batch contains no valid points"
            )

            # Posunieme offset, aby poskodene
            # riadky nezablokovali frontu.
            if not self._save_pending_offset(
                end_offset
            ):
                print(
                    "Could not advance pending offset"
                )

                return 0

            self._cleanup_consumed_pending()

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

            print(
                "Pending MQTT result:",
                repr(result)
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
        if not result:
            print(
                "Pending batch MQTT send failed"
            )

            # Offset sa neposunie.
            # Batch zostane na dalsi pokus.
            return 0

        # =========================
        # SEND OK
        # =========================

        # MQTT odoslanie bolo uspesne.
        # Neprepisujeme pending.txt.
        # Ulozime iba novy byte offset.
        if not self._save_pending_offset(
            end_offset
        ):
            print(
                "WARNING: batch sent but "
                "pending offset could not be updated"
            )

            # Pri dalsom pokuse sa moze batch
            # odoslat znova, pretoze offset
            # nebol bezpecne ulozeny.
            return 0

        print(
            "Pending batch sent:",
            len(points)
        )

        print(
            "Pending offset:",
            end_offset
        )

        # Ak sme dosli na koniec suboru,
        # odstranime pending.txt aj pending.pos.
        self._cleanup_consumed_pending()

        return len(points)

    # =========================
    # PENDING COUNT
    # =========================
    def pending_count(self):
        if not self.pending_exists():
            return 0

        count = 0
        offset = self._load_pending_offset()

        try:
            with open(PENDING_FILE, "rb") as f:
                f.seek(offset)

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
    # PENDING OFFSET
    # =========================
    def pending_offset(self):
        return self._load_pending_offset()

    # =========================
    # CLEAR PENDING
    # =========================
    def clear_pending(self):
        try:
            os.remove(PENDING_FILE)
        except OSError:
            pass

        self._clear_pending_offset()

    # =========================
    # LIST FILES
    # =========================
    def list_files(self):
        if not self.sd_ok:
            return []

        try:
            return os.listdir("/sd")

        except Exception as e:
            print(
                "SD list files failed:",
                e
            )

            return []
