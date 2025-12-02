# Tuya Smart Socket Control

This project provides an HTTP API to control your "Socket Kamar Tidur" (IT SMART POWER SOCKET EXTENSION PS01).

## Prerequisites

1.  **Python 3** installed.
2.  **Tuya IoT Account** (for Cloud control or to get Local Keys).

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration:**
    Open `.env` and fill in your details.

    **Option A: Cloud Control (Easier)**
    - Go to [Tuya IoT Platform](https://iot.tuya.com/).
    - Create a project (Cloud > Development > Create Cloud Project).
    - Link your Tuya App account (Cloud > Development > Link Tuya App Account).
    - Get your **Access ID (API Key)** and **Access Secret (API Secret)** from the project overview.
    - Set `TUYA_API_KEY`, `TUYA_API_SECRET`, and `TUYA_API_REGION` in `.env`.

    **Option B: Local Control (Faster)**
    - You need the `LOCAL_KEY` of your device.
    - If you have the API Key/Secret from Option A, you can run the wizard to find it:
      ```bash
      python -m tinytuya wizard
      ```
    - Set `USE_LOCAL=true`, `TUYA_LOCAL_KEY`, and `TUYA_DEVICE_IP` in `.env`.

## Usage

1.  **Run the Server:**
    ```bash
    python app.py
    ```

2.  **Control the Device:**
    Open your browser or use `curl`:

    - **Turn ON Master:** `http://localhost:5000/on`
    - **Turn OFF Master:** `http://localhost:5000/off`
    - **Turn ON Socket 1:** `http://localhost:5000/switch/1/on`
    - **Turn OFF Socket 1:** `http://localhost:5000/switch/1/off`
    - **Check Status:** `http://localhost:5000/status`

## Device Info
- **Name:** Socket Kamar Tidur
- **ID:** `eb03bbe4df01c1351aaxjz`
- **Model:** IT SMART POWER SOCKET EXTENSION PS01
# smart-tuya
