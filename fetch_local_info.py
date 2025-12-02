import tinytuya
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TUYA_API_KEY")
API_SECRET = os.getenv("TUYA_API_SECRET")
API_REGION = os.getenv("TUYA_API_REGION", "us")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")

print(f"--- Fetching Local Key for {DEVICE_ID} ---")

try:
    # 1. Connect to Cloud to get the Local Key
    cloud = tinytuya.Cloud(apiRegion=API_REGION, apiKey=API_KEY, apiSecret=API_SECRET)
    devices = cloud.getdevices()
    
    target_device = None
    for dev in devices:
        if dev['id'] == DEVICE_ID:
            target_device = dev
            break
            
    if not target_device:
        print("Device not found in Cloud account!")
        exit(1)

    local_key = target_device.get('key')
    print(f"Found Local Key: {local_key}")
    
    # 2. Scan local network for the IP address
    print("\n--- Scanning Local Network for Device IP ---")
    print("This may take a few seconds...")
    
    # Scan for devices
    found_devices = tinytuya.deviceScan(verbose=False)
    
    device_ip = None
    
    # Look for our device in the scan results
    for ip, info in found_devices.items():
        if info['gwId'] == DEVICE_ID or info['id'] == DEVICE_ID:
            device_ip = ip
            print(f"Found Device IP: {device_ip}")
            break
            
    if not device_ip:
        print("Could not find device IP on local network. Make sure the device is plugged in and connected to WiFi.")
        print("If you unplugged it, please PLUG IT BACK IN so we can find its IP.")
    else:
        print("\n--- SUCCESS ---")
        print(f"Please update your .env file with:")
        print(f"TUYA_LOCAL_KEY={local_key}")
        print(f"TUYA_DEVICE_IP={device_ip}")
        print(f"USE_LOCAL=true")

except Exception as e:
    print(f"Error: {e}")
