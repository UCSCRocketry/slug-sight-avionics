# SlugSight Telemetry System

Complete rocket telemetry system with LoRa transmission, ground station, and data logging for rocket flight data acquisition.

## System Overview

This system consists of three main components:

1. **Transmitter (TX)** - Arduino/Feather M4 on the rocket
2. **Receiver (RX)** - Arduino receiver at ground station
3. **Ground Station Software (GDS)** - Python software for visualization and data logging

### Data Flow

```
Rocket (TX) → LoRa → Ground Receiver (RX) → USB → Computer (GDS) → CSV Files
```

## Hardware Components

### Transmitter (On Rocket)
- Adafruit Feather M4 Express
- RFM95W LoRa Radio (915 MHz)
- LSM6DSOX IMU (accelerometer/gyroscope)
- LIS3MDL Magnetometer
- BMP280 Barometer
- GPS Module (115200 baud)

### Receiver (Ground Station)
- Arduino Uno/Nano (or compatible)
- RFM95W LoRa Radio (915 MHz)

## Telemetry Data (18 Fields)

The system transmits 17 fields from the rocket, and the receiver adds RSSI:

| # | Field | Unit | Description |
|---|-------|------|-------------|
| 1-3 | Pitch, Roll, Yaw | degrees | Orientation angles |
| 4 | Altitude | meters | Barometric altitude (MSL) |
| 5 | Velocity | m/s | Vertical velocity |
| 6-8 | Accel X, Y, Z | g | 3-axis acceleration |
| 9 | Pressure | Pa | Atmospheric pressure |
| 10 | IMU Temp | °C | IMU temperature |
| 11 | GPS Fix | 0/1 | GPS fix status |
| 12 | GPS Sats | count | Number of satellites |
| 13-14 | GPS Lat, Lon | degrees | GPS coordinates |
| 15 | GPS Altitude | meters | GPS altitude |
| 16 | GPS Speed | m/s | GPS ground speed |
| 17 | VBat | volts | Battery voltage |
| 18 | RSSI | dBm | Radio signal strength (added by RX) |

## Quick Start

### 1. Upload Arduino Code

**Transmitter:**
```bash
# Open slugsight_sensors_tx/slugsight_sensors_tx.ino in Arduino IDE
# Select board: Adafruit Feather M4 Express
# Upload to rocket Feather M4
```

**Receiver:**
```bash
# Open slugsight_sensors_rx/slugsight_sensors_rx.ino in Arduino IDE
# Select board: Arduino Uno (or your receiver board)
# Upload to receiver Arduino
```

### 2. Install Ground Station Software

```bash
cd gds
pip install -r requirements.txt
```

### 3. Run Ground Station

```bash
cd gds
python advanced_web_gui.py
```

Then open http://127.0.0.1:5000 in your web browser.

## Ground Station Features

- **Real-time Dashboard** - Live telemetry visualization
- **Automatic Data Logging** - All data saved to CSV files
- **Flight Metrics** - Max altitude, max G-force tracking
- **GPS Tracking** - GPS position and fix status
- **Battery Monitoring** - Battery voltage and percentage
- **Signal Quality** - RSSI monitoring
- **Attitude Display** - Pitch, roll, yaw gauges
- **Time-series Charts** - Historical data plots

## Data Logging

All telemetry is automatically saved to CSV files in the `gds/flight_data/` directory.

**Filename format:** `slugsight_YYYYMMDD_HHMMSS.csv`

**CSV Format:**
```csv
timestamp,packet_count,Pitch,Roll,Yaw,Altitude,Velocity,Accel X,Accel Y,Accel Z,Pressure Pa,IMU Temp C,GPS Fix,GPS Sats,GPS Lat,GPS Lon,GPS Alt m,GPS Speed m/s,VBat,RSSI
2025-11-09T12:00:00.123,0,5.2,-3.1,45.8,125.5,15.3,0.5,0.2,9.8,101325.0,22.5,1,8,37.123456,-122.345678,130.2,12.5,3.85,-95
...
```

## Configuration

### Transmitter Settings (`slugsight_sensors_tx.ino`)
- **Frequency:** 915 MHz (US) - Change `RF95_FREQ` for your region
- **Data Rate:** Bw500Cr45Sf128 (fastest)
- **TX Power:** 23 dBm (max)
- **Update Rate:** 10 Hz (100 Hz sensor fusion)

### Ground Station Settings (`advanced_web_gui.py`)
- **Serial Baud:** 115200
- **Output Directory:** `gds/flight_data/`
- **CSV Precision:** 6 decimal places
- **Buffer Size:** 10 packets (flush interval)

## Post-Flight Analysis

Use Python to analyze your flight data:

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
apogee_time = apogee_idx * 0.1
print(f"Apogee: {apogee_altitude:.1f}m at {apogee_time:.1f}s")

# Calculate max acceleration
max_g = df[['Accel X', 'Accel Y', 'Accel Z']].apply(
    lambda row: (row**2).sum()**0.5, axis=1
).max()
print(f"Max G-Force: {max_g:.1f}g")
```

## Directory Structure

```
slugsight_telemetry/
├── README.md                          # This file
├── slugsight_sensors_tx/              # Transmitter code (rocket)
│   └── slugsight_sensors_tx.ino      # Arduino code for TX
├── slugsight_sensors_rx/              # Receiver code (ground)
│   └── slugsight_sensors_rx.ino      # Arduino code for RX
└── gds/                               # Ground station software
    ├── README.md                      # GDS documentation
    ├── requirements.txt               # Python dependencies
    ├── advanced_web_gui.py            # Main ground station app
    ├── telemetry_parser.py            # CSV parser
    ├── data_logger.py                 # Data logging
    ├── test_integration.py            # Test script
    └── flight_data/                   # Logged flight data (created automatically)
```

## Troubleshooting

### No Serial Port Found
- Check USB connection
- Verify Arduino drivers installed
- Update `ARDUINO_VID_PIDS` in `advanced_web_gui.py`

### No Data Received
- Check receiver Arduino serial monitor (should show CSV data)
- Verify baud rate is 115200
- Check LoRa antenna connections
- Verify transmitter is powered on

### Web Dashboard Not Loading
- Check Flask is installed: `pip install flask flask-sock`
- Verify port 5000 is not in use
- Check browser console for errors

### GPS Not Getting Fix
- Ensure clear view of sky
- GPS can take 30-60 seconds for initial fix
- Check GPS antenna connection

## Safety Notes

⚠️ **Important Safety Information:**

1. **Radio Regulations** - Verify 915 MHz ISM band is legal in your region
2. **Flight Safety** - Follow all NAR/TRA safety codes
3. **Range Testing** - Test LoRa range before flight
4. **Backup Systems** - Always use backup recovery systems
5. **Battery Safety** - Monitor LiPo battery voltage

## License

MIT License - See individual files for details

## Support

For issues or questions, please open an issue on GitHub.

## Credits

Developed for the UCSC Rocket Team (SlugSight Avionics)
