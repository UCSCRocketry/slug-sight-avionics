# Ground Station Architecture

## Overview

The ground station is a Python application that receives telemetry data from the **ground Feather M4** (connected via USB) and displays it in a web browser. All telemetry data is logged to CSV files.

---

## Data Flow Diagram

```
┌──────────────────┐
│  Rocket Feather  │ (in flight)
│   + LoRa Radio   │
└────────┬─────────┘
         │ 915 MHz LoRa
         │ (10 Hz telemetry)
         ▼
┌──────────────────┐
│  Ground Feather  │ (at launch site)
│   + LoRa Radio   │
└────────┬─────────┘
         │ USB Serial
         │ (115200 baud)
         ▼
┌──────────────────────────────────────────────────────┐
│              Ground Station (Python)                  │
│                                                       │
│  serial_reader.py → telemetry_parser.py              │
│         ↓                    ↓                        │
│  data_logger.py ←────────────┘                       │
│         ↓                                             │
│  CSV File: data/flights/2024-01-15_14-30-00.csv     │
│         ↓                                             │
│  app.py (Flask Web Server)                           │
└────────┬─────────────────────────────────────────────┘
         │ HTTP
         │ localhost:5000
         ▼
┌──────────────────┐
│   Web Browser    │
│  (Dashboard UI)  │
└──────────────────┘
```

---

## File Structure

```
ground_station/
├── app.py                    # Flask web server + main entry point
├── serial_reader.py          # USB serial communication with ground Feather
├── data/
│   ├── telemetry_parser.py   # Binary packet decoder
│   └── data_logger.py        # CSV file writer
├── templates/
│   └── dashboard.html        # Web UI (HTML/JavaScript)
└── utils/
    └── helpers.py            # Config loading, logging setup
```

---

## Detailed Component Breakdown

### 1. **serial_reader.py** - USB Serial Interface

**Purpose:** Reads data from the ground Feather M4 via USB serial.

**Key Classes:**
- `SerialReader` - Manages USB serial connection
- `TelemetryParser` - Decodes binary telemetry packets

**Packet Format from Ground Feather:**
```
PKT:<num>,<time>,<len>,<rssi>,<hex_data>
```
Example:
```
PKT:0042,10500,66,-85,0100000A...
     │    │    │   │   └─ Telemetry data (hex string)
     │    │    │   └─ RSSI signal strength (dBm)
     │    │    └─ Packet length (bytes)
     │    └─ Ground Feather timestamp (ms)
     └─ Packet sequence number
```

**Binary Telemetry Structure (66 bytes):**
```c
struct TelemetryPacket {
    uint32_t timestamp_ms;        // 4 bytes - Flight computer time
    float altitude;               // 4 bytes - Barometric altitude (m)
    float pressure;               // 4 bytes - Atmospheric pressure (Pa)
    float temperature;            // 4 bytes - Temperature (°C)
    float accel_x, accel_y, accel_z;  // 12 bytes - Acceleration (m/s²)
    float gyro_x, gyro_y, gyro_z;     // 12 bytes - Rotation rate (deg/s)
    float mag_x, mag_y, mag_z;        // 12 bytes - Magnetic field (µT)
    float gps_lat, gps_lon, gps_alt;  // 12 bytes - GPS coordinates
    uint8_t gps_satellites;       // 1 byte - GPS satellite count
    uint8_t state;                // 1 byte - Flight state (0-4)
    uint16_t packet_num;          // 2 bytes - Packet sequence number
} __attribute__((packed));        // Total: 66 bytes
```

**Flight States:**
```
0 = PAD      (On launch pad, waiting)
1 = BOOST    (Motor burning, accelerating)
2 = COAST    (Coasting to apogee)
3 = DESCENT  (Parachute deployed, descending)
4 = LANDED   (Landed safely)
```

---

### 2. **data/telemetry_parser.py** - Binary Packet Decoder

**Purpose:** Converts raw binary bytes into human-readable telemetry dictionary.

**Input:** Raw bytes from `serial_reader.py`  
**Output:** Python dictionary with labeled fields

**Example:**
```python
# Input: 66 bytes of binary data
raw_data = b'\x29\x00\x00\x00\x96\x43\x12\x00...'

# Output: Parsed telemetry dictionary
telemetry = {
    'timestamp': 10.5,      # seconds
    'altitude': 150.3,      # meters
    'pressure': 95000.0,    # pascals
    'temperature': 20.5,    # celsius
    'accel_x': 0.5,         # m/s²
    'accel_y': 1.2,
    'accel_z': 9.8,
    'gyro_x': 0.1,          # deg/s
    'gyro_y': 0.2,
    'gyro_z': 0.3,
    'mag_x': 25.0,          # µT
    'mag_y': 10.0,
    'mag_z': -30.0,
    'gps_lat': 37.0,        # degrees
    'gps_lon': -122.0,
    'gps_alt': 155.0,       # meters
    'gps_satellites': 8,
    'state': 'BOOST',
    'packet_num': 42,
    'ground_rssi': -85      # Signal strength (dBm)
}
```

