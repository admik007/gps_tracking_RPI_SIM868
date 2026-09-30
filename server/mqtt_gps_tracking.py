import os
import json
import mysql.connector
import paho.mqtt.client as mqtt
from datetime import datetime

# =========================
# CONFIG
# =========================

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "gps/+/location")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ["MYSQL_USER"]
MYSQL_PASS = os.environ["MYSQL_PASS"]
MYSQL_DB = os.environ["MYSQL_DB"]

# =========================
# MYSQL
# =========================

db = mysql.connector.connect(
    host=MYSQL_HOST,
    database=MYSQL_DB,
    user=MYSQL_USER,
    password=MYSQL_PASS
)

cursor = db.cursor()

# =========================
# HELPERS
# =========================

def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_bool(value, default=True):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        return value.strip().lower() in (
            "1",
            "true",
            "yes",
            "on"
        )

    return default


# =========================
# MYSQL INSERT
# =========================

def normalize_gps_time(value):
    if not value:
        return None

    try:
        # -------------------------
        # BATCH / OLD PENDING FORMAT
        # 2026-08-08T131928.000Z
        # -------------------------
        if "T" in value:
            date_part, time_part = value.split("T", 1)
            time_part = time_part.rstrip("Z")

            if len(time_part) >= 10 and ":" not in time_part:
                time_part = (
                    time_part[0:2] + ":" +
                    time_part[2:4] + ":" +
                    time_part[4:]
                )

            value = date_part + "T" + time_part + "Z"

        return value

    except Exception as e:
        print("GPS time conversion error:", e)
        return value


def insert_record(data, device_id):

    # -------------------------
    # GPS DATA
    # -------------------------

    lat = safe_float(data.get("lat"))
    lon = safe_float(data.get("lon"))
    alt = safe_float(data.get("alt"))
    spd = safe_float(data.get("spd"))
    sat = safe_int(data.get("sat"))
    direction = safe_float(data.get("dir"))

    # -------------------------
    # NETWORK DATA
    # -------------------------

    csq = safe_int(data.get("csq"))
    creg = safe_int(data.get("creg"))
    cgatt = safe_int(data.get("cgatt"))

    mcc = str(data.get("mcc", "") or "")
    mnc = str(data.get("mnc", "") or "")

    bsic = safe_int(data.get("bsic"))
    cellid = safe_int(data.get("cellid"))
    lac = safe_int(data.get("lac"))

    # Old firmware/pending records do not contain gps_valid.
    # Those records were created only from valid GPS fixes.
    gps_valid = 1 if safe_bool(
        data.get("gps_valid"),
        True
    ) else 0

    # -------------------------
    # LEGACY FIELDS
    # -------------------------

    provider = 0
    loadrpi = 0
    cputemp = data.get("cputemp", "")

    # GPS TIME - UTC
    gps_time = normalize_gps_time(
        data.get("time", "")
    )

    # -------------------------
    # SERVER TIME
    # -------------------------

    now = datetime.now()

    # -------------------------
    # MYSQL
    # -------------------------

    sql = """
    INSERT INTO gps_tracking
    (
        lat,
        lon,
        alt,
        acc,
        spd,
        sat,
        time,
        bat,
        ip,
        year,
        month,
        day,
        hour,
        minute,
        second,
        device,
        provider,
        direction,
        devicerpi,
        temprpi,
        loadrpi,
        gps_valid,
        creg,
        cgatt,
        csq,
        mcc,
        mnc,
        bsic,
        cellid,
        lac
    )
    VALUES
    (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s
    )
    """

    values = (
        lat,
        lon,
        alt,
        0,
        spd,
        sat,
        gps_time,
        100.0,
        "",
        now.year,
        now.strftime("%m"),
        now.strftime("%d"),
        now.strftime("%H"),
        now.strftime("%M"),
        now.strftime("%S"),
        "",
        provider,
        direction,
        device_id,
        cputemp,
        loadrpi,
        gps_valid,
        creg,
        cgatt,
        csq,
        mcc,
        mnc,
        bsic,
        cellid,
        lac
    )

    cursor.execute(sql, values)


# =========================
# MQTT
# =========================

def on_connect(client, userdata, flags, rc):

    print("MQTT connected:", rc)

    client.subscribe(MQTT_TOPIC)

    print("Subscribed:", MQTT_TOPIC)


def on_message(client, userdata, msg):

    print()
    print("MQTT:", msg.topic)
    print("DATA:", msg.payload)

    try:

        data = json.loads(
            msg.payload.decode()
        )

        # -------------------------
        # DEVICE ID Z TOPICU
        # -------------------------

        parts = msg.topic.split("/")

        device_id = parts[1]

        # =====================================================
        # BATCH
        # =====================================================

        if "points" in data:

            points = data["points"]

            print(
                "MQTT BATCH:",
                len(points),
                "points"
            )

            inserted = 0

            for record in points:

                try:

                    insert_record(
                        record,
                        device_id
                    )

                    inserted += 1

                except Exception as e:

                    print(
                        "BATCH RECORD ERROR:",
                        e
                    )

            db.commit()

            print(
                "MYSQL: batch inserted:",
                inserted,
                "/",
                len(points)
            )

        # =====================================================
        # SINGLE RECORD
        # =====================================================

        else:

            print("MQTT SINGLE RECORD")

            insert_record(
                data,
                device_id
            )

            db.commit()

            print("MYSQL: inserted")

    except Exception as e:

        print("ERROR:", e)


# =========================
# START
# =========================

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

print("Connecting MQTT...")

client.connect(
    MQTT_HOST,
    MQTT_PORT,
    60
)

client.loop_forever()
