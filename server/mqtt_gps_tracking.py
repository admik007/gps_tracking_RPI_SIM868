import json
import mysql.connector
import paho.mqtt.client as mqtt
from datetime import datetime

# =========================
# CONFIG
# =========================

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "gps/+/location"

MYSQL_HOST = "localhost"
MYSQL_USER = "xxxxxxxx"
MYSQL_PASS = "xxxxxxxx"
MYSQL_DB = "xxxxxxxx"

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
# GPS TIME
# =========================

def normalize_gps_time(value):

    if not value:
        return None

    try:

        # ---------------------------------
        # OLD PENDING FORMAT
        #
        # 2026-08-08T131928.000Z
        # ->
        # 2026-08-08T13:19:28.000Z
        # ---------------------------------

        if "T" in value:

            date_part, time_part = value.split("T", 1)

            time_part = time_part.rstrip("Z")

            if (
                len(time_part) >= 6
                and ":" not in time_part
            ):

                time_part = (
                    time_part[0:2] + ":" +
                    time_part[2:4] + ":" +
                    time_part[4:]
                )

            value = (
                date_part +
                "T" +
                time_part +
                "Z"
            )

        return value

    except Exception as e:

        print(
            "GPS time conversion error:",
            e
        )

        return value


# =========================
# SAFE CONVERSIONS
# =========================

def safe_int(value, default=0):

    try:
        return int(value)
    except:
        return default


def safe_float(value, default=0.0):

    try:
        return float(value)
    except:
        return default


def safe_bool(value, default=True):

    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, int):
        return value != 0

    value = str(value).lower()

    if value in (
        "true",
        "1",
        "yes"
    ):
        return True

    if value in (
        "false",
        "0",
        "no"
    ):
        return False

    return default


# =========================
# MYSQL INSERT
# =========================

def insert_record(data, device_id):

    # =====================================================
    # GPS DATA
    # =====================================================

    lat = safe_float(
        data.get("lat", 0)
    )

    lon = safe_float(
        data.get("lon", 0)
    )

    alt = safe_float(
        data.get("alt", 0)
    )

    spd = safe_float(
        data.get("spd", 0)
    )

    sat = safe_int(
        data.get("sat", 0)
    )

    direction = safe_float(
        data.get("dir", 0)
    )

    gps_valid = safe_bool(
        data.get(
            "gps_valid",
            True
        )
    )


    # =====================================================
    # NETWORK DATA
    # =====================================================

    csq = safe_int(
        data.get("csq", 0)
    )

    creg = safe_int(
        data.get("creg", 0)
    )

    cgatt = safe_int(
        data.get("cgatt", 0)
    )

    # MCC / MNC intentionally strings
    mcc = str(
        data.get("mcc", "")
    )

    mnc = str(
        data.get("mnc", "")
    )

    bsic = safe_int(
        data.get("bsic", 0)
    )

    cellid = safe_int(
        data.get("cellid", 0)
    )

    lac = safe_int(
        data.get("lac", 0)
    )


    # =====================================================
    # LEGACY DATA
    # =====================================================

    cputemp = data.get(
        "cputemp",
        ""
    )

    # Existing fields kept for compatibility
    provider = creg
    signal = csq


    # =====================================================
    # GPS TIME
    # =====================================================

    gps_time = normalize_gps_time(
        data.get("time", "")
    )


    # =====================================================
    # SERVER TIME
    # =====================================================

    now = datetime.now()


    # =====================================================
    # MYSQL
    # =====================================================

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

        %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    )
    """

    values = (

        # GPS
        lat,
        lon,
        alt,
        0,
        spd,
        sat,
        gps_time,

        # legacy
        100.0,
        "",

        # server date/time
        now.year,
        now.strftime("%m"),
        now.strftime("%d"),
        now.strftime("%H"),
        now.strftime("%M"),
        now.strftime("%S"),

        "",

        # legacy provider
        provider,

        direction,

        device_id,
        cputemp,
        signal,

        # new fields
        1 if gps_valid else 0,
        creg,
        cgatt,
        csq,
        mcc,
        mnc,
        bsic,
        cellid,
        lac
    )

    cursor.execute(
        sql,
        values
    )


# =========================
# MQTT
# =========================

def on_connect(
    client,
    userdata,
    flags,
    rc
):

    print(
        "MQTT connected:",
        rc
    )

    client.subscribe(
        MQTT_TOPIC
    )

    print(
        "Subscribed:",
        MQTT_TOPIC
    )


# =========================
# MQTT MESSAGE
# =========================

def on_message(
    client,
    userdata,
    msg
):

    print()

    print(
        "MQTT:",
        msg.topic
    )

    print(
        "DATA:",
        msg.payload
    )

    try:

        data = json.loads(
            msg.payload.decode()
        )

        # =================================================
        # DEVICE ID FROM TOPIC
        # =================================================

        parts = msg.topic.split("/")

        if len(parts) < 3:

            print(
                "Invalid MQTT topic:",
                msg.topic
            )

            return

        device_id = parts[1]


        # =================================================
        # BATCH
        # =================================================

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


        # =================================================
        # SINGLE RECORD
        # =================================================

        else:

            print(
                "MQTT SINGLE RECORD"
            )

            insert_record(
                data,
                device_id
            )

            db.commit()

            print(
                "MYSQL: inserted"
            )


    except Exception as e:

        print(
            "ERROR:",
            e
        )

        try:
            db.rollback()
        except:
            pass


# =========================
# START
# =========================

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

print(
    "Connecting MQTT..."
)

client.connect(
    MQTT_HOST,
    MQTT_PORT,
    60
)

client.loop_forever()

