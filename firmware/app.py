from gps import GPS
from logger import Logger

import time, utime
import machine
import modem
import mqtt
import json
import gc

BOOT_TIME = utime.ticks_ms()
# =========================
# CONFIG
# =========================

NETWORK_CHECK_INTERVAL = 60
NETWORK_INFO_INTERVAL = 60
PUBLISH_INTERVAL = 5

MODEM_RESET_INTERVAL = 300
MQTT_WATCHDOG_INTERVAL = 600
GC_INTERVAL = 60

# Kolko zaznamov poslat naraz z cache
PENDING_BATCH_SIZE = 5


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
last_mqtt_success = time.time()
last_gc = time.time()
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
    record = None

    # =====================================================
    # NEW VALID GPS POINT
    # =====================================================
    if point["valid"] and point["ts"] != last_ts:
        last_ts = point["ts"]
        print(point)

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
            "csq": network_info.get("csq", 0),
            "creg": network_info.get("creg", 0),
            "cgatt": network_info.get("cgatt", 0),
            "mcc": network_info.get("mcc", ""),
            "mnc": network_info.get("mnc", ""),
            "bsic": network_info.get("bsic", 0),
            "cellid": network_info.get("cellid", 0),
            "lac": network_info.get("lac", 0),
            "gps_valid": True
        }

        # Permanent SD log contains only real GPS fixes.
        if logger is not None and logger.sd_ok:
            try:
                logger.write(record, network_info)
            except Exception as e:
                print("SD write error:", e)

        # If MQTT is already known to be offline, cache every real GPS point.
        if not mqtt_ok and logger is not None and logger.sd_ok:
            try:
                logger.cache(record, network_info)
                print("MQTT offline - point cached")
            except Exception as e:
                print("Pending write error:", e)
                logger.sd_ok = False
                storage_status = "failed"

    # =====================================================
    # CURRENT MQTT PUBLISH
    # =====================================================
    # Publish also when GPS has no fix. In that case lat/lon (and movement
    # values) are the last known values and gps_valid=False. No such
    # heartbeat is written to the permanent log or pending queue.
    if mqtt_ok and (time.time() - last_publish >= PUBLISH_INTERVAL):
        payload = {
            "id": mqtt.CLIENT_ID,
            "lat": point["lat"],
            "lon": point["lon"],
            "spd": point["spd"],
            "alt": point["alt"],
            "sat": point["sat"],
            "dir": point["dir"],
            "csq": network_info.get("csq", 0),
            "creg": network_info.get("creg", 0),
            "cgatt": network_info.get("cgatt", 0),
            "mcc": network_info.get("mcc", ""),
            "mnc": network_info.get("mnc", ""),
            "bsic": network_info.get("bsic", 0),
            "cellid": network_info.get("cellid", 0),
            "lac": network_info.get("lac", 0),
            "gps_valid": bool(point["valid"]),
            "time": gps.gps_datetime(),
            "storage": get_storage_status()
        }

        message = json.dumps(payload)

        try:
            result = mqtt.mqtt_publish(
                "gps/" + mqtt.CLIENT_ID + "/location",
                message
            )

            if result:
                last_publish = time.time()
                last_mqtt_success = time.time()

                if point["valid"]:
                    print("Current GPS sent")
                else:
                    print("GPS unavailable - heartbeat sent")

                # After each successful current/heartbeat message, try one
                # pending batch. Five points stay below the SIM868 CIPSEND
                # packet-size limit with the expanded JSON payload.
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
                            print("Pending batch sent:", sent)

                    except Exception as e:
                        print("Pending batch error:", e)

            else:
                print("MQTT lost")
                mqtt_ok = False

                # Cache only a newly-created real GPS point. Heartbeats with
                # gps_valid=False must never enter pending.txt.
                if record is not None and logger is not None and logger.sd_ok:
                    try:
                        logger.cache(record, network_info)
                    except Exception as e:
                        print("Pending write error:", e)

        except Exception as e:
            print("MQTT publish error:", e)
            mqtt_ok = False

            if record is not None and logger is not None and logger.sd_ok:
                try:
                    logger.cache(record, network_info)
                except Exception as cache_error:
                    print("Pending write error:", cache_error)

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
                # =================================================
                # TCP + MQTT RECONNECT
                # =================================================

                if not mqtt_ok:

                    print(
                        "Trying TCP/MQTT reconnect"
                    )

                    # ---------------------------------------------
                    # FIRST RESTORE TCP
                    # ---------------------------------------------

                    if modem.tcp_reconnect():

                        print(
                            "TCP ready, trying MQTT"
                        )

                        # -----------------------------------------
                        # THEN RESTORE MQTT
                        # -----------------------------------------

                        if mqtt.mqtt_connect():

                            mqtt_ok = True

                            print(
                                "MQTT restored"
                            )

                            # -------------------------------------
                            # ONLINE STATUS
                            # -------------------------------------

                            mqtt.mqtt_publish(
                                "gps/" +
                                mqtt.CLIENT_ID +
                                "/status",
                                json.dumps({
                                    "id": mqtt.CLIENT_ID,
                                    "msg": "online"
                                })
                            )

                            # =====================================
                            # SEND ONE PENDING BATCH
                            # =====================================
                            if (
                                logger is not None
                                and logger.sd_ok
                            ):
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
                        else:
                            print(
                                "MQTT reconnect failed"
                            )
                    else:
                        print(
                            "TCP reconnect failed"
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
    # PERIODIC GARBAGE COLLECTION
    # =====================================================
    if time.time() - last_gc >= GC_INTERVAL:
        gc.collect()
        last_gc = time.time()

        print(
            "GC:",
            "free =", gc.mem_free(),
            "allocated =", gc.mem_alloc()
        )

    # =====================================================
    # MQTT LIVENESS WATCHDOG
    # =====================================================
    # If GSM registration is healthy but no MQTT publish has
    # succeeded for 10 minutes, restart the whole Pico. This
    # recovers from stuck TCP/MQTT states that modem-only
    # recovery may not clear.
    if (
        network_info.get("creg", 0) in (1, 5)
        and time.time() - last_mqtt_success >= MQTT_WATCHDOG_INTERVAL
    ):
        print("MQTT watchdog timeout - resetting Pico")
        time.sleep(1)
        machine.reset()

    # =====================================================
    # SMALL DELAY
    # =====================================================
    time.sleep(0.1)
