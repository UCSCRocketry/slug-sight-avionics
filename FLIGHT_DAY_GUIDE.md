# Flight Day Quick Start Guide

## Pre-Flight Setup (10 minutes before launch)

### 1. Hardware Setup
- [ ] Connect receiver Arduino to computer via USB
- [ ] Verify receiver Arduino is powered (LED on)
- [ ] Ensure receiver LoRa antenna is connected
- [ ] Power on transmitter on rocket (verify LED heartbeat)

### 2. Start Ground Station
```bash
cd gds
python advanced_web_gui.py
```

**Expected Output:**
```
INFO - Data logging to: gds/flight_data/slugsight_20251109_120000.csv
INFO - Found GCS Receiver on port: /dev/cu.usbserial-XXX
INFO - Open this URL in your browser: http://127.0.0.1:5000
```

### 3. Open Web Dashboard
1. Open browser to: http://127.0.0.1:5000
2. Verify "Connected" status (green indicator)
3. Check data is updating (numbers changing)

### 4. Pre-Flight Checks
- [ ] **Battery**: VBat > 3.7V (preferably > 4.0V)
- [ ] **Signal**: RSSI > -100 dBm (closer to 0 is better)
- [ ] **GPS**: Wait for GPS fix (may take 30-60 seconds)
- [ ] **Sensors**: Altitude reading reasonable
- [ ] **Data Logging**: Note CSV filename from terminal

## During Flight

### What to Watch
1. **Status Indicator** - Should stay GREEN
2. **RSSI** - Signal strength (will drop at altitude)
3. **Altitude** - Real-time altitude
4. **Max Altitude** - Tracks apogee
5. **GPS** - Track rocket position

### If Connection Lost
- Don't panic! Receiver keeps trying to reconnect
- Data will resume when signal returns
- Check terminal for error messages

## Post-Flight

### 1. Verify Data Saved
```bash
ls -lh gds/flight_data/
```

Should show your flight CSV file with size > 0 bytes

### 2. Quick Data Check
```bash
# View first 10 rows
head -10 gds/flight_data/slugsight_YYYYMMDD_HHMMSS.csv

# Count packets received
wc -l gds/flight_data/slugsight_YYYYMMDD_HHMMSS.csv
```

### 3. Shutdown Ground Station
- Press `Ctrl+C` in terminal
- Wait for "Ground station shutdown complete" message
- CSV file is automatically closed and saved

## Quick Analysis

### Find Apogee
```python
import pandas as pd
df = pd.read_csv('gds/flight_data/YOUR_FILE.csv')
apogee = df['Altitude'].max()
print(f"Apogee: {apogee:.1f} meters")
```

### Plot Flight Profile
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('gds/flight_data/YOUR_FILE.csv')
time = df.index * 0.1  # 10 Hz data

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Altitude
ax1.plot(time, df['Altitude'])
ax1.set_ylabel('Altitude (m)')
ax1.set_title('Flight Profile')
ax1.grid(True)

# Velocity
ax2.plot(time, df['Velocity'])
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Velocity (m/s)')
ax2.grid(True)

plt.tight_layout()
plt.savefig('flight_profile.png')
plt.show()
```

## Troubleshooting

### "Could not find GCS Receiver"
```bash
# List USB devices (macOS)
ls /dev/cu.*

# List USB devices (Linux)
ls /dev/ttyUSB* /dev/ttyACM*
```
Update `ARDUINO_VID_PIDS` in `advanced_web_gui.py` if needed

### No Data Showing
1. Check receiver serial monitor in Arduino IDE
2. Verify baud rate is 115200
3. Check transmitter battery voltage
4. Verify transmitter is sending (LED should blink)

### Dashboard Shows Old Data
- Refresh browser page
- Check WebSocket connection (green status)
- Restart ground station

### CSV File Empty or Missing
- Check terminal for error messages
- Verify write permissions on `gds/flight_data/` directory
- Check disk space

## Data Rate Reference

At 10 Hz transmission rate:
- **10 packets/second**
- **600 packets/minute**
- **1-minute flight** ≈ 600 rows
- **5-minute flight** ≈ 3,000 rows
- **CSV file size** ≈ 150-200 KB per minute

## Emergency Procedures

### If Computer Crashes During Flight
- Partial data should still be in CSV (buffered every 10 packets)
- May lose last ~10 packets

### If Receiver Loses Power
- Restart ground station immediately
- New CSV file will be created
- Old data is safe

### If Signal Lost
- Receiver continues listening
- Data will resume if signal returns
- Check RSSI to estimate range

## Backup Recommendations

Before flight:
```bash
# Create backup directory
mkdir -p ~/rocket_backups

# After flight, immediately backup data
cp gds/flight_data/*.csv ~/rocket_backups/
```

## Contact Info

For issues during flight prep:
- Check `gds/README.md` for detailed troubleshooting
- Check `README.md` for system overview
- Review `CHANGES.md` for recent updates

## Success Checklist

✅ Ground station running and connected  
✅ Web dashboard showing live data  
✅ CSV filename noted for post-flight  
✅ GPS has fix (if needed)  
✅ Battery voltage good (> 3.7V)  
✅ RSSI acceptable (> -100 dBm)  
✅ All readouts changing/updating  

**You're ready to launch! 🚀**
