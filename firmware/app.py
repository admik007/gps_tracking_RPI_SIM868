from gps import GPS
from logger import Logger

import time, utime
import modem
import mqtt
import json

BOOT_TIME = utime.ticks_ms()
# =========================
# CONFIG
# =========================

NETWORK_CHECK_INTERVAL = 60
NETWORK_INFO_INTERVAL = 60
PUBLISH_INTERVAL = 5

MODEM_RESET_INTERVAL = 300

# Kolko zaznamov poslat naraz z cache
PENDING_BATCH_SIZE = 8


# =========================
# INIT
# =========================

mqtt_ok = False
storage_status = "unknown"

print("System start")

# =========================
# SD LOGGER
# =========================
try:
    logger = Logger()
    if logger.sd_ok:
        storage_status = "ok"
    else:
        storage_status = "failed"
except Exception as e:
    print("SD logger failed:", e)
    logger = None
    storage_status = "failed"  

# =========================
# MODEM
# =========================
print("Modem power on")
modem.power_on_off()
time.sleep(5)

# =========================
# GPS
# =========================
gps = GPS()

# =========================
# MODEM INIT
# =========================
print("Modem init")
if modem.modem_init():
    print("Modem OK")
    # =========================
    # INITIAL NETWORK INFO
    # =========================
    try:
        network_info = modem.get_network_info()
        print(
            "Initial network info:",
            network_info
        )
    except Exception as e:
        print(
            "Network info error:",
            e
        )
        network_info = {
            "csq": 0,
            "creg": 0,
            "cgatt": 0
        }
    # =========================
    # MQTT CONNECT
    # =========================
    if mqtt.mqtt_connect():
        mqtt_ok = True
        print("MQTT connected")
        # =========================
        # ONLINE STATUS
        # =========================
        mqtt.mqtt_publish(
            "gps/" + mqtt.CLIENT_ID + "/status",
            json.dumps({
                "id": mqtt.CLIENT_ID,
                "msg": "online"
            })
        )
    else:
        print("MQTT failed")
else:
    print("Modem failed")
    network_info = {
        "csq": 0,
        "creg": 0,
        "cgatt": 0
    }
# =========================
# TIMERS
# =========================
last_ts = ""
last_network_check = time.time()
last_network_info = time.time()
last_publish = 0
gsm_failed_since = None
# =========================
# PENDING STATE
# =========================
# Po uspesnom batchi posleme aktualny bod.
send_current_after_batch = False
# =========================
# LED BLINK
# =========================
led = machine.Pin("LED", machine.Pin.OUT)
led.toggle()
# =========================
# FUNKCIA NA ZISTENIE STAVU SD
# =========================
def get_storage_status():
    if logger is not None and logger.sd_ok:
        return "ok"

    return "failed"
