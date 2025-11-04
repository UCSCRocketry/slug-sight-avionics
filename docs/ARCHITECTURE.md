# Slug Sight Avionics - System Architecture

**Two Feather M4 Express boards with RadioHead LoRa communication**

## Hardware: Adafruit Feather M4 Express (ATSAMD51 @ 120MHz)

---

## ROCKET CONFIGURATION (Transmitter)

### Sensors Connected:

#### BMP280 Barometer - **SPI**
- **Datasheet**: https://cdn-shop.adafruit.com/datasheets/BST-BMP280-DS001-11.pdf
- **Interface**: SPI (faster than I2C)
- **I2C Address**: 0x77 (primary) or 0x76 (alternate)
- **Pins**: 
  - CS: Pin 10
  - MOSI, MISO, SCK: Hardware SPI

#### LSM6DSOX IMU (6-axis) - **I2C**
- **Function**: 3-axis accelerometer + 3-axis gyroscope
- **I2C Address**: 0x6A (primary) or 0x6B (if SDO high)
- **Pins**: SDA (22), SCL (23)
- **Range**: ±16G accel, ±2000 dps gyro

#### LIS3MDL Magnetometer - **I2C**
- **Function**: 3-axis magnetic field
- **I2C Address**: 0x1C (primary) or 0x1E (if SDO high)  
- **Pins**: SDA (22), SCL (23) - shared I2C bus
- **Range**: ±4 Gauss

#### Adafruit Ultimate GPS - **UART**
- **Function**: 99-channel GNSS, 10 Hz updates
- **Interface**: Serial1 (Hardware UART)
- **Baud**: 9600 (default) or 57600
- **Pins**: 
  - GPS TX → Feather RX (Pin 0)
  - GPS RX → Feather TX (Pin 1)

#### RFM95W LoRa Radio - **SPI**
- **Frequency**: 915 MHz (US) or 868 MHz (EU)
- **Library**: RadioHead RH_RF95
- **Pins**:
  - CS: Pin 8
  - RST: Pin 4
  - IRQ (G0): Pin 3
  - MOSI, MISO, SCK: Hardware SPI (shared with BMP280)

---

## GROUND CONFIGURATION (Receiver Bridge)

### Hardware:
- **Feather M4 Express** #2
- **RFM95W LoRa Radio** - same config as rocket
- **USB Serial** → Laptop

### Function:
1. Receive LoRa packets from rocket
2. Forward raw packets to laptop via USB Serial
3. Acts as LoRa-to-USB bridge

### Pins (Ground Feather):
- **LoRa SPI**:
  - CS: Pin 8
  - RST: Pin 4  
  - IRQ: Pin 3
- **USB Serial**: Native USB (auto-configured)

---

## LAPTOP GROUND STATION

### Software:
- **Python 3.9+**
- **Flask web server** on localhost:5000
- **Serial connection** to ground Feather M4

### Functions:
1. Read packets from ground Feather via USB serial
2. Parse telemetry data
3. Log to CSV file with timestamps
4. Display live data on web interface

---

## Data Flow:

