# SlugSight Telemetry System

Complete rocket telemetry system with LoRa transmission, ground station, and dual-redundant data logging for rocket flight data acquisition.

## System Overview

This system consists of three main components:

1. **Transmitter (TX)** - Arduino/Feather M4 on the rocket (collects data, logs to SD, transmits via LoRa)
2. **Receiver (RX)** - Arduino receiver at ground station (receives LoRa, forwards to USB)
3. **Ground Station Software (GDS)** - Python software for real-time visualization and recording

### Data Flow

```
ROCKET HARDWARE (SPI & UART)
┌─────────────────────────────────────────────────────────────────────────┐
│ [Reyax RYS352A]                                                         │
│ (GPS Module)                                                            │
│       |                  [LSM6DSOX]             [SD Card]               |
│     (UART)              (Accel/Gyro)           (Backup Log)             |
│       |                      |                      |                   │
│       v                      v    (SPI Data Bus)    ^                   │
│ [Feather M4 Express] <==+====+===========+==========+========+          │
│ (Rocket MCU)            ^                ^                   v          │
│                         |                |                   |          │
│                     [BMP280]         [LIS3MDL]          [RFM9x LoRa]    │
│                    (Barometer)     (Magnetometer)           (TX)        |
│                                                              │          |
└──────────────────────────────────────────────────────────────:──────────┘
                                                               :
                                                      (915 MHz LoRa Link)
 GROUND STATION                                                :
┌──────────────────────────────────────────────────────────────:──────────┐
│                                                              v          │
│                                                         [RFM9x LoRa]    │
│                                                             (RX)        │
│                                                              |          │
│                                                            (SPI)        │
│                                                              |          │
│                                                              v          │
│ [CSV File] <──(Write)── [Python GDS] <──(Serial/USB)── [Arduino Uno R3] │
│ (Primary Log)           (Software)                     (Ground MCU)     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Hardware Components & Wiring

### 1. Transmitter (On Rocket)
**Board:** Adafruit Feather M4 Express
**Mounting:** Vertical (Y-Axis pointing Up/Down towards nose cone)

| Component | Interface | Pin / Connection |
|-----------|-----------|------------------|
| **RFM95W LoRa** | SPI | CS=10, RST=11, INT=12 |
| **Micro SD** | SPI | CS=13 |
| **LSM6DSOX (IMU)** | SPI | CS=9 |
| **BMP280 (Baro)** | SPI | CS=6 |
| **LIS3MDL (Mag)** | SPI | CS=5 |
| **GPS Module** | UART | Serial1 (TX/RX) |
| **Battery Sense** | Analog | A6 (Voltage Divider) |

### 2. Receiver (Ground Station)
**Board:** Arduino Uno / Nano

| Component | Interface | Pin / Connection |
|-----------|-----------|------------------|
| **RFM95W LoRa** | SPI | CS=10, RST=9, INT=2 |
| **Host PC** | USB | Serial (115200 baud) |

## Calibration Workflow (L2/L3 Rockets)
Since rotating a large rocket on the launch pad is impossible, use this "Calibrate Once" method.
The calibration offsets are saved into the code itself, carrying over permanently as long as the sled layout doesn't change.

1.  **Prepare Sled:** Assemble your avionics sled with all batteries, switches, and metal hardware attached.
2.  **Enable Calibration Mode:** In `slugsight_tx.ino`, set `#define CALIBRATION_MODE true`.
3.  **Upload & Rotate:** Upload code. Open Serial Monitor. Rotate the sled in a figure-8 motion for 30-60 seconds.
4.  **Copy Offsets:** Write down the `X`, `Y`, and `Z` offset values printed to the Serial Monitor.
5.  **Hardcode & Finalize:**
    - Paste the values into the `MAG_OFFSET_X`, `Y`, `Z` variables in the code.
    - Set `#define CALIBRATION_MODE false`.
    - Re-upload the code.
6.  **Ready to Fly:** The rocket is now permanently calibrated for its own magnetic signature.

## Telemetry Data (18 Fields)

The system transmits 17 fields from the rocket, and the receiver adds RSSI:

| # | Field | Unit | Description |
|---|-------|------|-------------|
| 1-3 | Pitch, Roll, Yaw | degrees | Orientation angles (Sensor Fusion) |
| 4 | Altitude | meters | Barometric altitude (MSL) |
| 5 | Velocity | m/s | Vertical velocity |
| 6-8 | Accel X, Y, Z | g | 3-axis acceleration |
| 9 | Pressure | Pa | Atmospheric pressure |
| 10 | IMU Temp | \u00B0C | IMU temperature |
| 11 | GPS Fix | 0/1 | GPS fix status |
| 12 | GPS Sats | count | Number of satellites |
| 13-14 | GPS Lat, Lon | degrees | GPS coordinates |
| 15 | GPS Altitude | meters | GPS altitude |
| 16 | GPS Speed | m/s | GPS ground speed |
| 17 | VBat | volts | Battery voltage |
| 18 | RSSI | dBm | Radio signal strength (added by RX) |

## Quick Start

### 1. Upload Firmware

**Transmitter:**
```bash
# Open firmware/slugsight_tx/slugsight_tx.ino in Arduino IDE
# Select board: Adafruit Feather M4 Express
# Upload to rocket Feather M4
```

**Receiver:**
```bash
# Open firmware/slugsight_rx/slugsight_rx.ino in Arduino IDE
# Select board: Arduino Uno (or your receiver board)
# Upload to receiver Arduino
```

### 2. Install Ground Station Software

It is recommended to use a virtual environment:

```bash
cd gds

# Create virtual environment
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# OR (Windows CMD)
venc\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Ground Station

```bash
cd gds
source venv/bin/activate  # Ensure venv is active
python slugsight_gds.py
```

Then open [http://127.0.0.1:8080](http://127.0.0.1:8080) in your web browser.

## Data Logging & Redundancy Strategy

This system implements a **Dual-Redundant** logging strategy to ensure no flight data is lost:

### 1. Ground Recording (Primary)
The Ground Station (GDS) automatically saves all received telemetry packets to CSV files on your laptop.
- **Time Source:** Laptop Network Time (UTC). Records **immediately** upon connection, regardless of GPS lock.
- **Location:** `gds/flight_data/`
- **Filename:** `slugsight_YYYYMMDD_HHMMSS.csv`

### 2. Onboard SD Card (Backup)
The transmitter (TX) writes every data packet to an onboard Micro SD card **before** transmission. This creates a complete, high-fidelity log of the flight even if the radio link cuts out or the ground station fails.
- **Time Source:** GPS Time (UTC). Logging **waits for a 3D GPS lock** to ensure the file timestamp is correct.
- **Location:** Root of SD card
- **Filename:** `LOGxx.CSV` (increments automatically)

**Note:** Telemetry (Battery, IMU) is transmitted immediately on power-up. SD logging starts silently in the background once GPS time is acquired.

## License

This project is dual-licensed:

1. **Firmware (`firmware/`)**: The Arduino transmitter and receiver code is licensed under the **GPLv3** (GNU General Public License v3.0) to comply with the RadioHead library dependency.
2. **Ground Station (`gds/`)**: The Python ground station software and documentation are licensed under the **MIT License**.

See `LICENSE-FIRMWARE` and `LICENSE-SOFTWARE` for full details.

## Support

For issues or questions, please open an issue on GitHub.

## Credits

Developed for the UCSC Rocket Team (SlugSight Avionics)