**Range Validation:**
- Checks if values are reasonable (altitude < 50 km, temperature between -50°C and 100°C, etc.)
- Rejects packets with out-of-range values to prevent corrupted data

---

### 3. **data/data_logger.py** - CSV File Writer

**Purpose:** Writes telemetry to timestamped CSV files.

**Features:**
- **Auto-generates filenames:** `2024-01-15_14-30-00.csv`
- **CSV header row:** Column names on first line
- **Buffered writing:** Flushes every 10 packets (configurable)
- **Float precision:** 6 decimal places (configurable)

**Example CSV Output:**
```csv
timestamp,altitude,pressure,temperature,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,gps_lat,gps_lon,gps_alt,gps_satellites,state,packet_num,ground_rssi
0.000,0.000,101325.000,20.500,0.000,0.000,9.800,0.000,0.000,0.000,25.000,10.000,-30.000,37.000,-122.000,155.000,0,PAD,0,-85
0.100,1.234,101300.000,20.480,0.500,1.200,9.850,0.100,0.200,0.300,25.100,10.050,-30.050,37.000,-122.000,155.100,8,PAD,1,-84
0.200,2.468,101280.000,20.460,1.000,2.400,10.200,0.200,0.400,0.600,25.200,10.100,-30.100,37.000,-122.000,155.200,8,PAD,2,-83
...
```

**File Location:** `data/flights/2024-01-15_14-30-00.csv`

---

### 4. **app.py** - Flask Web Server

**Purpose:** Main application that coordinates everything and serves the web interface.

**Architecture:**
```
┌─────────────────────────────────────────┐
│          Flask Web Server               │
│        (Main Thread - app.py)           │
│                                         │
│  Routes:                                │
│    / → dashboard.html                   │
│    /api/telemetry/latest → JSON         │
│    /api/telemetry/history → JSON        │
│    /api/stats → JSON                    │
└─────────────────────────────────────────┘
         ▲                    ▲
         │                    │
         │              (reads global state)
         │                    │
┌─────────────────────────────────────────┐
│      Background Telemetry Thread        │
│                                         │
│  1. serial_reader.read_packet()         │
│  2. telemetry_parser.parse()            │
│  3. data_logger.write()  → CSV file     │
│  4. Update global state (latest data)   │
│  5. Update history (last 1000 packets)  │
└─────────────────────────────────────────┘
```

**Global State Variables:**
- `latest_telemetry` - Most recent telemetry packet (dict)
- `telemetry_history` - Last 1000 packets (deque)
- `packet_count` - Total packets received
- `error_count` - Failed packet count

**Console Output Example:**
```
[0042] BOOST    | Alt:   150.3m | AccZ:  20.45 m/s² | RSSI:  -85dBm | GPS: 8 sats
[0043] BOOST    | Alt:   155.8m | AccZ:  22.10 m/s² | RSSI:  -84dBm | GPS: 8 sats
[0044] COAST    | Alt:   160.2m | AccZ:   1.20 m/s² | RSSI:  -83dBm | GPS: 8 sats
```

---

### 5. **templates/dashboard.html** - Web UI

**Purpose:** Real-time telemetry visualization in web browser.

**Access:** Open `http://localhost:5000` in your browser

**Features:**
- Live altitude graph
- Real-time sensor readings
- Flight state indicator
- GPS map (if available)
- Statistics (packet rate, connection status)

**API Endpoints:**
```javascript
// Get latest telemetry (updates dashboard)
fetch('/api/telemetry/latest')
  .then(response => response.json())
  .then(data => updateDashboard(data));

// Get telemetry history (for graphs)
fetch('/api/telemetry/history')
  .then(response => response.json())
  .then(data => plotAltitude(data));

// Get statistics
fetch('/api/stats')
  .then(response => response.json())
  .then(data => updateStats(data));
```

---

### 6. **utils/helpers.py** - Configuration & Logging

**Purpose:** Load YAML config and setup logging.

**Functions:**
- `load_config(path)` - Reads `ground_config.yaml`
- `setup_logging(config)` - Configures Python logging

---

## Configuration (`config/ground_config.yaml`)

### Key Settings:

**Serial Connection:**
```yaml
serial:
  serial_port: "/dev/cu.usbmodem14201"  # macOS
  # Linux: /dev/ttyACM0
  # Windows: COM3
  baud_rate: 115200
  timeout_s: 1.0
```

**Data Logging (CSV only):**
```yaml
data_logging:
  csv:
    delimiter: ","
    include_header: true
    float_precision: 6
  output_directory: "./data/flights"
  filename_format: "%Y-%m-%d_%H-%M-%S"
  buffer_size: 10  # Flush every 10 packets
```

