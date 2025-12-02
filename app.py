import os
from flask import Flask, jsonify, request
import tinytuya
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "eb03bbe4df01c1351aaxjz")
DEVICE_NAME = "Socket Kamar Tidur"

# Cloud Configuration (Get these from Tuya IoT Platform: iot.tuya.com)
API_KEY = os.getenv("TUYA_API_KEY", "")
API_SECRET = os.getenv("TUYA_API_SECRET", "")
API_REGION = os.getenv("TUYA_API_REGION", "us") # us, eu, cn, in

# Local Configuration (Advanced: requires extracting local_key)
USE_LOCAL = os.getenv("USE_LOCAL", "false").lower() == "true"
LOCAL_KEY = os.getenv("TUYA_LOCAL_KEY", "")
DEVICE_IP = os.getenv("TUYA_DEVICE_IP", "")

# Initialize Tuya Connection
def get_device():
    if USE_LOCAL:
        if not LOCAL_KEY or not DEVICE_IP:
            raise ValueError("Local control requires TUYA_LOCAL_KEY and TUYA_DEVICE_IP")
        d = tinytuya.OutletDevice(DEVICE_ID, DEVICE_IP, LOCAL_KEY)
        d.set_version(3.3)
        return d
    else:
        if not API_KEY or not API_SECRET:
            raise ValueError("Cloud control requires TUYA_API_KEY and TUYA_API_SECRET")
        c = tinytuya.Cloud(apiRegion=API_REGION, apiKey=API_KEY, apiSecret=API_SECRET)
        return c

@app.route('/')
def index():
    return jsonify({
        "device": DEVICE_NAME,
        "id": DEVICE_ID,
        "endpoints": [
            {"url": "/on", "method": "GET/POST", "desc": "Turn Master Switch ON"},
            {"url": "/off", "method": "GET/POST", "desc": "Turn Master Switch OFF"},
            {"url": "/switch/<index>/on", "method": "GET/POST", "desc": "Turn specific switch ON (e.g. 1, 2, usb1)"},
            {"url": "/switch/<index>/off", "method": "GET/POST", "desc": "Turn specific switch OFF"},
            {"url": "/status", "method": "GET", "desc": "Get Device Status"}
        ]
    })

@app.route('/status', methods=['GET'])
def get_status():
    try:
        dev = get_device()
        if USE_LOCAL:
            data = dev.status()
        else:
            data = dev.getstatus(DEVICE_ID)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "hint": "Check your .env configuration"}), 500

@app.route('/sockets', methods=['GET'])
def get_sockets():
    try:
        dev = get_device()
        if USE_LOCAL:
            data = dev.status()
            # Local status is usually a dict of DPS values like {'1': True, '2': False}
            # We need to map them if possible, or just return the raw DPS
            return jsonify({"type": "local", "dps": data})
        else:
            data = dev.getstatus(DEVICE_ID)
            # Cloud data usually has a 'result' list with 'code' and 'value'
            if 'result' in data:
                sockets = [
                    {"code": item['code'], "value": item['value']}
                    for item in data['result'] 
                    if str(item['code']).startswith('switch')
                ]
                return jsonify({"sockets": sockets})
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/on', methods=['POST', 'GET'])
def turn_on_master():
    return control_switch("switch_1", True) # Usually switch_1 is master or first socket

@app.route('/off', methods=['POST', 'GET'])
def turn_off_master():
    return control_switch("switch_1", False)

@app.route('/switch/<index>/on', methods=['POST', 'GET'])
def turn_on_index(index):
    # Handle numeric indices or names like 'usb1'
    code = f"switch_{index}" if index.isdigit() else index
    return control_switch(code, True)

@app.route('/switch/<index>/off', methods=['POST', 'GET'])
def turn_off_index(index):
    code = f"switch_{index}" if index.isdigit() else index
    return control_switch(code, False)

def control_switch(code, value):
    try:
        dev = get_device()
        if USE_LOCAL:
            # Local control usually uses indices (1, 2, etc) rather than codes for simple calls,
            # but set_value works with DPS indices.
            # For simplicity in this generic script, we'll try standard methods or DPS.
            # Note: tinytuya's turn_on() defaults to the first switch.
            if code == "switch_1":
                if value: dev.turn_on()
                else: dev.turn_off()
            else:
                # Map 'switch_N' to DPS index if possible, or use set_value if we know the DPS mapping
                return jsonify({"error": "Local control for specific sockets requires DPS mapping. Use Cloud for easier code-based control."}), 501
        else:
            # Cloud control uses standard instruction sets
            commands = {"commands": [{"code": code, "value": value}]}
            res = dev.sendcommand(DEVICE_ID, commands)
            return jsonify(res)
            
        return jsonify({"message": f"Sent {value} to {code}", "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"Starting server for device: {DEVICE_ID}")
    app.run(host='0.0.0.0', port=5000, debug=True)
