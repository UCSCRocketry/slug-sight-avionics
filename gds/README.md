# SlugSight Ground Station (GDS)

This directory contains the ground station software for receiving, parsing, displaying, and logging telemetry data from your rocket avionics system.

## Components

### 1. **advanced_web_gui.py** - Main Ground Station Application
- Connects to the Arduino receiver via serial port
- Parses incoming CSV telemetry data
- Displays real-time telemetry in a web dashboard
- Automatically logs all data to CSV files

### 2. **telemetry_parser.py** - Telemetry Parser
- Parses 18-point CSV telemetry string:
  - Pitch, Roll, Yaw
  - Altitude, Velocity
  - Accel X, Y, Z
  - Pressure, IMU Temperature
  - GPS Fix, Satellites
  - GPS Lat, Lon, Altitude, Speed
  - Battery Voltage, RSSI
- Validates and converts data types
- Adds timestamps

### 3. **data_logger.py** - CSV Data Logger
- Automatically creates timestamped CSV files
- Saves all telemetry to `flight_data/` directory
- Configurable precision and buffer settings

## Installation

1. **Install Python dependencies:**
   ```bash
   cd gds
   pip install -r requirements.txt
   ```

2. **Connect your GCS Receiver Arduino** to your computer via USB

## Usage

1. **Start the ground station:**
   ```bash
   python advanced_web_gui.py
   ```

2. **Open the web interface:**
   - Navigate to http://127.0.0.1:5000 in your web browser

3. **View telemetry:**
   - The dashboard will automatically connect to your receiver
   - Real-time data will be displayed
   - All data is automatically logged to `flight_data/` directory

## Data Logging

- **Location:** `gds/flight_data/`
- **Filename Format:** `slugsight_YYYYMMDD_HHMMSS.csv`
- **Contents:** All 18 telemetry fields plus timestamp and packet count
- **Precision:** 6 decimal places for floats

### CSV File Format
Each row contains:
- `timestamp` - ISO format timestamp
- `packet_count` - Sequential packet number
- `Pitch`, `Roll`, `Yaw` - Degrees
- `Altitude` - Meters
- `Velocity` - Meters/second
- `Accel X`, `Accel Y`, `Accel Z` - G-forces
- `Pressure Pa` - Pascals
- `IMU Temp C` - Celsius
- `GPS Fix` - 0=No fix, 1=3D fix
- `GPS Sats` - Number of satellites
- `GPS Lat`, `GPS Lon` - Decimal degrees
- `GPS Alt m` - GPS altitude in meters
- `GPS Speed m/s` - GPS speed in m/s
- `VBat` - Battery voltage
- `RSSI` - Signal strength in dBm

## Configuration

You can customize the data logger by editing the `logger_config` dictionary in `advanced_web_gui.py`:

```python
logger_config = {
    'output_directory': './flight_data',  # Where to save files
    'filename_format': 'slugsight_%Y%m%d_%H%M%S',  # Filename pattern
    'csv': {
        'delimiter': ',',
        'include_header': True,
        'float_precision': 6  # Decimal places
    },
    'buffer_size': 10  # Flush to disk every N packets
}
```

## Troubleshooting

### "Could not find a GCS Receiver Arduino"
- Check USB connection
- Verify the Arduino is recognized by your OS
- Update `ARDUINO_VID_PIDS` in `advanced_web_gui.py` with your Arduino's VID/PID

### No data appearing
- Check serial connection (baud rate should be 115200)
- Verify receiver Arduino is powered and transmitting
- Check receiver Arduino serial monitor for incoming data

### Permission denied on serial port (Linux/Mac)
```bash
sudo usermod -a -G dialout $USER  # Linux
# Then log out and back in
```

On macOS, you may need to give Terminal permission to access USB devices in System Preferences > Security & Privacy.

## Flight Day Checklist

1. ✅ Verify all hardware connections
2. ✅ Start ground station: `python advanced_web_gui.py`
3. ✅ Open browser to http://127.0.0.1:5000
4. ✅ Verify data is being received (check status indicator)
5. ✅ Note the CSV filename for post-flight analysis
6. ✅ After flight, check `flight_data/` for logged data

## Post-Flight Analysis

The CSV files can be analyzed with:
- Python (pandas, matplotlib)
- Excel/Google Sheets
- MATLAB
- Any CSV-compatible tool

Example Python analysis:
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load flight data
df = pd.read_csv('flight_data/slugsight_20250101_120000.csv')

# Plot altitude vs time
plt.figure(figsize=(12, 6))
plt.plot(df.index * 0.1, df['Altitude'])  # 10 Hz data rate
plt.xlabel('Time (seconds)')
plt.ylabel('Altitude (m)')
plt.title('Flight Altitude Profile')
plt.grid(True)
plt.show()
```
