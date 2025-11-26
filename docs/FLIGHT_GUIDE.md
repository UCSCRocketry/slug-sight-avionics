# Flight Day Quick Start Guide

## Pre-Flight Setup (10 minutes before launch)

### 1. Hardware Setup
* [ ] Connect the receiver Arduino to the computer via USB.
* [ ] Verify the receiver Arduino is powered (LED on).
* [ ] Ensure the receiver LoRa antenna is securely connected.
* [ ] Power on the transmitter on the rocket (verify LED heartbeat).

### 2. Start Ground Station

```bash
cd gds

# Activate venv (macOS/Linux)
source venv/bin/activate

# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

python slugsight_gds.py
```

**Expected Output:**
```text
INFO - Data logging to: .../gds/flight_data/slugsight_20251109_120000.csv
INFO - Found GCS Receiver on port: /dev/cu.usbserial-XXX
INFO - Open this URL in your browser: [http://127.0.0.1:8080](http://127.0.0.1:8080)
```

### 3. Open Web Dashboard
1.  Open your web browser to: **http://127.0.0.1:8080**
2.  Verify the "Connected" status indicator is Green.
3.  Confirm that telemetry numbers are updating.

### 4. Pre-Flight Checks
* [ ] **Lithium Ion Battery**: VBat > 3.7V (Appears immediately on boot). Ideally fully charged (4.2V).
* [ ] **Signal**: RSSI > -100 dBm (Values closer to 0 are better).
* [ ] **GPS**: Wait for GPS fix (may take 30-60 seconds). Fix status will update from '0' to '1'.
* [ ] **Sensors**: Ensure altitude reading is reasonable relative to the launch site (approx. 0-100m).
* [ ] **Data Logging**: Confirm the Ground Station terminal indicates recording is active.

## During Flight

### Critical Monitoring
1.  **Status Indicator**: Should remain GREEN.
2.  **RSSI**: Signal strength. Expect this to drop as altitude increases.
3.  **Altitude**: Real-time barometric altitude.
4.  **Max Altitude**: Automatically tracks apogee.
5.  **GPS**: Tracks rocket position latitude/longitude.

### Data Rate Reference
At the standard 10 Hz transmission rate:
* **10 packets/second**
* **600 packets/minute**
* **1-minute flight**: Approx. 600 rows (150 KB)
* **5-minute flight**: Approx. 3,000 rows

## Post-Flight

### 1. Verify and Backup Data
It is critical to secure flight data immediately after recovery.

```bash
# Verify file exists and has content
ls -lh gds/flight_data/

# Create backup directory
mkdir -p ~/rocket_backups

# Copy data immediately
cp gds/flight_data/*.csv ~/rocket_backups/
```

### 2. Quick Field Analysis
Run this Python snippet in a separate terminal to verify apogee before leaving the launch pad:

```python
import pandas as pd

# Replace with actual filename
df = pd.read_csv('gds/flight_data/slugsight_CURRENT.csv') 

apogee = df['Altitude'].max()
print(f"Apogee: {apogee:.1f} meters")

max_vel = df['Velocity'].max()
print(f"Max Velocity: {max_vel:.1f} m/s")
```

### 3. Shutdown Ground Station
1.  Press `Ctrl+C` in the terminal running the Python script.
2.  Wait for the "Ground station shutdown complete" message.
3.  The CSV file is automatically closed and saved.

## Troubleshooting

### "Could not find GCS Receiver"

**1. macOS/Linux:**
```bash
ls /dev/cu.*
ls /dev/ttyUSB* /dev/ttyACM*
```

**2. Windows:**
* Open Device Manager > Ports (COM & LPT).
* Look for "USB Serial Device" or "Arduino".
* Alternatively, run: `python -m serial.tools.list_ports`

*Note: Update `ARDUINO_VID_PIDS` in `gds/slugsight_gds.py` if the device ID differs.*

### No Data Displayed
1.  Check the receiver Serial Monitor in Arduino IDE.
2.  Verify the baud rate is set to **115200**.
3.  Check the **Lithium Ion battery** voltage on the transmitter.
4.  Verify the transmitter is sending (LED should blink).

### CSV File Empty or Missing
* Check the terminal for error messages.
* Verify write permissions on the `gds/flight_data/` directory.
* Check available disk space.

## Emergency Procedures

### Computer Crash During Flight
* **Impact**: Partial data loss may occur (last ~10 packets).
* **Action**: Restart the ground station immediately. A new CSV file will be created automatically. The previous file will contain data up to the crash.

### Receiver Power Loss
* **Impact**: Data stream interruption.
* **Action**: Restore power and restart the ground station script. Old data is safe on disk; a new file will be initialized.

### Signal Loss
* **Impact**: Telemetry freezes.
* **Action**: Do not close the ground station. The receiver will continue listening. Data will resume automatically if the signal returns. Use RSSI values to estimate range and link margin.

## Success Checklist

* [ ] Ground station running and connected.
* [ ] Web dashboard active at http://127.0.0.1:8080.
* [ ] CSV filename noted for post-flight retrieval.
* [ ] GPS has fix (Status = 1).
* [ ] **Lithium Ion Battery** voltage nominal (> 3.7V).
* [ ] RSSI acceptable (> -100 dBm).
* [ ] All sensor readouts are updating dynamically.
