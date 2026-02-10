# SlugSight Telemetry System

Complete rocket telemetry system with LoRa transmission, ground station, and dual-redundant data logging for rocket flight data acquisition.

## System Overview

This system consists of three main components:

1.  **Transmitter (TX)**: Arduino/Feather M4 on the rocket. Collects sensor data, logs to the onboard SD card, and transmits telemetry via LoRa.
2.  **Receiver (RX)**: Arduino receiver at the ground station. Receives LoRa packets and forwards them via USB to the host computer.
3.  **Ground Station Software (GDS)**: Python software for real-time visualization, dashboard display, and data recording.


### Key Features
* **Real-time Dashboard**: Live visualization of altitude, orientation, and signal strength.
* **Dual-Redundant Logging**: Saves data to both the Ground Station (CSV) and Onboard SD Card simultaneously.
* **GPS Tracking**: Live latitude/longitude streaming for recovery.
* **Flight Metrics**: Automatic tracking of Apogee and Max G-Force.
* **Battery Monitoring**: Real-time voltage monitoring for the onboard Lithium Ion battery.

## Quick Start

### 1. Upload Firmware

**Transmitter:**
1.  Open `firmware/slugsight_tx/slugsight_tx.ino` in Arduino IDE.
2.  Select board: **Adafruit Feather M4 Express**.
3.  Upload to the rocket Feather M4.

**Receiver:**
1.  Open `firmware/slugsight_rx/slugsight_rx.ino` in Arduino IDE.
2.  Select board: **Arduino Uno** (or your receiver board).
3.  Upload to the receiver Arduino.

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

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Ground Station

```bash
python slugsight_gds.py
```

Once running, open **http://127.0.0.1:8080** in your web browser.

### Testing & Verification

Before heading to the launch site, run the integration test suite. This verifies that the parser handles data correctly and that CSV logging is working.

```bash
python test_integration.py
```

**Expected Output**: `OK` (All tests passed).



## Directory Structure

The project is organized as follows:

```text
slugsight_telemetry/
├── README.md                          # Main system documentation
├── FLIGHT_GUIDE.md                    # Flight day checklist and procedures
├── firmware/                          # Arduino Source Code
│   ├── slugsight_tx/                  # Rocket Transmitter Code
│   │   └── slugsight_tx.ino
│   └── slugsight_rx/                  # Ground Receiver Code
│       └── slugsight_rx.ino
└── gds/                               # Ground Station Software
    ├── requirements.txt               # Python dependencies
    ├── slugsight_gds.py               # Main Ground Station Application
    └── flight_data/                   # Telemetry Logs (Auto-generated)
        └── slugsight_YYYYMMDD_...csv
```


## Safety Notes

**IMPORTANT SAFETY INFORMATION:**

1.  **Radio Regulations**: Verify the 915 MHz ISM band is legal for use in your specific region.
2.  **Flight Safety**: Adhere to all NAR/TRA safety codes and local regulations.
3.  **Range Testing**: Always perform a ground range test of the LoRa system before flight.
4.  **Backup Systems**: Avionics should be considered a secondary payload. Always use backup recovery systems (e.g., motor ejection or redundant altimeters).
5.  **Battery Safety**: Monitor **Lithium Ion** battery voltage closely. Do not fly if voltage is below 3.7V. Ensure batteries are secured and protected from impact.

## License

This project is dual-licensed:

1.  **Firmware (`firmware/`)**: The Arduino transmitter and receiver code is licensed under the **GPLv3** (GNU General Public License v3.0) to comply with the RadioHead library dependency.
2.  **Ground Station (`gds/`)**: The Python ground station software and documentation are licensed under the **MIT License**.

## Support and Credits

Developed for the UCSC Rocket Team (SlugSight Avionics). For issues, please utilize the GitHub Issues tracker.
