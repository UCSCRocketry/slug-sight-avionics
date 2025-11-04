# Slug Sight Avionics - Complete Setup Guide

**Comprehensive walkthrough of the entire system: hardware setup, firmware flashing, ground station operation, and data flow**

---

## Table of Contents

1. [System Overview](#system-overview)
2. [What Each Part Does](#what-each-part-does)
3. [Hardware Assembly](#hardware-assembly)
4. [Software Installation](#software-installation)
5. [Firmware Flashing](#firmware-flashing)
6. [Ground Station Setup](#ground-station-setup)
7. [Testing The System](#testing-the-system)
8. [Telemetry Flow Example](#telemetry-flow-example)
9. [Troubleshooting](#troubleshooting)

---

# System Overview

The Slug Sight Avionics system consists of **three main components**:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  ROCKET         │       │  GROUND         │       │  LAPTOP         │
│  Feather M4     │──LoRa→│  Feather M4     │──USB──│  Ground Station │
│  (Transmitter)  │       │  (Bridge)       │       │  (Web UI)       │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

**The journey of a single data point:**
1. BMP280 sensor measures air pressure → 101,325 Pa
2. Rocket Feather reads it over SPI in ~0.5 milliseconds
3. Rocket Feather packages it with other sensor data into a 66-byte binary packet
4. Rocket Feather transmits packet via LoRa radio at 915 MHz (takes ~60ms)
5. Ground Feather receives packet, adds RSSI signal strength metadata
6. Ground Feather forwards packet to laptop via USB serial (115,200 baud)
7. Python script on laptop parses binary data → `{"pressure": 101325.0, ...}`
8. Flask web server updates dashboard → displays "Pressure: 101.3 kPa"
9. Data logger writes to CSV file: `1730678400,101325.0,...`

**Total latency: ~100-150 milliseconds** from sensor measurement to web display.

---

# What Each Part Does

## 🚀 Rocket Feather M4 (Flight Computer)

**Location:** Inside the rocket  
**Power:** 3.7V LiPo battery (JST connector)  
**Job:** Read sensors and transmit telemetry

### What happens inside the rocket Feather every 100 milliseconds:

```cpp
// 1. Read BMP280 barometer (SPI, ~0.5ms)
float pressure = bmp.readPressure();      // Example: 101325.0 Pa
float altitude = bmp.readAltitude(1013.25);  // Example: 150.5 m

// 2. Read LSM6DSOX IMU (I2C, ~1.5ms)
sensors_event_t accel, gyro;
lsm6ds.getEvent(&accel, &gyro);
// accel.x = 0.2 m/s²
// accel.y = -0.1 m/s²
// accel.z = 9.8 m/s² (sitting on pad)

// 3. Read LIS3MDL magnetometer (I2C, ~1.0ms)
sensors_event_t mag;
lis3mdl.getEvent(&mag);
// mag.x = 25.4 μT (pointing North)

// 4. Read GPS (UART, parsed in background)
float gps_lat = gps.latitude;   // Example: 36.9741
float gps_lon = gps.longitude;  // Example: -122.0308

// 5. Pack into binary struct (66 bytes)
struct TelemetryPacket {
    uint32_t timestamp_ms;  // 1500 (1.5 seconds since boot)
    float altitude;         // 150.5
    float pressure;         // 101325.0
    float temperature;      // 25.3
    float accel_x, y, z;    // 0.2, -0.1, 9.8
    float gyro_x, y, z;     // 0.0, 0.0, 0.0
    float mag_x, y, z;      // 25.4, 10.2, -35.8
    float gps_lat, lon, alt;// 36.9741, -122.0308, 155.0
    uint8_t gps_sats;       // 8
    uint8_t state;          // 0 (PAD)
    uint16_t crc;           // 0xAB12
};

// 6. Transmit via LoRa (915 MHz, ~60ms)
rf95.send((uint8_t*)&packet, sizeof(packet));
rf95.waitPacketSent();  // Blocks until transmission complete

// 7. Loop repeats in 100ms
```

**Output rate:** 10 packets/second (every 100ms)  
**Sensor polling:** BMP280, IMU, magnetometer read every cycle; GPS updates at its own 1 Hz rate  
**Flight state machine:** Detects launch, apogee, descent based on acceleration and altitude

---

## 📡 Ground Feather M4 (LoRa-to-USB Bridge)

**Location:** On the ground, connected to your laptop  
**Power:** USB power from laptop  
**Job:** Receive LoRa packets and forward to laptop

### What happens inside the ground Feather:

```cpp
// 1. Wait for LoRa packet (blocking, wakes on interrupt)
if (rf95.available()) {
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);
    
    // 2. Receive packet
    if (rf95.recv(buf, &len)) {
        // 3. Get signal strength
        int16_t rssi = rf95.lastRssi();  // Example: -45 dBm (strong signal)
        
        // 4. Format as text for serial port
        // Format: "PKT:<num>,<time>,<len>,<rssi>,<hex_data>"
        Serial.print("PKT:");
        Serial.print(packetCount++);
        Serial.print(",");
        Serial.print(millis());
        Serial.print(",");
        Serial.print(len);
        Serial.print(",");
        Serial.print(rssi);
        Serial.print(",");
        
        // 5. Convert binary to hex string
        for (int i = 0; i < len; i++) {
            if (buf[i] < 16) Serial.print("0");
            Serial.print(buf[i], HEX);
        }
        Serial.println();
        
        // Example output:
        // PKT:42,5123,66,-45,DC05000000A0C84200...
        //     ^   ^   ^  ^   ^
        //     |   |   |  |   Binary packet data (hex encoded)
        //     |   |   |  RSSI signal strength
        //     |   |   Packet length (66 bytes)
        //     |   Ground Feather uptime (milliseconds)
        //     Packet number
    }
}
```

**Why not run Python on the Feather?** Feather M4 can't run Python, only Arduino C++. Laptop handles all the complex parsing and visualization.

**Why a separate board?** This design:
- Keeps LoRa connection stable even if you restart the laptop software
- Allows you to unplug/replug USB without losing packets
- Provides RSSI (signal strength) data for each packet
- Simplifies debugging (can monitor serial output easily)

---

## 💻 Laptop Ground Station (Data Processing & Visualization)

**Location:** Your laptop/computer  
**Power:** Laptop battery/AC  
**Job:** Parse data, log to files, display on web interface

### Component Breakdown:

#### 1️⃣ **serial_reader.py** - USB Serial Communication

```python
class SerialReader:
    """Reads packets from ground Feather M4 via USB serial"""
    
    def __init__(self, config):
        # Open serial port (example: /dev/cu.usbmodem14201)
        self.ser = serial.Serial(
            port=config['serial_port'],    # "/dev/cu.usbmodem14201"
            baudrate=config['baud_rate'],  # 115200
            timeout=1.0
        )
    
    def read_packet(self):
        """Read one line from serial port"""
        line = self.ser.readline().decode('utf-8').strip()
        
        # Example line from ground Feather:
        # "PKT:42,5123,66,-45,DC05000000A0C84200..."
        
        if line.startswith("PKT:"):
            parts = line[4:].split(',', 4)
            return {
                'packet_num': int(parts[0]),      # 42
                'ground_time': int(parts[1]),     # 5123 ms
                'length': int(parts[2]),          # 66 bytes
                'rssi': int(parts[3]),            # -45 dBm
                'data': bytes.fromhex(parts[4])   # Binary packet data
            }
```

**What's happening:**
- Python opens the USB serial port (like opening a file)
- Reads one line at a time
- Splits the text format into metadata and binary data
- Returns a dictionary with all the info

---

#### 2️⃣ **telemetry_parser.py** - Binary Data Decoding

```python
class TelemetryParser:
    """Converts binary packet to human-readable dictionary"""
    
    def parse(self, data, metadata):
        """Parse 66-byte binary packet"""
        
        # Binary format: '<I 3f 3f 3f 3f 3f BB H'
        #   < = little-endian
        #   I = uint32 (4 bytes) - timestamp
        #   3f = 3 floats (12 bytes) - altitude, pressure, temp
        #   3f = 3 floats (12 bytes) - accel x,y,z
        #   3f = 3 floats (12 bytes) - gyro x,y,z
        #   3f = 3 floats (12 bytes) - mag x,y,z
        #   3f = 3 floats (12 bytes) - GPS lat,lon,alt
        #   B = uint8 (1 byte) - GPS satellites
        #   B = uint8 (1 byte) - flight state
        #   H = uint16 (2 bytes) - CRC checksum
        
        values = struct.unpack('<I 3f 3f 3f 3f 3f BB H', data)
        
        # Convert to dictionary with meaningful names
        return {
            'timestamp_ms': values[0],        # 1500
            'altitude': values[1],            # 150.5 m
            'pressure': values[2],            # 101325.0 Pa
            'temperature': values[3],         # 25.3 °C
            'accel_x': values[4],             # 0.2 m/s²
            'accel_y': values[5],             # -0.1 m/s²
            'accel_z': values[6],             # 9.8 m/s²
            'gyro_x': values[7],              # 0.0 deg/s
            'gyro_y': values[8],              # 0.0 deg/s
            'gyro_z': values[9],              # 0.0 deg/s
            'mag_x': values[10],              # 25.4 μT
            'mag_y': values[11],              # 10.2 μT
            'mag_z': values[12],              # -35.8 μT
            'gps_lat': values[13],            # 36.9741°
            'gps_lon': values[14],            # -122.0308°
            'gps_alt': values[15],            # 155.0 m
            'gps_satellites': values[16],     # 8
            'state': values[17],              # 0 (PAD)
            'crc': values[18],                # 0xAB12
            
            # Add metadata from ground Feather
            'ground_rssi': metadata['rssi'],  # -45 dBm
            'packet_num': metadata['packet_num']  # 42
        }
```

**What's happening:**
- Takes the 66 bytes of binary data
- Uses `struct.unpack()` to convert bytes → numbers
- Maps each number to a meaningful name
- Returns a Python dictionary that's easy to work with

---

#### 3️⃣ **data_logger.py** - CSV File Writing

```python
class DataLogger:
    """Writes telemetry to CSV file"""
    
    def write(self, telemetry):
        """Append one row to CSV"""
        
        # Create timestamped filename: flight_20251103_143022.csv
        # CSV format:
        # timestamp_ms,altitude,pressure,temperature,accel_x,...
        # 1500,150.5,101325.0,25.3,0.2,-0.1,9.8,...
        
        self.writer.writerow([
            telemetry['timestamp_ms'],
            telemetry['altitude'],
            telemetry['pressure'],
            # ... all fields ...
        ])
        self.file.flush()  # Write to disk immediately
```

**What's happening:**
- Opens a new CSV file for each flight session
- Appends one row per telemetry packet
- Flushes to disk immediately so data isn't lost if program crashes
- Files saved in `data/flights/` directory

---

#### 4️⃣ **app.py** - Flask Web Server

```python
app = Flask(__name__)

# Global variables (shared between threads)
latest_telemetry = {}       # Most recent packet
telemetry_history = deque(maxlen=1000)  # Last 1000 packets

def telemetry_thread():
    """Background thread that reads serial port"""
    while running:
        # Read from serial
        packet = reader.read_packet()
        
        # Parse binary data
        telemetry = parser.parse(packet['data'], packet)
        
        # Update global state
        latest_telemetry.update(telemetry)
        telemetry_history.append(telemetry)
        
        # Log to CSV
        data_logger.write(telemetry)

@app.route('/api/telemetry/latest')
def get_latest_telemetry():
    """API endpoint: returns latest packet as JSON"""
    return jsonify(latest_telemetry)
    # Returns: {"altitude": 150.5, "pressure": 101325.0, ...}

# Flask runs in main thread, telemetry_thread runs in background
```

**What's happening:**
- Flask web server runs on port 5000
- Background thread continuously reads serial port
- Updates global variables when new data arrives
- Web browser requests `/api/telemetry/latest` every 100ms
- Flask returns latest data as JSON
- JavaScript in browser updates display

---

#### 5️⃣ **dashboard.html** - Web Interface

```html
<!-- Auto-update every 100ms using JavaScript -->
<script>
async function updateTelemetry() {
    // Fetch latest data from Flask server
    const response = await fetch('/api/telemetry/latest');
    const data = await response.json();
    
    // Update HTML elements
    document.getElementById('altitude').textContent = 
        data.altitude.toFixed(1) + ' m';
    document.getElementById('pressure').textContent = 
        (data.pressure / 1000).toFixed(1) + ' kPa';
    // ... update all other fields ...
}

// Call every 100ms
setInterval(updateTelemetry, 100);
</script>

<!-- Display elements -->
<div class="telemetry-value">
    <span class="label">Altitude:</span>
    <span id="altitude">0.0 m</span>
</div>
```

**What's happening:**
- JavaScript makes HTTP request to Flask server every 100ms
- Server returns latest telemetry as JSON
- JavaScript updates HTML elements with new values
- CSS makes it look nice with colors and formatting

---

# Hardware Assembly

## Rocket Feather M4 Wiring

### Pin Connections:

| Sensor | Interface | Pins | Notes |
|--------|-----------|------|-------|
| **BMP280** | SPI | CS=10, MOSI=24, MISO=23, SCK=25 | Barometer (SPI for speed) |
| **LSM6DSOX** | I2C | SDA=22, SCL=23 | IMU (accel + gyro) |
| **LIS3MDL** | I2C | SDA=22, SCL=23 | Magnetometer (shares I2C bus) |
| **GPS** | UART | RX=0, TX=1 | Serial1 hardware UART |
| **RFM95W** | SPI | CS=8, RST=4, IRQ=3, MOSI=24, MISO=23, SCK=25 | LoRa radio |
| **Battery** | JST | BAT+, BAT- | 3.7V LiPo (500-2000 mAh) |

### Step-by-step wiring:

```
1. BMP280 Barometer (SPI):
   BMP280 VIN  → Feather 3V
   BMP280 GND  → Feather GND
   BMP280 SCK  → Feather SCK (Pin 25)
   BMP280 SDI  → Feather MOSI (Pin 24)
   BMP280 SDO  → Feather MISO (Pin 23)
   BMP280 CS   → Feather Pin 10

2. LSM6DSOX IMU (I2C):
   LSM6DS VIN  → Feather 3V
   LSM6DS GND  → Feather GND
   LSM6DS SDA  → Feather SDA (Pin 22)
   LSM6DS SCL  → Feather SCL (Pin 23)

3. LIS3MDL Magnetometer (I2C - shared bus):
   LIS3MDL VIN → Feather 3V
   LIS3MDL GND → Feather GND
   LIS3MDL SDA → Feather SDA (Pin 22) - same as IMU
   LIS3MDL SCL → Feather SCL (Pin 23) - same as IMU

4. GPS (UART):
   GPS VIN → Feather 3V
   GPS GND → Feather GND
   GPS TX  → Feather RX (Pin 0)
   GPS RX  → Feather TX (Pin 1)

5. RFM95W LoRa (SPI - shared bus with BMP280):
   RFM95 VIN  → Feather 3V
   RFM95 GND  → Feather GND
   RFM95 SCK  → Feather SCK (Pin 25) - shared
   RFM95 MOSI → Feather MOSI (Pin 24) - shared
   RFM95 MISO → Feather MISO (Pin 23) - shared
   RFM95 CS   → Feather Pin 8
   RFM95 RST  → Feather Pin 4
   RFM95 G0   → Feather Pin 3 (IRQ)

6. Battery:
   LiPo JST connector → Feather JST port
   (Red = positive, Black = ground)
```

**Power consumption:**
- Feather M4: ~50 mA
- All sensors: ~20 mA
- LoRa TX: ~120 mA (during transmission)
- **Total:** ~190 mA peak, ~70 mA average
- **Flight time with 1000 mAh battery:** ~14 hours continuous

---

## Ground Feather M4 Wiring

Much simpler! Only needs LoRa radio:

```
RFM95W LoRa Radio:
  RFM95 VIN  → Feather 3V
  RFM95 GND  → Feather GND
  RFM95 SCK  → Feather SCK (Pin 25)
  RFM95 MOSI → Feather MOSI (Pin 24)
  RFM95 MISO → Feather MISO (Pin 23)
  RFM95 CS   → Feather Pin 8
  RFM95 RST  → Feather Pin 4
  RFM95 G0   → Feather Pin 3

USB Cable:
  USB-C → Feather USB port → Laptop
```

**No battery needed** - powered by laptop USB.

---

# Software Installation

## 1. Install PlatformIO (for firmware)

**Option A: VS Code Extension (recommended)**
```bash
# Install VS Code if you don't have it
brew install --cask visual-studio-code

# Open VS Code, go to Extensions (Cmd+Shift+X)
# Search for "PlatformIO IDE"
# Click Install
```

**Option B: Command Line**
```bash
# Install Python first
brew install python3

# Install PlatformIO Core
pip3 install platformio

# Verify installation
pio --version
```

---

## 2. Install Python Dependencies (for ground station)

```bash
cd slug-sight-avionics
pip3 install -r requirements.txt
```

This installs:
- `pyserial` - USB serial communication
- `pyyaml` - Config file parsing
- `pandas` - CSV data handling
- `Flask` - Web server
- `Flask-Cors` - Allow browser requests

---

# Firmware Flashing

## Rocket Feather M4

```bash
cd firmware_rocket

# First time only: Install library dependencies
pio lib install

# Build firmware
pio run

# Connect rocket Feather to laptop via USB
# Flash firmware
pio run --target upload

# Monitor serial output (optional)
pio device monitor --baud 115200
```

**Expected serial output:**
```
Slug Sight Flight Computer v2.0
Initializing BMP280... OK
Initializing LSM6DSOX... OK
Initializing LIS3MDL... OK
Initializing GPS... OK
Initializing LoRa (915 MHz)... OK
Ready for flight!

[0001] PAD     | Alt:   100.2m | AccZ:  9.81 m/s² | GPS: 0 sats
[0002] PAD     | Alt:   100.3m | AccZ:  9.78 m/s² | GPS: 3 sats
[0003] PAD     | Alt:   100.1m | AccZ:  9.82 m/s² | GPS: 5 sats
```

---

## Ground Feather M4

```bash
cd firmware_ground

# Install libraries (first time only)
pio lib install

# Build and upload
pio run --target upload

# Monitor serial output
pio device monitor --baud 115200
```

**Expected serial output:**
```
Slug Sight Ground Receiver v2.0
Initializing LoRa (915 MHz)... OK
Listening for rocket...

PKT:1,1234,66,-45,DC05000000A0C842...
PKT:2,1334,66,-44,E0050000A0C84200...
PKT:3,1434,66,-46,E4050000A1C84200...
```

Each line starting with `PKT:` is a packet forwarded to your laptop.

---

# Ground Station Setup

## 1. Find Ground Feather's Serial Port

**macOS:**
```bash
ls /dev/cu.usbmodem*
# Output: /dev/cu.usbmodem14201
```

**Linux:**
```bash
ls /dev/ttyACM*
# Output: /dev/ttyACM0
```

**Windows:**
```
Open Device Manager → Ports (COM & LPT)
Look for "USB Serial Device (COM3)" or similar
```

---

## 2. Configure Serial Port

Edit `config/ground_config.yaml`:

```yaml
serial:
  serial_port: "/dev/cu.usbmodem14201"  # <-- Change this!
  baud_rate: 115200
  timeout: 1.0

web_interface:
  host: "0.0.0.0"  # Allow access from other devices on network
  port: 5000

data_logging:
  directory: "data/flights"
  prefix: "flight"
  create_subdirs: true
```

---

## 3. Run Ground Station

```bash
cd ground_station
python app.py
```

**Expected output:**
```
============================================================
  SLUG SIGHT GROUND STATION v2.0
  UCSC Rocket Team
  Feather M4 + Web Interface
============================================================

✓ Ground station ready!
✓ Logging to: data/flights/flight_20251103_143022.csv

 Web interface: http://localhost:5000
   Open in your browser to view live telemetry

------------------------------------------------------------

Starting web server...
 * Running on http://0.0.0.0:5000

Connected to ground Feather on /dev/cu.usbmodem14201
Listening for packets...

[0001] PAD     | Alt:   100.2m | AccZ:  9.81 m/s² | RSSI: -45dBm | GPS: 8 sats
[0002] PAD     | Alt:   100.3m | AccZ:  9.78 m/s² | RSSI: -44dBm | GPS: 8 sats
```

---

## 4. Open Web Interface

Open browser to: **http://localhost:5000**

You should see the dashboard with:
- ✅ Live altitude, pressure, temperature
- ✅ Acceleration (X, Y, Z)
- ✅ Gyro rates
- ✅ Magnetic field
- ✅ GPS coordinates and satellite count
- ✅ Flight state (PAD/BOOST/COAST/DESCENT/LANDED)
- ✅ Signal strength (RSSI)
- ✅ Packet statistics

The display updates **10 times per second** (100ms refresh rate).

---

# Testing The System

## Bench Test (Rocket on Table)

1. **Power on rocket Feather** (via USB or battery)
   - Serial monitor should show sensor readings
   - GPS will slowly acquire satellites (may take 30-60 seconds outdoors)

2. **Connect ground Feather to laptop**
   - Should see `PKT:...` lines in serial monitor

3. **Start ground station:**
   ```bash
   cd ground_station
   python app.py
   ```

4. **Open web interface:** http://localhost:5000
   - Should see live data updating
   - Altitude should be stable (~±0.5m noise)
   - Acceleration Z should be ~9.8 m/s² (gravity)

5. **Tilt/move the rocket:**
   - Acceleration values should change
   - Gyro should show rotation rates
   - Magnetometer should show compass heading changes

---

## Range Test

1. **Setup ground station indoors**
   - Connect ground Feather to laptop
   - Start `python app.py`
   - Keep laptop plugged in

2. **Power rocket Feather with battery**
   - Disconnect USB
   - Connect LiPo battery to JST port

3. **Walk away with rocket**
   - Monitor web interface for RSSI signal strength
   - Typical ranges:
     - **-40 to -50 dBm:** Excellent (< 100m)
     - **-50 to -70 dBm:** Good (100m - 500m)
     - **-70 to -90 dBm:** Fair (500m - 2km)
     - **< -90 dBm:** Weak (> 2km, may lose packets)

4. **Record maximum reliable distance**
   - Note where you start losing packets
   - This is your operational range

---

## Pre-Flight Checklist

Before launch day:

- [ ] Rocket Feather firmware uploaded and tested
- [ ] Ground Feather firmware uploaded and tested
- [ ] All sensors reading correctly (BMP280, IMU, mag, GPS)
- [ ] GPS acquires satellites outdoors (8+ satellites)
- [ ] LoRa transmission working (RSSI visible on ground station)
- [ ] Web interface displays live data
- [ ] CSV logging working (check `data/flights/` directory)
- [ ] Battery fully charged
- [ ] Range test completed (know your maximum distance)
- [ ] Backup battery available

On launch day:

- [ ] Ground station laptop fully charged
- [ ] Ground Feather connected and receiving packets
- [ ] Web interface open and updating
- [ ] GPS has satellite lock (8+ satellites)
- [ ] Rocket battery connected and fully charged
- [ ] Clear line of sight to launch pad

---

# Telemetry Flow Example

Let's trace **one altitude measurement** from sensor to web display:

## Timeline: 1.500 seconds after rocket boot

### Step 1: Sensor Measurement (Rocket Feather)
**Time: T+0ms**

```cpp
// BMP280 barometer measures air pressure
float pressure = bmp.readPressure();  
// Returns: 101,325.0 Pa (sea level pressure)

// BMP280 calculates altitude from pressure
float altitude = bmp.readAltitude(1013.25);
// Returns: 150.5 meters (assuming we're at the launch site)
```

**What's physically happening:**
- BMP280 has a tiny piezo-resistive pressure sensor
- Air molecules press on it
- Resistance changes with pressure
- Chip converts resistance → digital number
- SPI bus transfers 3 bytes: `0x01`, `0x8A`, `0xE5`
- Arduino library converts bytes → `101325.0` (floating point)
- Formula converts pressure → altitude: `150.5` meters

**Time taken:** 0.5 milliseconds

---

### Step 2: Packet Construction (Rocket Feather)
**Time: T+3ms** (after reading all sensors)

```cpp
// Create binary packet struct
struct TelemetryPacket packet;
packet.timestamp_ms = millis();      // 1500 (milliseconds since boot)
packet.altitude = 150.5;             // From BMP280
packet.pressure = 101325.0;          // From BMP280
packet.temperature = 25.3;           // From BMP280
packet.accel_x = 0.2;                // From LSM6DSOX
packet.accel_y = -0.1;
packet.accel_z = 9.8;
// ... all other sensor values ...
packet.crc = calculate_crc(&packet, 64);  // Checksum for error detection

// Convert struct to raw bytes
uint8_t* bytes = (uint8_t*)&packet;
// bytes[0-3]   = 0xDC 0x05 0x00 0x00  (timestamp: 1500)
// bytes[4-7]   = 0x00 0x00 0x16 0x43  (altitude: 150.5)
// bytes[8-11]  = 0x00 0xA0 0xC8 0x47  (pressure: 101325.0)
// bytes[12-15] = 0xCD 0xCC 0xCA 0x41  (temperature: 25.3)
// ... (total 66 bytes)
```

**Binary representation in memory:**
```
Offset  Hex Values          Meaning
------  ------------------  --------------------------
0x00    DC 05 00 00         timestamp_ms = 1500
0x04    00 00 16 43         altitude = 150.5
0x08    00 A0 C8 47         pressure = 101325.0
0x0C    CD CC CA 41         temperature = 25.3
0x10    CD CC 4C 3E         accel_x = 0.2
0x14    CD CC CC BD         accel_y = -0.1
0x18    CD CC 1C 41         accel_z = 9.8
...     ...                 (gyro, mag, GPS data)
0x40    AB 12               crc = 0x12AB
```

**Time taken:** 0.2 milliseconds

---

### Step 3: LoRa Transmission (Rocket Feather)
**Time: T+3.2ms**

```cpp
// Send packet via RadioHead library
rf95.send((uint8_t*)&packet, 66);
rf95.waitPacketSent();
```

**What's physically happening:**
1. RFM95W LoRa chip receives 66 bytes over SPI
2. Chip adds forward error correction (FEC) → 66 bytes becomes ~100 bytes with redundancy
3. Chip modulates data onto 915 MHz carrier wave using chirp spread spectrum
4. Radio waves propagate through air at speed of light (3×10⁸ m/s)
5. Ground Feather antenna receives radio waves 2 km away:
   - Travel time: 2000m ÷ 3×10⁸ m/s = **0.0000067 seconds** (6.7 microseconds)
   - But LoRa transmission itself takes much longer due to spread spectrum

**Time taken:** 
- Transmission time: ~60 milliseconds (depends on spreading factor)
- Propagation delay: negligible (microseconds)

**Total LoRa latency: ~60ms**

---

### Step 4: LoRa Reception (Ground Feather)
**Time: T+63ms**

```cpp
// Ground Feather RFM95W receives packet
if (rf95.available()) {
    uint8_t buf[66];
    uint8_t len = sizeof(buf);
    
    if (rf95.recv(buf, &len)) {
        // buf now contains: DC 05 00 00 00 00 16 43 ...
        
        int16_t rssi = rf95.lastRssi();  // -45 dBm
        
        // Forward to laptop via USB serial
        Serial.print("PKT:42,5123,66,-45,");
        for (int i = 0; i < len; i++) {
            if (buf[i] < 16) Serial.print("0");
            Serial.print(buf[i], HEX);
        }
        Serial.println();
        
        // Output on USB serial:
        // "PKT:42,5123,66,-45,DC05000000001643...12AB\n"
    }
}
```

**Time taken:** 1 millisecond (minimal processing)

---

### Step 5: USB Serial Transfer (Ground Feather → Laptop)
**Time: T+64ms**

The text string `"PKT:42,5123,66,-45,DC050000...12AB\n"` is sent over USB:

- String length: ~150 characters
- USB serial baud rate: 115,200 bits/second
- Bits per character: 10 (8 data + 1 start + 1 stop)
- Transfer time: 150 chars × 10 bits ÷ 115,200 bps = **13 milliseconds**

**Total USB latency: ~13ms**

---

### Step 6: Python Serial Read (Laptop)
**Time: T+77ms**

```python
# serial_reader.py
line = ser.readline()  # Blocks until '\n' received
# line = b"PKT:42,5123,66,-45,DC05000000001643...12AB\n"

# Parse the line
parts = line.decode('utf-8').strip()[4:].split(',', 4)
packet = {
    'packet_num': 42,
    'ground_time': 5123,
    'length': 66,
    'rssi': -45,
    'data': bytes.fromhex('DC05000000001643...12AB')
}
```

**Time taken:** < 1 millisecond

---

### Step 7: Binary Parsing (Laptop)
**Time: T+78ms**

```python
# telemetry_parser.py
import struct

# Unpack 66 bytes according to format string
values = struct.unpack('<I 3f 3f 3f 3f 3f BB H', packet['data'])

# values[0] = 1500         (timestamp_ms)
# values[1] = 150.5        (altitude) ← OUR VALUE!
# values[2] = 101325.0     (pressure)
# values[3] = 25.3         (temperature)
# ...

telemetry = {
    'timestamp_ms': 1500,
    'altitude': 150.5,      # ← Here it is!
    'pressure': 101325.0,
    'temperature': 25.3,
    # ... all other fields ...
    'ground_rssi': -45
}
```

**What `struct.unpack` does:**
```python
# Binary bytes:     00 00 16 43
# Interpreted as float (little-endian IEEE 754):
#   0x43160000 = 150.5
```

**Time taken:** < 1 millisecond

---

### Step 8: Data Logging (Laptop)
**Time: T+79ms**

```python
# data_logger.py
csv_writer.writerow([
    1500,      # timestamp_ms
    150.5,     # altitude ← Written to CSV
    101325.0,  # pressure
    25.3,      # temperature
    # ... all fields ...
])
file.flush()  # Force write to disk
```

**Result:** File `flight_20251103_143022.csv` now contains:
```csv
timestamp_ms,altitude,pressure,temperature,...
1400,149.8,101330.0,25.2,...
1500,150.5,101325.0,25.3,...  ← New line added!
```

**Time taken:** ~5 milliseconds (disk I/O)

---

### Step 9: Flask State Update (Laptop)
**Time: T+84ms**

```python
# app.py (telemetry_thread function)
latest_telemetry = {
    'altitude': 150.5,  # ← Updated!
    'pressure': 101325.0,
    # ... all other fields ...
}

telemetry_history.append(latest_telemetry.copy())
```

**What happened:** 
- Python dictionary updated in memory
- This is thread-safe (Python GIL protects it)
- Flask web server can now access this data

**Time taken:** < 0.1 milliseconds

---

### Step 10: Web Browser Request (Laptop → Browser)
**Time: T+100ms**

JavaScript in the web browser makes an HTTP request every 100ms:

```javascript
// dashboard.html
async function updateTelemetry() {
    const response = await fetch('http://localhost:5000/api/telemetry/latest');
    const data = await response.json();
    // data = {"altitude": 150.5, "pressure": 101325.0, ...}
}

setInterval(updateTelemetry, 100);  // Call every 100ms
```

**Flask server responds:**
```python
# app.py
@app.route('/api/telemetry/latest')
def get_latest_telemetry():
    return jsonify(latest_telemetry)
    # Returns JSON: {"altitude": 150.5, ...}
```

**Time taken:** 
- HTTP request/response: ~5 milliseconds (localhost)

---

### Step 11: Web Display Update (Browser)
**Time: T+105ms**

```javascript
// Update HTML with new value
document.getElementById('altitude').textContent = 
    data.altitude.toFixed(1) + ' m';

// Result: <span id="altitude">150.5 m</span>
```

**User sees:**
```
┌─────────────────────────────┐
│  ALTITUDE                   │
│  150.5 m                    │
└─────────────────────────────┘
```

**Time taken:** < 1 millisecond (DOM update)

---

## Total Journey Time

| Step | Component | Action | Latency |
|------|-----------|--------|---------|
| 1 | Rocket: BMP280 | Measure pressure | 0.5 ms |
| 2 | Rocket: Feather M4 | Build packet | 0.2 ms |
| 3 | Rocket: RFM95W | LoRa transmission | 60 ms |
| 4 | Ground: RFM95W | LoRa reception | 1 ms |
| 5 | Ground: Feather M4 | USB serial send | 13 ms |
| 6 | Laptop: Python | Serial read | 1 ms |
| 7 | Laptop: Python | Binary parsing | 1 ms |
| 8 | Laptop: Python | CSV logging | 5 ms |
| 9 | Laptop: Python | State update | 0.1 ms |
| 10 | Laptop: Flask | HTTP response | 5 ms |
| 11 | Browser: JavaScript | DOM update | 1 ms |
| **TOTAL** | | **Sensor → Display** | **~88 ms** |

**Plus:** Browser polls every 100ms, so worst case you wait up to 100ms for the next poll.

**Total end-to-end latency: 100-200 milliseconds**

This means when the rocket is at 150.5 meters, you see "150.5 m" on your screen about **0.1-0.2 seconds** later!

---

# Troubleshooting

## Ground Feather Not Appearing on USB

**Problem:** Can't find `/dev/cu.usbmodem*` or `/dev/ttyACM*`

**Solutions:**
```bash
# 1. Check if Feather is recognized at all
system_profiler SPUSBDataType | grep -A 10 Feather

# 2. Try different USB cable (must be data cable, not charge-only)

# 3. Press reset button on Feather twice quickly
#    → Should enter bootloader mode (red LED pulsing)

# 4. Check dmesg on Linux
dmesg | tail -20

# 5. Install drivers (Windows only)
#    Download from: https://www.adafruit.com/drivers
```

---

## No Packets Received

**Problem:** Ground station shows "Waiting for packets..."

**Troubleshooting steps:**

1. **Check rocket Feather is transmitting:**
   ```bash
   # Connect rocket to USB, monitor serial
   cd firmware_rocket
   pio device monitor
   
   # Should see: "LoRa TX: 66 bytes, RSSI: -45 dBm"
   ```

2. **Check ground Feather is receiving:**
   ```bash
   # Monitor ground Feather serial
   cd firmware_ground
   pio device monitor
   
   # Should see: "PKT:1,1234,66,-45,DC05..."
   ```

3. **Check LoRa configuration matches:**
   - Both must use same frequency (915 MHz)
   - Both must use same spreading factor (7)
   - Both must use same bandwidth (125 kHz)
   - Check `firmware_rocket/src/main.cpp` and `firmware_ground/src/main.cpp`

4. **Check antenna connections:**
   - RFM95W must have antenna connected (coiled wire or SMA antenna)
   - **NEVER** transmit without antenna → can damage radio

5. **Reduce distance:**
   - Put both Feathers within 1 meter for testing
   - Should get very strong signal (RSSI > -40 dBm)

---

## Web Interface Not Loading

**Problem:** Browser shows "Can't connect to localhost:5000"

**Solutions:**

1. **Check Flask is running:**
   ```bash
   ps aux | grep python
   # Should see: python app.py
   ```

2. **Check firewall (macOS):**
   ```
   System Preferences → Security & Privacy → Firewall
   → Allow Python to accept connections
   ```

3. **Try explicit IP:**
   ```
   http://127.0.0.1:5000
   ```

4. **Check Flask output:**
   ```
   * Running on http://0.0.0.0:5000
   ```
   Should see this message when Flask starts

---

## GPS Not Getting Fix

**Problem:** GPS shows 0 satellites

**Solutions:**

1. **Go outside** - GPS needs clear sky view
2. **Wait 30-60 seconds** - Cold start takes time
3. **Check antenna:**
   - Ultimate GPS has ceramic patch antenna on top
   - Must face up toward sky
   - Metal/carbon fiber can block signal
4. **Verify GPS module:**
   ```bash
   # Monitor Serial1 output
   pio device monitor
   # Should see NMEA sentences: $GPGGA, $GPRMC, etc.
   ```

---

## CSV File Not Created

**Problem:** `data/flights/` directory is empty

**Solutions:**

1. **Check directory exists:**
   ```bash
   ls -la data/flights/
   ```

2. **Check permissions:**
   ```bash
   chmod 755 data/flights/
   ```

3. **Check Python logs:**
   - Look for error messages in terminal where you ran `python app.py`

4. **Check config:**
   ```yaml
   # config/ground_config.yaml
   data_logging:
     directory: "data/flights"  # Must match actual directory
   ```

---

## High Packet Loss

**Problem:** RSSI < -90 dBm, many dropped packets

**Solutions:**

1. **Increase TX power** (rocket firmware):
   ```cpp
   rf95.setTxPower(23, false);  // Max power for RFM95W
   ```

2. **Reduce data rate:**
   ```cpp
   rf95.setSpreadingFactor(10);  // Slower but more reliable
   // Default is 7 (fastest)
   ```

3. **Add external antenna:**
   - Replace wire antenna with SMA antenna
   - Use directional Yagi antenna on ground

4. **Check line of sight:**
   - Hills, buildings, trees block signal
   - Launch from clear area

---

# Next Steps

✅ You now understand:
- How each component works
- How to wire the hardware
- How to flash firmware
- How to run the ground station
- How telemetry flows through the entire system

**Ready for launch!** 🚀

For more details, see:
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - Technical architecture
- [`hardware.md`](hardware.md) - Hardware specifications and BOM
- [`README.md`](../README.md) - Project overview

---

**Good luck with your flight!**  
*UCSC Rocket Team*