# =========================
# MAIN LOOP
# =========================
while True:
    led.toggle()
    # =====================================================
    # GPS READ
    # =====================================================
    point = gps.read()
    if point["valid"]:
        if point["ts"] != last_ts:
            last_ts = point["ts"]
            print(point)
            # =================================================
            # CREATE RECORD
            # =================================================
            record = {
                "id": mqtt.CLIENT_ID,
                "date": point["date"],
                "ts": point["ts"],
                "time": gps.gps_datetime(),
                "lat": point["lat"],
                "lon": point["lon"],
                "spd": point["spd"],
                "dir": point["dir"],
                "alt": point["alt"],
                "sat": point["sat"],
                "csq": network_info["csq"],
                "creg": network_info["creg"],
                "cgatt": network_info["cgatt"]
            }
            # =================================================
            # PERMANENT SD LOG
            # =================================================
            if logger is not None and logger.sd_ok:
                try:
                    logger.write(
                        record,
                        network_info
                    )
                except Exception as e:
                    print(
                        "SD write error:",
                        e
                    )
            # =================================================
            # CURRENT GPS PUBLISH
            # =================================================
            if mqtt_ok:
                if (
                    time.time() - last_publish
                    >= PUBLISH_INTERVAL
                ):
                    # -----------------------------------------
                    # CREATE CURRENT PAYLOAD
                    # -----------------------------------------
                    payload = {
                        "id": mqtt.CLIENT_ID,
                        "lat": point["lat"],
                        "lon": point["lon"],
                        "spd": point["spd"],
                        "alt": point["alt"],
                        "sat": point["sat"],
                        "dir": point["dir"],
                        "csq": network_info["csq"],
                        "creg": network_info["creg"],
                        "cgatt": network_info["cgatt"],
                        "time": gps.gps_datetime(),
                        "storage": get_storage_status()
                    }
                    message = json.dumps(payload)
                    # -----------------------------------------
                    # SEND CURRENT
                    # -----------------------------------------
                    try:
                        result = mqtt.mqtt_publish(
                            "gps/" +
                            mqtt.CLIENT_ID +
                            "/location",
                            message
                        )
                        if result is True:
                            last_publish = time.time()
                            print(
                                "Current GPS sent"
                            )
                            # ---------------------------------
                            # AFTER CURRENT POINT:
                            # TRY ONE CACHE BATCH
                            # ---------------------------------
                            if logger is not None and logger.sd_ok:
                                try:
                                    sent = logger.flush_pending(
                                        mqtt_publish=mqtt.mqtt_publish,
                                        topic=(
                                            "gps/" +
                                            mqtt.CLIENT_ID +
                                            "/location"
                                        ),
                                        device_id=mqtt.CLIENT_ID,
                                        batch_size=PENDING_BATCH_SIZE
                                    )
                                    if sent > 0:
                                        print(
                                            "Pending batch sent:",
                                            sent
                                        )
                                except Exception as e:

                                    print(
                                        "Pending batch error:",
                                        e
                                    )
                        else:
                            print(
                                "MQTT lost"
                            )
                            mqtt_ok = False
                            # -----------------------------
                            # CACHE CURRENT POINT
                            # -----------------------------
                            if logger is not None and logger.sd_ok:
                                try:
                                    logger.cache(
                                        record,
                                        network_info
                                    )
                                except Exception as e:
                                    print(
                                        "Pending write error:",
                                        e
                                    )
                    except Exception as e:
                        print(
                            "MQTT publish error:",
                            e
                        )
                        mqtt_ok = False
                        if logger is not None and logger.sd_ok:
                            try:
                                logger.cache(
                                    record,
                                    network_info
                                )
                            except Exception as e:
                                print(
                                    "Pending write error:",
                                    e
                                )
            else:
                # =================================================
                # MQTT OFFLINE
                # =================================================
                if logger is not None and logger.sd_ok:
                    try:
                        logger.write(
                            record,
                            network_info
                        )
                    except Exception as e:
                        print("SD write error:", e)
                        logger.sd_ok = False
                        storage_status = "failed"
    # =====================================================
    # NETWORK INFO
    # =====================================================
    if (
        time.time() - last_network_info
        >= NETWORK_INFO_INTERVAL
    ):
        last_network_info = time.time()
        try:
            network_info = modem.get_network_info()
            print(
                "Network info:",
                network_info
            )
        except Exception as e:
            print(
                "Network info error:",
                e
            )
            network_info = {
                "csq": 0,
                "creg": 0,
                "cgatt": 0
            }
    # =====================================================
    # NETWORK CHECK
    # =====================================================
    if (
        time.time() - last_network_check
        >= NETWORK_CHECK_INTERVAL
    ):
        last_network_check = time.time()
        print(
            "Network check"
        )
        try:
            if modem.check_network():
                print(
                    "Network OK"
                )
                # -----------------------------
                # GSM RECOVERED
                # -----------------------------
                gsm_failed_since = None
                # =================================================
                # MQTT RECONNECT
                # =================================================
                if not mqtt_ok:
                    print(
                        "Trying MQTT reconnect"
                    )
                    if mqtt.mqtt_connect():
                        mqtt_ok = True
                        print(
                            "MQTT restored"
                        )
                        # -----------------------------
                        # ONLINE
                        # -----------------------------
                        mqtt.mqtt_publish(
                            "gps/" +
                            mqtt.CLIENT_ID +
                            "/status",
                            json.dumps({
                                "id": mqtt.CLIENT_ID,
                                "msg": "online"
                            })
                        )
                        # =================================================
                        # SEND ONE PENDING BATCH
                        # =================================================
                        if logger is not None and logger.sd_ok:
                            try:
                                sent = logger.flush_pending(
                                    mqtt_publish=
                                    mqtt.mqtt_publish,
                                    topic=(
                                        "gps/" +
                                        mqtt.CLIENT_ID +
                                        "/location"
                                    ),
                                    device_id=
                                    mqtt.CLIENT_ID,
                                    batch_size=
                                    PENDING_BATCH_SIZE
                                )
                                print(
                                    "Pending batch sent:",
                                    sent
                                )
                            except Exception as e:
                                print(
                                    "Pending send error:",
                                    e
                                )
            else:
                # =================================================
                # NO GSM
                # =================================================
                print(
                    "No GSM"
                )
                mqtt_ok = False
                # -----------------------------
                # START GSM FAILURE TIMER
                # -----------------------------
                if gsm_failed_since is None:
                    gsm_failed_since = time.time()
                    print(
                        "GSM failure started"
                    )
                # =================================================
                # MODEM RESET AFTER 5 MINUTES
                # =================================================
                elif (
                    time.time() -
                    gsm_failed_since
                    >= MODEM_RESET_INTERVAL
                ):
                    print(
                        "GSM unavailable for 5 minutes"
                    )
                    print(
                        "Performing modem reset..."
                    )
                    if modem.modem_reset():
                        print(
                            "Modem reset completed"
                        )
                        time.sleep(5)
                        # =================================================
                        # FULL MODEM INIT
                        # =================================================
                        if modem.modem_init():
                            print(
                                "Modem reinitialized"
                            )
                            # -----------------------------
                            # NETWORK INFO
                            # -----------------------------
                            try:
                                network_info = (
                                    modem.get_network_info()
                                )
                                print(
                                    "Network info:",
                                    network_info
                                )
                            except Exception:
                                network_info = {
                                    "csq": 0,
                                    "creg": 0,
                                    "cgatt": 0
                                }
                            # =================================================
                            # MQTT
                            # =================================================
                            if mqtt.mqtt_connect():
                                mqtt_ok = True
                                print(
                                    "MQTT restored"
                                )
                                mqtt.mqtt_publish(
                                    "gps/" +
                                    mqtt.CLIENT_ID +
                                    "/status",
                                    json.dumps({
                                        "id": mqtt.CLIENT_ID,
                                        "msg": "online"
                                    })
                                )
                                # =================================================
                                # SEND ONE PENDING BATCH
                                # =================================================
                                if logger is not None and logger.sd_ok:
                                    try:
                                        sent = (
                                            logger.flush_pending(

                                                mqtt_publish=
                                                mqtt.mqtt_publish,

                                                topic=(
                                                    "gps/" +
                                                    mqtt.CLIENT_ID +
                                                    "/location"
                                                ),
                                                device_id=
                                                mqtt.CLIENT_ID,

                                                batch_size=
                                                PENDING_BATCH_SIZE
                                            )
                                        )
                                        print(
                                            "Pending batch sent:",
                                            sent
                                        )
                                    except Exception as e:
                                        print(
                                            "Pending send error:",
                                            e
                                        )
                                # -----------------------------
                                # GSM RECOVERY SUCCESSFUL
                                # -----------------------------
                                gsm_failed_since = None
                            else:
                                print(
                                    "MQTT restore failed"
                                )
                        else:
                            print(
                                "Modem reinitialization failed"
                            )
                            # -----------------------------
                            # RESTART 5 MIN TIMER
                            # -----------------------------
                            gsm_failed_since = time.time()
        except Exception as e:
            print(
                "Network check error:",
                e
            )
            mqtt_ok = False
            network_info = {
                "csq": 0,
                "creg": 0,
                "cgatt": 0
            }
    # =====================================================
    # SMALL DELAY
    # =====================================================
    time.sleep(0.1)
