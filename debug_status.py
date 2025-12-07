import os
import tinytuya
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TUYA_API_KEY")
API_SECRET = os.getenv("TUYA_API_SECRET")
API_REGION = os.getenv("TUYA_API_REGION", "us")
DEVICE_ID = os.getenv("TUYA_DEVICE_ID")

c = tinytuya.Cloud(apiRegion=API_REGION, apiKey=API_KEY, apiSecret=API_SECRET)

print("--- Checking Device Status via Cloud ---")
try:
    # getstatus returns the DPS values
    status = c.getstatus(DEVICE_ID)
    print(f"getstatus: {json.dumps(status, indent=2)}")
    
    # getconnectstatus
    print(f"Checking connection status for {DEVICE_ID}...")
    connect_status = c.getconnectstatus(DEVICE_ID)
    print(f"getconnectstatus: {json.dumps(connect_status, indent=2)}")
    
except Exception as e:
    print(f"Error: {e}")
