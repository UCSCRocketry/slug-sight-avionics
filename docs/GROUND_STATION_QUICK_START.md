# Ground Station Quick Start Guide

## What It Does

The ground station receives telemetry data from your rocket via the ground Feather M4 and displays it in real-time on a web dashboard. All data is saved to CSV files for later analysis.

---

## How It Works (Simple Version)

```
Rocket → LoRa Radio → Ground Feather → USB → Ground Station → CSV File + Web Browser
```

**Step by step:**
1. **Rocket Feather** collects sensor data (altitude, acceleration, GPS, etc.)
2. **Rocket transmits** via LoRa radio at 915 MHz (10 times per second)
3. **Ground Feather** receives LoRa signal and forwards to laptop via USB
4. **Ground Station** (Python app) decodes the data
5. **Data is saved** to CSV file: `data/flights/2024-01-15_14-30-00.csv`
6. **Web dashboard** shows live telemetry at `http://localhost:5000`

---

## Quick Setup

### 1. Connect Hardware
```bash
# Plug ground Feather M4 into your laptop via USB cable
# Make sure LoRa antenna is connected to ground Feather
```

### 2. Find Serial Port
```bash
# macOS:
ls /dev/cu.usbmodem*

# Linux:
ls /dev/ttyACM*

# Windows (PowerShell):
dir COM*
```
You'll see something like `/dev/cu.usbmodem14201` - this is your port!

### 3. Update Configuration
Open `config/ground_config.yaml` and edit this line:
```yaml
serial:
  serial_port: "/dev/cu.usbmodem14201"  # ← Put your port here
```

### 4. Start Ground Station
```bash
cd ground_station
python app.py
```

You should see:
```
============================================================
  SLUG SIGHT GROUND STATION v2.0
  UCSC Rocket Team
  Feather M4 + Web Interface
============================================================

✓ Ground station ready!
✓ Logging to: data/flights/2024-01-15_14-30-00.csv

 Web interface: http://localhost:5000
   Open in your browser to view live telemetry

------------------------------------------------------------
```

### 5. Open Dashboard
Open your web browser and go to: **http://localhost:5000**

---

## What You'll See

### Console Output (Terminal)
```
[0001] PAD      | Alt:     0.5m | AccZ:   9.81 m/s² | RSSI:  -75dBm | GPS: 8 sats
[0002] PAD      | Alt:     0.6m | AccZ:   9.80 m/s² | RSSI:  -74dBm | GPS: 8 sats
[0003] BOOST    | Alt:    10.3m | AccZ:  25.45 m/s² | RSSI:  -78dBm | GPS: 8 sats
[0004] BOOST    | Alt:    22.8m | AccZ:  28.20 m/s² | RSSI:  -82dBm | GPS: 8 sats
[0005] COAST    | Alt:    45.2m | AccZ:   1.20 m/s² | RSSI:  -85dBm | GPS: 8 sats
```

**Color coding:**
- **PAD** = White (waiting on launch pad)
- **BOOST** = Green (motor burning)
- **COAST** = Yellow (coasting to apogee)
- **DESCENT** = Blue (parachute deployed)
- **LANDED** = Red (safely on ground)

### CSV File Output
Location: `data/flights/2024-01-15_14-30-00.csv`

```csv
timestamp,altitude,pressure,temperature,accel_x,accel_y,accel_z,state,packet_num
0.100,0.500,101325.0,20.5,0.0,0.0,9.81,PAD,1
0.200,0.600,101324.8,20.5,0.0,0.0,9.80,PAD,2
0.300,10.300,101200.5,20.3,2.5,1.2,25.45,BOOST,3
0.400,22.800,101050.2,20.0,3.1,1.8,28.20,BOOST,4
```

You can open this file in:
- **Excel** - For charts and analysis
- **Google Sheets** - Cloud analysis
- **Python/MATLAB** - Advanced analysis
- **Any text editor** - Quick inspection

---

## File Structure (What Does What?)

```
ground_station/
├── app.py                  ← Main program (Flask web server)
├── serial_reader.py        ← Reads USB serial from ground Feather
├── data/
│   ├── telemetry_parser.py ← Decodes binary packets
│   └── data_logger.py      ← Writes CSV files
├── templates/
│   └── dashboard.html      ← Web UI (graphs and displays)
└── utils/
    └── helpers.py          ← Config and logging setup
```

**You only need to run:** `python app.py`  
Everything else runs automatically!

---

## Troubleshooting

### ❌ "Serial port not found"
**Problem:** Ground Feather not detected  
**Solution:**
1. Check USB cable is plugged in
2. Try different USB port
3. Check cable supports data (not just charging)
4. Run `ls /dev/cu.*` (macOS) or `ls /dev/ttyACM*` (Linux) to find port
5. Update `serial_port` in `ground_config.yaml`

