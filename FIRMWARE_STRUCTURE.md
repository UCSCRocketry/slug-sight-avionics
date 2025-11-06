# Firmware Structure

**Last Updated:** November 6, 2025

## Active Firmware Projects

This project uses a **dual Feather M4 architecture** with two separate firmware projects:

### 1. `firmware_rocket/` - Rocket Flight Computer 

**Hardware:** Adafruit Feather M4 Express (on the rocket)

**Sensors:**
- BMP280 Barometer (SPI)
- LSM6DSOX 6-axis IMU (I2C)
- LIS3MDL Magnetometer (I2C)
- Adafruit Ultimate GPS (UART)
- RFM95W LoRa Radio (SPI)

**Functions:**
- Reads all sensors at 10 Hz
- Runs flight state machine (PAD → BOOST → COAST → DESCENT → LANDED)
- Packs data into 66-byte binary telemetry packet
- Transmits via RadioHead LoRa library at 915 MHz

**Files:**
```
firmware_rocket/
├── platformio.ini          # Build configuration
└── src/
    ├── main.cpp            # Main firmware (sensor reading + transmission)
    └── state/
        └── flight_state.h  # Flight state machine (detects launch/apogee)
```

**How to flash:**
```bash
cd firmware_rocket
pio run --target upload
pio device monitor
```

---

### 2. `firmware_ground/` - Ground Receiver Bridge 

**Hardware:** Adafruit Feather M4 Express (on ground, connected to laptop via USB)

**Sensors:**
- RFM95W LoRa Radio (SPI) - ONLY sensor needed

**Functions:**
- Receives LoRa packets from rocket
- Formats as: `PKT:<num>,<time>,<len>,<rssi>,<hex_data>`
- Forwards to laptop via USB Serial at 115,200 baud
- **No sensor processing** - just a simple bridge

**Files:**
```
firmware_ground/
├── platformio.ini     # Build configuration  
└── src/
    └── main.cpp       # Simple LoRa-to-USB bridge
```

**How to flash:**
```bash
cd firmware_ground
pio run --target upload
pio device monitor
```

---

## How They Work Together

```
┌─────────────────────────────┐
│ ROCKET (firmware_rocket/)   │
│  Read sensors → Pack data   │
│  → Transmit via LoRa        │
└──────────────┬──────────────┘
               │
          LoRa 915 MHz
               │
               ↓
┌─────────────────────────────┐
│ GROUND (firmware_ground/)   │
│  Receive LoRa → Forward USB │
└──────────────┬──────────────┘
               │
           USB Serial
               │
               ↓
┌─────────────────────────────┐
│ LAPTOP (ground_station/)    │
│  Parse → Log CSV → Web UI   │
└─────────────────────────────┘
```

**Key Points:**
- Both use **RadioHead library** with matching configuration (915 MHz, SF7)
- Binary packet format must match between firmware and Python parser
- They are **separate programs** flashed to different boards
- Connected only by wireless LoRa radio

---

## 📋 Code Organization

### Rocket Firmware Structure

The rocket firmware keeps everything in one `main.cpp` file for simplicity, with the flight state machine as a separate module:

```cpp
// main.cpp structure:
// 1. Includes (sensors, LoRa, state machine)
// 2. Pin definitions
// 3. Telemetry packet struct
// 4. Global objects (sensors, LoRa, state machine)
// 5. setup() - Initialize everything
// 6. loop() - Read sensors, update state, transmit
```

**Why one file?**
- Simpler for embedded systems
- Easier to understand data flow
- No complex module dependencies
- All code visible in one place

**Flight state machine:**
- Separate `state/flight_state.h` header-only library
- Automatic launch detection (acceleration > 20 m/s²)
- Automatic apogee detection (velocity < -2 m/s)
- Automatic landing detection (altitude stable + low accel)

---

##  Working with PlatformIO

### Opening Projects

**Option 1: Separate Windows**
```bash
# Terminal 1
cd firmware_rocket
code .

# Terminal 2
cd firmware_ground
code .
```

**Option 2: Workspace File (Recommended)**

Create `slug-sight-avionics.code-workspace` at project root:
```json
{
  "folders": [
    {"name": "Rocket Firmware", "path": "firmware_rocket"},
    {"name": "Ground Firmware", "path": "firmware_ground"},
    {"name": "Ground Station", "path": "ground_station"}
  ]
}
```

Then: **File → Open Workspace from File**

### Building and Uploading

```bash
# Build only
cd firmware_rocket
pio run

# Build and upload
pio run --target upload

# Monitor serial output
pio device monitor --baud 115200

# Clean build
pio run --target clean
```

---

## 📦 Dependencies

### Rocket Firmware Libraries (auto-installed by PlatformIO):
- `RadioHead` v1.120 - LoRa communication
- `Adafruit BMP280` v2.6.6 - Barometer
- `Adafruit LSM6DS` v4.6.3 - IMU
- `Adafruit LIS3MDL` v2.1.1 - Magnetometer
- `Adafruit GPS` v1.7.2 - GPS parsing
- `Adafruit BusIO` v1.14.1 - I2C/SPI helper
- `Adafruit Unified Sensor` v1.1.9 - Sensor framework

### Ground Firmware Libraries:
- `RadioHead` v1.120 - LoRa communication (ONLY library needed!)

---

## Summary

1. **`firmware_rocket/`** - Complete rocket flight computer with all sensors
2. **`firmware_ground/`** - Simple LoRa-to-USB bridge
3. Flight state machine preserved and enhanced
4. Old generic template removed
5. All sensors working and transmitting via LoRa
