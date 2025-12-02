import urllib.request
import json
import time

BASE_URL = "http://localhost:5000"

def call_api(endpoint, method="GET"):
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing: {endpoint} ...")
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"Failed: {e}")

print("--- 1. Check Status ---")
call_api("/status")

print("\n--- 2. Turn ON (Master) ---")
call_api("/on", method="POST")

print("\nWaiting 5 seconds...")
time.sleep(5)

print("\n--- 3. Turn OFF (Master) ---")
call_api("/off", method="POST")