### ❌ "No packets received"
**Problem:** Not receiving telemetry data  
**Solution:**
1. **Check ground Feather:** Is green LED blinking? (should blink when receiving packets)
2. **Check rocket Feather:** Is it powered on and transmitting?
3. **Check antennas:** Both LoRa antennas connected?
4. **Check frequency:** Both radios on 915 MHz?
5. **Check distance:** Start close (~1 meter) for testing

### ❌ "Permission denied" on serial port
**Problem:** No permission to access USB port (Linux)  
**Solution:**
```bash
# Add yourself to dialout group
sudo usermod -a -G dialout $USER

# Log out and log back in, then retry
```

### ❌ "Module not found" errors
**Problem:** Missing Python packages  
**Solution:**
```bash
pip install -r requirements.txt
```

### ❌ Web dashboard won't load
**Problem:** Flask server not starting  
**Solution:**
1. Check if port 5000 is already in use
2. Try killing other processes: `lsof -ti:5000 | xargs kill`
3. Change port in `ground_config.yaml`:
   ```yaml
   web:
     port: 8080  # Use different port
   ```

---

## Data Files

### Where are CSV files saved?
```
data/flights/2024-01-15_14-30-00.csv
              └─ Timestamp when you started ground station
```

### How to analyze data?

**Excel/Google Sheets:**
1. Open CSV file
2. Create charts (altitude vs. time, acceleration vs. time, etc.)
3. Find max altitude, max acceleration, flight duration

**Python:**
```python
import pandas as pd

# Load CSV file
df = pd.read_csv('data/flights/2024-01-15_14-30-00.csv')

# Find max altitude
max_alt = df['altitude'].max()
print(f"Max altitude: {max_alt:.1f} m")

# Plot altitude vs. time
import matplotlib.pyplot as plt
plt.plot(df['timestamp'], df['altitude'])
plt.xlabel('Time (s)')
plt.ylabel('Altitude (m)')
plt.title('Flight Profile')
plt.show()
```

---

## Configuration Options

### `config/ground_config.yaml`

**Serial Port (most important):**
```yaml
serial:
  serial_port: "/dev/cu.usbmodem14201"  # ← Change this to your port
  baud_rate: 115200                      # Don't change (matches firmware)
```

**CSV Settings:**
```yaml
data_logging:
  csv:
    delimiter: ","              # Use comma separator
    include_header: true        # Include column names (recommended)
    float_precision: 6          # 6 decimal places
  output_directory: "./data/flights"
  buffer_size: 10               # Flush every 10 packets (1 second)
```

**Range Validation (reject bad data):**
```yaml
validation:
  enable_range_check: true      # Check if values are reasonable
  ranges:
    altitude: [-100, 50000]     # meters (-100 to 50 km)
    pressure: [10000, 110000]   # pascals
    temperature: [-50, 100]     # celsius
```

---

## API Endpoints (for custom apps)

If you want to write your own software to read telemetry:

```
GET http://localhost:5000/api/telemetry/latest
→ Returns most recent telemetry packet (JSON)

GET http://localhost:5000/api/telemetry/history
→ Returns last 100 packets (JSON array)

GET http://localhost:5000/api/stats
→ Returns statistics (packet count, rate, errors)
```

**Example:**
```bash
curl http://localhost:5000/api/telemetry/latest
```

Returns:
```json
{
  "timestamp": 10.5,
  "altitude": 150.3,
  "pressure": 95000.0,
  "temperature": 20.5,
  "accel_z": 20.45,
  "state": "BOOST",
  "packet_num": 42
}
```

---

## Tips

### Best Practices
1. **Start ground station BEFORE launching rocket** (don't miss data!)
2. **Keep ground Feather antenna vertical** (better reception)
3. **Position ground station upwind** (LoRa signal propagates better upwind)
4. **Test before flight day** (run ground station, power rocket on pad, verify telemetry)

### Expected Performance
- **Packet rate:** 10 Hz (10 packets per second)
- **Range:** ~500m with stock antennas (line of sight)
- **Latency:** ~20ms from sensor to display
- **CSV file size:** ~1 MB for 10-minute flight

### Pre-Flight Checklist
- [ ] Ground Feather connected via USB
- [ ] LoRa antenna connected to ground Feather
- [ ] Serial port configured in `ground_config.yaml`
- [ ] Ground station running: `python app.py`
- [ ] Dashboard loading at `http://localhost:5000`
- [ ] Rocket powered on and transmitting (test on pad)
- [ ] Receiving packets in console (green text)

---

## Summary

**To run ground station:**
```bash
cd ground_station
python app.py
```

**Open dashboard:**
```
http://localhost:5000
```

**Find data files:**
```
data/flights/2024-01-15_14-30-00.csv
```

That's it! The ground station handles everything else automatically.

For detailed technical information, see `docs/GROUND_STATION.md`.