**Telemetry Validation:**
```yaml
validation:
  enable_checksum: true
  enable_range_check: true
  ranges:
    altitude: [-100, 50000]     # meters
    pressure: [10000, 110000]   # pascals
    temperature: [-50, 100]     # celsius
    accel: [-200, 200]          # m/s²
    gyro: [-2000, 2000]         # deg/s
```

**Web Interface:**
```yaml
web:
  host: "0.0.0.0"   # Listen on all network interfaces
  port: 5000         # http://localhost:5000
  debug: false       # Set to true for development
```

---

## Complete Data Flow Example

### T+0ms: Rocket transmits telemetry
```
Rocket Feather:
  - Reads BMP280: altitude = 150.3m
  - Reads LSM6DSOX: accel_z = 20.45 m/s²
  - Packs into 66-byte binary packet
  - Transmits via LoRa (915 MHz)
```

### T+10ms: Ground Feather receives packet
```
Ground Feather:
  - Receives packet via LoRa
  - Measures RSSI = -85 dBm (signal strength)
  - Formats as: "PKT:42,10500,66,-85,<hex_data>"
  - Sends via USB serial to laptop
```

### T+15ms: Ground station processes packet
```python
# serial_reader.py reads USB serial
line = "PKT:42,10500,66,-85,0100000A96431200..."
packet = {
    'data': bytes.fromhex('0100000A96431200...'),
    'packet_num': 42,
    'rssi': -85
}

# telemetry_parser.py decodes binary
telemetry = {
    'timestamp': 10.5,
    'altitude': 150.3,
    'accel_z': 20.45,
    'state': 'BOOST',
    ...
}

# data_logger.py writes to CSV
writer.writerow([10.5, 150.3, 20.45, 'BOOST', ...])

# app.py updates global state
latest_telemetry = telemetry
telemetry_history.append(telemetry)

# Console output
print("[0042] BOOST    | Alt:   150.3m | AccZ:  20.45 m/s²")
```

### T+20ms: Browser updates
```javascript
// JavaScript in dashboard.html
fetch('/api/telemetry/latest')
  .then(data => {
    document.getElementById('altitude').textContent = data.altitude.toFixed(1);
    document.getElementById('state').textContent = data.state;
    updateAltitudeGraph(data);
  });
```

---

## How to Use

### 1. Connect Ground Feather
```bash
# Plug ground Feather M4 into laptop via USB
# Check serial port name:
ls /dev/cu.usbmodem*  # macOS
ls /dev/ttyACM*       # Linux
```

### 2. Update Configuration
Edit `config/ground_config.yaml`:
```yaml
serial:
  serial_port: "/dev/cu.usbmodem14201"  # Your port here
```

### 3. Start Ground Station
```bash
cd ground_station
python app.py
```

### 4. Open Dashboard
Open browser: `http://localhost:5000`

### 5. View Data Files
CSV files saved to: `data/flights/2024-01-15_14-30-00.csv`

---

## Troubleshooting

### "Serial port not found"
```bash
# List available ports
ls /dev/cu.*       # macOS
ls /dev/tty*       # Linux
dir COM*           # Windows (PowerShell)

# Update ground_config.yaml with correct port
```

### "No packets received"
1. Check ground Feather is powered on (LED blinking?)
2. Check rocket Feather is transmitting (test mode?)
3. Check LoRa frequency matches (915 MHz)
4. Check LoRa antenna connected to ground Feather

### "Telemetry looks corrupted"
- Check range validation in `ground_config.yaml`
- Enable checksum verification
- Check for radio interference

### "CSV file not created"
- Check `data/flights/` directory exists (created automatically)
- Check file permissions (write access?)
- Check disk space

---

## Statistics & Performance

**Expected Performance:**
- Packet rate: 10 Hz (10 packets/second)
- Latency: ~20ms (LoRa transmission + USB + processing)
- CSV flush rate: Every 10 packets (1 second)
- Web UI update rate: ~5 Hz (JavaScript polling)

**Memory Usage:**
- Telemetry history: 1000 packets × ~500 bytes = ~500 KB
- CSV buffer: 10 packets × ~500 bytes = ~5 KB

**File Size Estimates:**
- 1 minute flight: ~600 packets × ~200 bytes/line = ~120 KB
- 10 minute flight: ~6000 packets × ~200 bytes/line = ~1.2 MB

---

## Summary

The ground station is a **3-stage pipeline**:

1. **Reception** (`serial_reader.py`) - Get data from ground Feather via USB
2. **Processing** (`telemetry_parser.py`) - Decode binary packets into readable data
3. **Storage & Display** (`data_logger.py` + `app.py`) - Write to CSV and show in browser

All data is stored in **CSV format only** for easy analysis in Excel, Python, MATLAB, etc.

The web interface runs on `localhost:5000` and updates in real-time as packets arrive.
