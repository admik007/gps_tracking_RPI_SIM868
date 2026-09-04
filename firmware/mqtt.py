import time
import modem
import machine
import ubinascii
import ujson
import config


CLIENT_ID = ubinascii.hexlify(
    machine.unique_id()
).decode()


MQTT_USER = config.MQTT_USER
MQTT_PASS = config.MQTT_PASS


# =========================
# MQTT REMAINING LENGTH
# =========================

def mqtt_length(length):

    result = bytearray()

    while True:

        digit = length % 128
        length //= 128

        if length > 0:
            digit |= 0x80

        result.append(digit)

        if length == 0:
            break

    return result


# =========================
# MQTT STRING
# =========================

def mqtt_string(text):

    data = text.encode()

    return bytes([
        len(data) >> 8,
        len(data) & 0xff
    ]) + data


# =========================
# MQTT CONNECT
# =========================

def mqtt_connect():

    variable_header = (
        b'\x00\x04' +
        b'MQTT' +
        b'\x04' +
        b'\xC2' +
        b'\x00\x3C'
    )

    payload = (
        mqtt_string(CLIENT_ID) +
        mqtt_string(MQTT_USER) +
        mqtt_string(MQTT_PASS)
    )

    packet = (
        b'\x10' +
        mqtt_length(
            len(variable_header) +
            len(payload)
        ) +
        variable_header +
        payload
    )

    print("MQTT CONNECT")
    print(packet)

    result = modem.tcp_send(packet)

    if result:

        print("MQTT connected")
        return True

    print("MQTT connect failed")
    return False


# =========================
# MQTT PUBLISH
# =========================

def mqtt_publish(topic, message):

    topic_data = mqtt_string(topic)
    payload = message.encode()

    packet = (
        b'\x30' +
        mqtt_length(
            len(topic_data) +
            len(payload)
        ) +
        topic_data +
        payload
    )

    print("MQTT PUBLISH")
    print("topic len:", len(topic_data))
    print("payload len:", len(payload))
    print(
        "remaining:",
        len(topic_data) + len(payload)
    )
    print(packet)

    return modem.tcp_send(packet)


# =========================
# CACHE LINE -> JSON
# =========================

def cache_line_to_json(line):

    fields = line.strip().split(",")

    if len(fields) < 11:

        print("Invalid cache line:")
        print(line)

        return None


    date = fields[0]
    ts = fields[1]

    lat = float(fields[2])
    lon = float(fields[3])
    spd = float(fields[4])
    direction = float(fields[5])
    alt = float(fields[6])
    sat = int(fields[7])

    csq = int(fields[8])
    creg = int(fields[9])
    cgatt = int(fields[10])


    # =========================
    # GPS UTC TIME
    # =========================

    day = date[0:2]
    month = date[2:4]
    year = "20" + date[4:6]

    hour = ts[0:2]
    minute = ts[2:4]
    second = ts[4:]


    gps_time = (
        year + "-" +
        month + "-" +
        day + "T" +
        hour + ":" +
        minute + ":" +
        second + "Z"
    )


    # =========================
    # JSON
    # =========================

    data = {
        "id": CLIENT_ID,
        "time": gps_time,
        "lat": lat,
        "lon": lon,
        "spd": spd,
        "dir": direction,
        "alt": alt,
        "sat": sat,
        "csq": csq,
        "creg": creg,
        "cgatt": cgatt
    }


    return ujson.dumps(data)


# =========================
# PUBLISH CACHE
# =========================

def mqtt_publish_cache_line(line):

    payload = cache_line_to_json(line)

    if payload is None:
        return False


    topic = (
        "gps/" +
        CLIENT_ID +
        "/location"
    )


    return mqtt_publish(
        topic,
        payload
    )
