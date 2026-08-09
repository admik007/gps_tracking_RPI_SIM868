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
            # 131928.000
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
    # DATA
    # -------------------------

    lat = float(data.get("lat", 0))
    lon = float(data.get("lon", 0))
    alt = float(data.get("alt", 0))
    spd = float(data.get("spd", 0))
    sat = int(data.get("sat", 0))
    direction = float(data.get("dir", 0))

    provider = int(data.get("creg", 0))
    signal = int(data.get("csq", 0))
    cputemp = data.get("cputemp", "")

    # GPS TIME - UTC
    gps_time = normalize_gps_time(data.get("time", ""))

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
        loadrpi
    )
    VALUES
    (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
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
        signal
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
