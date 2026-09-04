def create():

    return {
        "date": "",

        "ts": "",

        "lat": 0.0,
        "lon": 0.0,

        "spd": 0,
        "dir": 0,

        "alt": 0.0,
        "sat": 0,

        "temp": 0.0,
        "load": 0,
        "rssi": 0,

        "valid": False
    }

def datetime(point):

    d = point["date"]
    t = point["ts"]

    if not d or not t:
        return ""

    day = d[0:2]
    month = d[2:4]
    year = "20" + d[4:6]

    return (
        f"{year}-{month}-{day}T"
        f"{t[0:2]}:{t[2:4]}:{t[4:]}Z"
    )
