
## Hardware Components & Wiring

### 1. Transmitter (On Rocket)
* **Board**: Adafruit Feather M4 Express
* **Power**: Lithium Ion Battery (3.7V Nominal, JST Connector)
* **Mounting**: Vertical (Y-Axis pointing Up/Down towards nose cone)

| Component | Interface | Pin / Connection |
| :--- | :--- | :--- |
| **RFM95W LoRa** | SPI | CS=10, RST=11, INT=12 |
| **Micro SD** | SPI | CS=13 |
| **LSM6DSOX (IMU)** | SPI | CS=9 |
| **BMP280 (Baro)** | SPI | CS=6 |
| **LIS3MDL (Mag)** | SPI | CS=5 |
| **GPS Module** | UART | Serial1 (TX/RX) |
| **Battery Sense** | Analog | A6 (Voltage Divider) |

### 2. Receiver (Ground Station)
* **Board**: Arduino Uno / Nano

| Component | Interface | Pin / Connection |
| :--- | :--- | :--- |
| **RFM95W LoRa** | SPI | CS=10, RST=9, INT=2 |
| **Host PC** | USB | Serial (115200 baud) |

## Configuration Reference

### LoRa Radio Settings
These settings must match exactly on both Transmitter and Receiver:
* **Frequency**: 915.0 MHz (ISM Band)
* **Bandwidth**: 500 kHz
* **Coding Rate**: 4/5
* **Spreading Factor**: 128
* **TX Power**: 23 dBm (Max Power)

### Ground Station Settings
* **Baud Rate**: 115200
* **Update Rate**: 10 Hz
* **CSV Buffer**: 10 packets (flushed to disk automatically)

## Data Logging & Redundancy Strategy

This system implements a **Dual-Redundant** logging strategy to ensure no flight data is lost:

1.  **Ground Recording (Primary)**: The Ground Station (GDS) automatically saves all received telemetry packets to CSV files on the laptop.
    * **Time Source**: Laptop Network Time (UTC). Records immediately upon connection.
    * **Location**: `gds/flight_data/`
    * **Filename**: `slugsight_YYYYMMDD_HHMMSS.csv`

2.  **Onboard SD Card (Backup)**: The transmitter (TX) writes every data packet to an onboard Micro SD card **before** transmission. This creates a high-fidelity log even if the radio link fails.
    * **Time Source**: GPS Time (UTC). Logging waits for a 3D GPS lock to ensure the timestamp is correct.
    * **Location**: Root of SD card.
    * **Filename**: `LOGxx.CSV` (increments automatically).



## Calibration Workflow (L2/L3 Rockets)

Since rotating a large rocket on the launch pad is often impossible, use this "Calibrate Once" method. The calibration offsets are saved into the code itself, carrying over permanently as long as the avionics sled layout does not change.

1.  **Prepare Sled**: Assemble your avionics sled with all batteries, switches, and metal hardware attached.
2.  **Enable Calibration Mode**: In `slugsight_tx.ino`, set `#define CALIBRATION_MODE true`.
3.  **Upload & Rotate**: Upload the code and open the Serial Monitor. Rotate the sled in a figure-8 motion for 30-60 seconds.
4.  **Copy Offsets**: Record the `X`, `Y`, and `Z` offset values printed to the Serial Monitor.
5.  **Hardcode & Finalize**:
    * Paste the values into the `MAG_OFFSET_X`, `Y`, `Z` variables in the code.
    * Set `#define CALIBRATION_MODE false`.
    * Re-upload the code.
6.  **Ready to Fly**: The rocket is now permanently calibrated for its own magnetic signature.

## Telemetry Data Specifications

The system transmits 17 fields from the rocket, and the receiver adds RSSI (Received Signal Strength Indicator) for a total of 18 fields.

| # | Field | Unit | Description |
| :--- | :--- | :--- | :--- |
| 1-3 | Pitch, Roll, Yaw | degrees | Orientation angles (Sensor Fusion) |
| 4 | Altitude | meters | Barometric altitude (MSL) |
| 5 | Velocity | m/s | Vertical velocity |
| 6-8 | Accel X, Y, Z | g | 3-axis acceleration |
| 9 | Pressure | Pa | Atmospheric pressure |
| 10 | IMU Temp | C | IMU temperature |
| 11 | GPS Fix | 0/1 | GPS fix status |
| 12 | GPS Sats | count | Number of satellites |
| 13-14 | GPS Lat, Lon | degrees | GPS coordinates |
| 15 | GPS Altitude | meters | GPS altitude |
| 16 | GPS Speed | m/s | GPS ground speed |
| 17 | VBat | volts | Lithium Ion Battery voltage |
| 18 | RSSI | dBm | Radio signal strength (added by RX) |

### Data Packet & CSV Format

All telemetry is automatically saved to CSV files in the `gds/flight_data/` directory.

**Filename format:** `slugsight_YYYYMMDD_HHMMSS.csv`

**CSV Format:**
```csv
timestamp,packet_count,Pitch,Roll,Yaw,Altitude,Velocity,Accel X,Accel Y,Accel Z,Pressure Pa,IMU Temp C,GPS Fix,GPS Sats,GPS Lat,GPS Lon,GPS Alt m,GPS Speed m/s,VBat,RSSI
2025-11-09T12:00:00.123,0,5.2,-3.1,45.8,125.5,15.3,0.5,0.2,9.8,101325.0,22.5,1,8,37.123456,-122.345678,130.2,12.5,3.85,-95
...
```




## Post-Flight Analysis

Use Python to analyze your flight data. Ensure `pandas` and `matplotlib` are installed.

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load flight data
df = pd.read_csv('gds/flight_data/slugsight_20251109_120000.csv')

# Plot altitude profile
plt.figure(figsize=(12, 6))
time_sec = df.index * 0.1  # 10 Hz data rate
plt.plot(time_sec, df['Altitude'])
plt.xlabel('Time (seconds)')
plt.ylabel('Altitude (meters)')
plt.title('Flight Altitude Profile')
plt.grid(True)
plt.show()

# Find apogee
apogee_idx = df['Altitude'].idxmax()
apogee_altitude = df.loc[apogee_idx, 'Altitude']
print(f"Apogee: {apogee_altitude:.1f}m")

# Calculate max acceleration
max_g = df[['Accel X', 'Accel Y', 'Accel Z']].apply(
    lambda row: (row**2).sum()**0.5, axis=1
).max()
print(f"Max G-Force: {max_g:.1f}g")
```








### Data Flow Architecture

```text
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
