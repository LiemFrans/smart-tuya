import os
import time
import tinytuya
import subprocess
from dotenv import load_dotenv
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load environment variables
load_dotenv()

API_KEY = os.getenv("TUYA_API_KEY")
API_SECRET = os.getenv("TUYA_API_SECRET")
API_REGION = os.getenv("TUYA_API_REGION", "us")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
DEVICE_NAME = "Socket Kamar Tidur"

# InfluxDB Config
INFLUX_URL = os.getenv("INFLUXDB_URL")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET")

# Configuration
CHECK_INTERVAL = 10  # Seconds between checks

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

def send_notification(title, message, urgency="normal"):
    """Sends a GNOME notification using notify-send."""
    try:
        # Use 'tuya-app' to match the filename 'tuya-app.desktop'
        subprocess.run(["notify-send", "-a", "tuya-app", "-u", urgency, title, message])
        print(f"[{datetime.now()}] Notification sent: {title} - {message}")
    except Exception as e:
        print(f"[{datetime.now()}] Failed to send notification: {e}")

def get_socket_details(c, device_id):
    try:
        status = c.getstatus(device_id)
        if 'result' in status:
            details = []
            for item in status['result']:
                code = item.get('code', '')
                if code.startswith('switch'):
                    # Extract number if possible, e.g. switch_1 -> S1
                    label = code.replace('switch_', 'S').replace('switch', 'S')
                    val = "ON" if item.get('value') else "OFF"
                    details.append(f"{label}: {val}")
            return ", ".join(details)
    except Exception as e:
        print(f"Error fetching details: {e}")
    return "Details unavailable"

def main():
    print(f"[{datetime.now()}] Starting Monitor Service for {DEVICE_NAME} ({DEVICE_ID})...")
    
    # Initialize Cloud connection
    try:
        c = tinytuya.Cloud(apiRegion=API_REGION, apiKey=API_KEY, apiSecret=API_SECRET)
    except Exception as e:
        print(f"Error initializing Tuya Cloud: {e}")
        return

    # Initial state
    last_is_online = None 

    while True:
        try:
            # Check connection status
            # We use Cloud to check 'online' status because local scan is tricky if IP changes
            # However, Cloud has delay.
            # Let's try a hybrid approach:
            # 1. Try to connect locally (fastest check for ONLINE)
            # 2. If local fails, check Cloud (to confirm OFFLINE)
            
            is_online = False
            
            # Method 1: Simple Socket Connect (Ping)
            # We need the IP for this. Since we don't have a static IP in .env yet,
            # we can try to find it dynamically if we have the key.
            
            # For now, let's stick to Cloud but be aware of the delay.
            # OR, we can use the 'getstatus' which might fail faster if device is unreachable?
            # Actually, getstatus goes to Cloud API, so it just returns what Cloud knows.
            
            # To get REAL-TIME status, we MUST use Local.
            # Since the user couldn't find the IP, we will rely on Cloud for now.
            
            is_online = c.getconnectstatus(DEVICE_ID)
            
            # Log to InfluxDB
            write_to_influx("device_connectivity", 
                fields={"is_online": bool(is_online)},
                tags={"device_name": DEVICE_NAME, "device_id": DEVICE_ID}
            )
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if last_is_online is None:
                # First run, just set the state
                last_is_online = is_online
                status_str = "ONLINE" if is_online else "OFFLINE"
                print(f"[{current_time}] Initial Status: {status_str}")
                
                if is_online:
                    details = get_socket_details(c, DEVICE_ID)
                    send_notification(
                        f"{DEVICE_NAME} is Online", 
                        f"Initial Status: {details}",
                        urgency="normal"
                    )
            
            elif is_online != last_is_online:
                # Status changed
                if is_online:
                    # Changed from Offline -> Online
                    details = get_socket_details(c, DEVICE_ID)
                    send_notification(
                        f"{DEVICE_NAME} is Online", 
                        f"Reconnected. Status: {details}",
                        urgency="normal"
                    )
                    print(f"[{current_time}] Status Changed: OFFLINE -> ONLINE")
                else:
                    # Changed from Online -> Offline
                    send_notification(
                        f"{DEVICE_NAME} is Offline", 
                        "The device is not connected to WiFi or is unavailable.",
                        urgency="critical"
                    )
                    print(f"[{current_time}] Status Changed: ONLINE -> OFFLINE")
                
                last_is_online = is_online
            else:
                # No change, just log debug (optional, maybe too noisy)
                # print(f"[{current_time}] Status stable: {'ONLINE' if is_online else 'OFFLINE'}")
                pass

        except Exception as e:
            print(f"[{datetime.now()}] Error checking status: {e}")
            # We don't change last_is_online here to avoid flapping on network errors
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
