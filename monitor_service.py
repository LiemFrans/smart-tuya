import os
import time
import tinytuya
import subprocess
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

API_KEY = os.getenv("TUYA_API_KEY")
API_SECRET = os.getenv("TUYA_API_SECRET")
API_REGION = os.getenv("TUYA_API_REGION", "us")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
DEVICE_NAME = "Socket Kamar Tidur"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configuration
CHECK_INTERVAL = 10  # Seconds between checks

def send_telegram_message(message):
    """Sends a message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[{datetime.now()}] Failed to send Telegram message: {e}")

def send_notification(title, message, urgency="normal"):
    """Sends a GNOME notification using notify-send and Telegram."""
    try:
        # Use 'tuya-app' to match the filename 'tuya-app.desktop'
        subprocess.run(["notify-send", "-a", "tuya-app", "-u", urgency, title, message])
        print(f"[{datetime.now()}] Notification sent: {title} - {message}")
        
        # Send to Telegram as well
        telegram_msg = f"*{title}*\n{message}"
        if urgency == "critical":
            telegram_msg = f"🚨 *{title}* 🚨\n{message}"
        send_telegram_message(telegram_msg)
        
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
    last_api_error_notified = False

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
            
            # Handle error response from tinytuya
            if isinstance(is_online, dict) and 'Error' in is_online:
                error_msg = is_online['Error']
                payload = is_online.get('Payload', '')
                print(f"[{datetime.now()}] Error checking status: {error_msg} - {payload}")
                
                if "don't have access to this API" in payload:
                    if not last_api_error_notified:
                        # Extract IP if present for a cleaner message
                        clean_msg = "Your IP address is not whitelisted in Tuya Cloud."
                        if "your ip" in payload:
                            try:
                                ip_addr = payload.split("your ip(")[1].split(")")[0]
                                clean_msg = f"Your IP ({ip_addr}) is not whitelisted in Tuya Cloud."
                            except:
                                pass
                        
                        send_notification(
                            "Tuya API Access Error",
                            f"{clean_msg}\nPlease update the whitelist in Tuya IoT Platform.",
                            urgency="critical"
                        )
                        last_api_error_notified = True
                
                is_online = False
            else:
                last_api_error_notified = False

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
