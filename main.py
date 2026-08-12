import network, time, urequests, machine, os
import config

SSID = config.SSID
PASS = config.PASS
HOST = config.HOST

DEVICE_ID = "".join("{:02x}".format(b) for b in machine.unique_id())

BASE_URL = f"http://"+HOST+"/firmware/{DEVICE_ID}/"
VERSION_URL = BASE_URL + "version.txt"
MANIFEST_URL = BASE_URL + "manifest.txt"
LOCAL_VERSION_FILE = "version.txt"

print("Start local script ...")

led = machine.Pin("LED", machine.Pin.OUT)
def blink():
 led.value(1)
 time.sleep(.1)
 led.value(0)
 time.sleep(.9)

# ----------------- Connect Wi-Fi -----------------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def connect_wifi():
    wlan.disconnect()
    time.sleep(0.3)
    wlan.connect(SSID, security=0)

    timeout = 15000  # 15 seconds
    start = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout:
            print("Wi-Fi timeout")
            return False
        time.sleep(0.2)

    print("Wi-Fi connected:", wlan.ifconfig())
    return True

# Retry 3×
for attempt in range(3):
    if connect_wifi():
        break
    print("WiFi retry", attempt+1)
    blink()
    time.sleep(1)
else:
    print("Wi-Fi failed, running local script")
    if "app.py" in os.listdir():
        exec(open("app.py").read())
    else:
        machine.reset()

# ----------------- Check latest version -----------------
try:
    r = urequests.get(VERSION_URL)
    latest_version = r.text.strip()
    r.close()
except:
    latest_version = None

# Read local version
local_version = None
if LOCAL_VERSION_FILE in os.listdir():
    with open(LOCAL_VERSION_FILE) as f:
        local_version = f.read().strip()

# ----------------- Download files if new -----------------
if latest_version and latest_version != local_version:
    print("Downloading new firmware...")

    files = []

    # Download manifest
    try:
        r = urequests.get(MANIFEST_URL)
        files = [line.strip() for line in r.text.splitlines() if line.strip()]
        r.close()
        blink()
    except Exception as e:
        print("Failed to download manifest:", e)
        files = []

    if files:
        # Download all files
        for file in files:
            print(f"Downloading {file}...")
            try:
                r = urequests.get(BASE_URL + file)
                with open(file, "w") as f:
                    f.write(r.text)
                r.close()
            except Exception as e:
                print(f"Failed to download {file}: {e}")

        # Auto-delete unused files
        protected = ["boot.py", "main.py", "version.txt"]
        local_files = os.listdir()

        for lf in local_files:
            if lf not in files and lf not in protected:
                try:
                    print(f"Deleting old file: {lf}")
                    os.remove(lf)
                except Exception as e:
                    print(f"Failed to delete {lf}: {e}")

        # Save new version
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(latest_version)

        print("Update complete")

    else:
        print("Manifest missing or empty. Skipping update.")

# ----------------- Run main app -----------------
try:
    print("Start external script ...")
    print(BASE_URL)
    exec(open("app.py").read())
except:
    machine.reset()

