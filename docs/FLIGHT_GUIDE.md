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

# Activate venv (macOS/Linux)
source venv/bin/activate

# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

python slugsight_gds.py
```

**Expected Output:**
```
INFO - Data logging to: .../gds/flight_data/slugsight_20251109_120000.csv
INFO - Found GCS Receiver on port: /dev/cu.usbserial-XXX
INFO - Open this URL in your browser: [http://127.0.0.1:8080](http://127.0.0.1:8080)
```

### 3. Open Web Dashboard
1. Open browser to: [http://127.0.0.1:8080](http://127.0.0.1:8080)
2. Verify "Connected" status (green indicator)
3. Check data is updating (numbers changing)

### 4. Pre-Flight Checks
- [ ] **Battery**: VBat > 3.7V (Appears immediately on boot)
- [ ] **Signal**: RSSI > -100 dBm (closer to 0 is better)
- [ ] **GPS**: Wait for GPS fix (may take 30-60 seconds). Fix status will update from '0' to '1' when locked.
- [ ] **Sensors**: Altitude reading reasonable
- [ ] **Data Logging**: Confirm Ground Station is recording (see terminal). **Onboard SD logging** will start automatically once GPS fix is acquired.

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
# On Windows: dir gds\flight_data\
```

Should show your flight CSV file with size > 0 bytes

### 2. Quick Data Check
```bash
# View first 10 rows (macOS/Linux)
head -10 gds/flight_data/slugsight_YYYYMMDD_HHMMSS.csv

# View first 10 rows (Windows PowerShell)
Get-Content gds/flight_data/slugsight_YYYYMMDD_HHMMSS.csv -Head 10
```

### 3. Shutdown Ground Station
- Press `Ctrl+C` in terminal
- Wait for "Ground station shutdown complete" message
- CSV file is automatically closed and saved

## Troubleshooting

### "Could not find GCS Receiver"
**1. macOS/Linux:**
```bash
ls /dev/cu.*
ls /dev/ttyUSB* /dev/ttyACM*
```

**2. Windows:**
- Open Device Manager > Ports (COM & LPT)
- Look for "USB Serial Device" or "Arduino"
- Or run this Python command to list all ports:
```bash
python -m serial.tools.list_ports
```

Update `ARDUINO_VID_PIDS` in `gds/slugsight_gds.py` if needed.

### No Data Showing
1. Check receiver serial monitor in Arduino IDE
2. Verify baud rate is 115200
3. Check transmitter battery voltage
4. Verify transmitter is sending (LED should blink)

### CSV File Empty or Missing
- Check terminal for error messages
- Verify write permissions on `gds/flight_data/` directory
- Check disk space

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
