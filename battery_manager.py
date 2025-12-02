import os
import time
import psutil
import subprocess
import tinytuya
from dotenv import load_dotenv
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
ALLOWED_SSIDS = ["frans-extender", "frans-extender_5G", "Frans", "Frans-IOT"]
BATTERY_MAX = 100
BATTERY_MIN = 20
CHECK_INTERVAL = 60  # Check every 60 seconds

# Tuya Config
API_KEY = os.getenv("TUYA_API_KEY")
API_SECRET = os.getenv("TUYA_API_SECRET")
API_REGION = os.getenv("TUYA_API_REGION", "us")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
USE_LOCAL = os.getenv("USE_LOCAL", "false").lower() == "true"
LOCAL_KEY = os.getenv("TUYA_LOCAL_KEY")
DEVICE_IP = os.getenv("TUYA_DEVICE_IP")

# InfluxDB Config
INFLUX_URL = os.getenv("INFLUXDB_URL")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET")

# Switch 2 Code (usually "switch_2" or "2" for local)
SWITCH_CODE = "switch_2" 
SWITCH_INDEX = 2

def get_influx_client():
    if INFLUX_URL and INFLUX_TOKEN:
        return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    return None

def write_to_influx(measurement, fields, tags=None):
    try:
        client = get_influx_client()
        if not client: return
        
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = Point(measurement)
        
        for k, v in fields.items():
            point = point.field(k, v)
            
        if tags:
            for k, v in tags.items():
                point = point.tag(k, v)
                
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as e:
        print(f"InfluxDB Write Error: {e}")

def get_current_ssid():
    """Returns the current WiFi SSID using iwgetid or nmcli."""
    try:
        # Try iwgetid first (part of wireless-tools)
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        
        # Fallback to nmcli
        result = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"], 
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("yes:"):
                    return line.split(":")[1]
    except Exception as e:
        print(f"Error getting SSID: {e}")
    return None

def send_notification(title, message, urgency="normal"):
    """Sends a GNOME notification."""
    try:
        # Use 'tuya-app' to match the filename 'tuya-app.desktop'
        subprocess.run(["notify-send", "-a", "tuya-app", "-u", urgency, title, message])
        print(f"[{datetime.now()}] Notification sent: {title} - {message}")
    except Exception as e:
        print(f"[{datetime.now()}] Failed to send notification: {e}")

def get_device():
    """Initializes and returns the Tuya device object."""
    if USE_LOCAL and DEVICE_IP and LOCAL_KEY:
        d = tinytuya.OutletDevice(DEVICE_ID, DEVICE_IP, LOCAL_KEY)
        d.set_version(3.3)
        return d, "local"
    else:
        c = tinytuya.Cloud(apiRegion=API_REGION, apiKey=API_KEY, apiSecret=API_SECRET)
        return c, "cloud"

def control_switch_2(turn_on):
    """Turns Switch 2 ON or OFF."""
    dev, mode = get_device()
    action = "ON" if turn_on else "OFF"
    print(f"[{datetime.now()}] Turning Switch 2 {action} via {mode}...")
    
    try:
        if mode == "local":
            # Local control
            if turn_on:
                dev.turn_on(switch=SWITCH_INDEX)
            else:
                dev.turn_off(switch=SWITCH_INDEX)
        else:
            # Cloud control
            commands = {"commands": [{"code": SWITCH_CODE, "value": turn_on}]}
            dev.sendcommand(DEVICE_ID, commands)
            
        send_notification(
            f"Battery Manager: Charging {action}",
            f"Switch 2 turned {action} because battery reached limit."
        )
        return True
    except Exception as e:
        print(f"Error controlling device: {e}")
        send_notification("Battery Manager Error", f"Failed to control switch: {e}", "critical")
        return False

def main():
    print(f"[{datetime.now()}] Starting Battery Manager Service...")
    print(f"Allowed SSIDs: {ALLOWED_SSIDS}")
    
    # State tracking to avoid repeated commands
    # We don't know the initial state of the switch, so we might send a command once to sync.
    # But better to only act when thresholds are crossed.
    last_action = None # 'ON' or 'OFF'

    while True:
        try:
            # 1. Check WiFi
            ssid = get_current_ssid()
            if ssid not in ALLOWED_SSIDS:
                print(f"[{datetime.now()}] Connected to '{ssid}' (Not allowed). Skipping check.")
                time.sleep(CHECK_INTERVAL)
                continue

            # 2. Check Battery
            battery = psutil.sensors_battery()
            if not battery:
                print("Battery information not available.")
                time.sleep(CHECK_INTERVAL)
                continue

            percent = battery.percent
            is_plugged = battery.power_plugged
            
            print(f"[{datetime.now()}] SSID: {ssid} | Battery: {percent}% | Plugged: {is_plugged}")

            # Log to InfluxDB
            write_to_influx("battery_status", 
                fields={"percent": float(percent), "plugged": bool(is_plugged)},
                tags={"ssid": ssid, "device": "laptop"}
            )

            # 3. Logic
            if percent >= BATTERY_MAX and is_plugged:
                # Battery full, turn OFF charging
                # We check if last_action is NOT OFF, meaning we haven't turned it off yet.
                # OR if we just started (last_action is None), we should enforce the state.
                # Force retry if plugged is still True
                print("Battery full. Cutting power...")
                if control_switch_2(False):
                    last_action = "OFF"
            
            elif percent < BATTERY_MIN and not is_plugged:
                # Battery low, turn ON charging
                if last_action != "ON":
                    print("Battery low. Starting power...")
                    if control_switch_2(True):
                        last_action = "ON"
            
            # Optional: If between 20 and 100, do nothing (hysteresis)

        except Exception as e:
            print(f"Error in main loop: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