```
┌─────────────────────────────────────────────────────────────┐
│ ROCKET FEATHER M4                                           │
│  ├─ BMP280 (SPI) ────┐                                      │
│  ├─ LSM6DSOX (I2C) ──┤                                      │
│  ├─ LIS3MDL (I2C) ───┼──→ Telemetry Packet ──→ RFM95W LoRa │
│  └─ GPS (UART) ──────┘                                      │
└───────────────────────────────────────────┬─────────────────┘
                                            │
                                    LoRa 915 MHz
                                     (wireless)
                                            │
                                            ↓
┌─────────────────────────────────────────────────────────────┐
│ GROUND FEATHER M4                                           │
│   RFM95W LoRa ──→ Receive ──→ USB Serial                   │
└───────────────────────────────────────────┬─────────────────┘
                                            │
                                       USB Cable
                                            │
                                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAPTOP (Python GDS)                                         │
│   ├─ Read USB Serial (/dev/cu.usbmodem...)                 │
│   ├─ Parse telemetry packets                               │
│   ├─ Log to CSV file                                        │
│   └─ Flask web UI → http://localhost:5000                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Communication Protocol:

### Packet Structure (Binary, 74 bytes):
| Field | Type | Size | Unit |
|-------|------|------|------|
| timestamp | float32 | 4 | seconds |
| altitude | float32 | 4 | meters |
| pressure | float32 | 4 | pascals |
| temperature | float32 | 4 | celsius |
| accel_x/y/z | float32 | 12 | m/s² |
| gyro_x/y/z | float32 | 12 | deg/s |
| mag_x/y/z | float32 | 12 | μT |
| gps_lat/lon/alt | float32 | 12 | deg/deg/m |
| state | uint8 | 1 | enum |
| checksum | uint16 | 2 | CRC16 |

### RadioHead Configuration:
- **Frequency**: 915.0 MHz
- **TX Power**: 23 dBm (max for RFM95W)
- **Spreading Factor**: 7 (fastest)
- **Bandwidth**: 125 kHz
- **Coding Rate**: 4/5
- **Data Rate**: ~10 packets/sec (100ms interval)

---

## Timing Analysis:

### Rocket Loop (60-100 Hz capable):
```
Read BMP280 (SPI):      ~0.5 ms
Read LSM6DSOX (I2C):    ~1.5 ms
Read LIS3MDL (I2C):     ~1.0 ms
Parse GPS (UART):       ~0.1 ms (async)
Build packet:           ~0.2 ms
Send LoRa:             ~50-80 ms (non-blocking)
-----------------------------------------
Total per loop:        ~3-5 ms (plus LoRa TX)
```

**Verdict**: ✅ No timing issues. Can easily run at 50-100 Hz.

---

## File Structure:

```
slug-sight-avionics/
├── firmware_rocket/          # Rocket Feather M4 (transmitter)
│   ├── src/
│   │   └── main.cpp         # Rocket main code
│   └── platformio.ini       # Rocket build config
│
├── firmware_ground/          # Ground Feather M4 (receiver)
│   ├── src/
│   │   └── main.cpp         # Ground bridge code
│   └── platformio.ini       # Ground build config
│
├── ground_station/           # Laptop Python GDS
│   ├── main.py              # Flask web server
│   ├── serial_reader.py     # Read from ground Feather
│   ├── data/
│   │   ├── telemetry_parser.py
│   │   └── data_logger.py
│   └── templates/
│       └── dashboard.html   # Web UI
│
├── config/
│   ├── rocket_config.yaml   # Rocket settings
│   └── ground_config.yaml   # Ground station settings
│
└── docs/
    ├── ARCHITECTURE.md      # This file
    ├── hardware.md
    └── setup.md
```

---

## Benefits of This Architecture:

### ✅ Advantages:
1. **Separation of Concerns**: Rocket only worries about sensors + transmission
2. **Reliable**: Ground Feather handles LoRa complexity, laptop just reads serial
3. **Hot-swap**: Can unplug/reconnect laptop without affecting LoRa link
4. **Debugging**: Can monitor ground Feather serial for diagnostics
5. **Portable**: Same ground Feather setup works for any rocket

### 📊 Performance:
- **Range**: 2-5 km line-of-sight (LoRa)
- **Data Rate**: 10 packets/sec (adjustable)
- **Latency**: ~100-150 ms (LoRa + serial + parsing)
- **Reliability**: CRC16 checksum, packet numbering

---

## Next Steps:

1. ✅ Wire up sensors to rocket Feather M4
2. ✅ Upload firmware to rocket Feather
3. ✅ Wire up LoRa to ground Feather M4  
4. ✅ Upload bridge firmware to ground Feather
5. ✅ Connect ground Feather to laptop via USB
6. ✅ Run Python ground station
7. ✅ Open http://localhost:5000 in browser
8. 🚀 **Launch!**
