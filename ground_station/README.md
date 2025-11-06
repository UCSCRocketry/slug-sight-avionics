# Ground Station - Quick Start

## Running the Ground Station

### With Hardware (Ground Feather M4 Connected):

1. **Connect ground Feather M4 via USB**

2. **Find your serial port:**
   ```bash
   # macOS
   ls /dev/cu.usbmodem*
   
   # Linux
   ls /dev/ttyACM*
   
   # Windows (PowerShell)
   dir COM*
   ```

3. **Update configuration:**
   Edit `config/ground_config.yaml`:
   ```yaml
   serial:
     serial_port: "/dev/cu.usbmodem14201"  # ← Your port here
   ```

4. **Activate virtual environment and run:**
   ```bash
   source ../.venv/bin/activate
   python app.py
   ```

5. **Open dashboard:**
   ```
   http://localhost:8080
   ```

---

### Without Hardware (Demo/Testing):

You can run the ground station without hardware connected. The web interface will work, but you won't receive telemetry data.

1. **Activate virtual environment and run:**
   ```bash
   source ../.venv/bin/activate
   python app.py
   ```

2. **You'll see a warning:**
   ```
   ⚠️  HARDWARE NOT CONNECTED
   Ground Feather M4 is not connected via USB.
   The web interface will still run for testing.
   ```

3. **Open dashboard anyway:**
   ```
   http://localhost:8080
   ```

---

## Port Already in Use?

If you see:
```
Port 8080 is in use by another program
```

**Option 1:** Stop the other program using port 8080

**Option 2:** Change the port in `config/ground_config.yaml`:
```yaml
web:
  port: 9090  # Or any other available port
```

---

## Available Serial Ports

Currently available on your system:
```
/dev/cu.Bluetooth-Incoming-Port
/dev/cu.BoseFlexSESoundLink
/dev/cu.debug-console
```

When you plug in the ground Feather M4, you'll see a new port like:
```
/dev/cu.usbmodem14201  ← Ground Feather M4
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"
Install dependencies:
```bash
# From project root
source .venv/bin/activate
pip install -r requirements.txt
```

### "Serial port not found"
- Ground Feather M4 not plugged in
- USB cable doesn't support data (try different cable)
- Wrong port in config file

### "Permission denied" (Linux)
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

---

## Quick Commands

```bash
# Activate environment
source ../.venv/bin/activate

# Run ground station
python app.py

# Check available ports
ls /dev/cu.*          # macOS
ls /dev/ttyACM*       # Linux

# Stop ground station
Ctrl+C
```

---

## Data Files

CSV files saved to:
```
data/flights/2025-11-06_14-16-09.csv
```

Each run creates a new timestamped file.
