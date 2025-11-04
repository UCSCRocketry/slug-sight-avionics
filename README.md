# Slug Sight Avionics

**Rocket avionics system with dual Feather M4 architecture and web-based ground station**

A complete avionics solution for model rocketry featuring sensor fusion, LoRa telemetry, and real-time web visualization. Built for the UCSC Rocket Team.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Feather%20M4-orange.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)

---

## 🚀 System Architecture

### **Dual Feather M4 Design**

```
┌─────────────────────────────────────────┐
│ ROCKET FEATHER M4                       │
│  ├─ BMP280 (SPI) ────┐                 │
│  ├─ LSM6DSOX (I2C) ──┤                 │
│  ├─ LIS3MDL (I2C) ───┼──> Telemetry    │
│  └─ GPS (UART) ──────┘     ↓           │
│                        RFM95W LoRa ─────┼─→ Wireless 915 MHz
└─────────────────────────────────────────┘
                                          │
                                          ↓
┌─────────────────────────────────────────┐
│ GROUND FEATHER M4 (LoRa Bridge)         │
│   RFM95W LoRa ──> USB Serial ───────────┼─→ USB Cable
└─────────────────────────────────────────┘
                                          │
                                          ↓
┌─────────────────────────────────────────┐
│ LAPTOP (Python Ground Station)          │
│   ├─ Read USB Serial                    │
│   ├─ Parse & log telemetry (CSV)        │
│   └─ Flask Web UI (localhost:5000)      │
└─────────────────────────────────────────┘
```

---

## ✨ Features

### Flight Computer (Rocket Feather M4)
- **5 sensors**: BMP280 barometer (SPI), LSM6DSOX IMU (I2C), LIS3MDL magnetometer (I2C), Ultimate GPS (UART)
- **LoRa transmission**: 915 MHz, 10 Hz data rate, 2-5 km range
- **RadioHead library**: Reliable packet transmission with RSSI feedback
- **120 MHz ARM Cortex-M4**: No timing issues, 60-100 Hz capable

### Ground Receiver (Ground Feather M4)
- **LoRa-to-USB bridge**: Simple, reliable packet forwarding
- **Hot-swappable**: Unplug/replug laptop without affecting LoRa link
- **RSSI reporting**: Signal strength monitoring

### Ground Station (Laptop)
- **Flask web interface**: http://localhost:5000
- **Real-time visualization**: Live telemetry dashboard
- **CSV data logging**: Timestamped flight logs
- **Cross-platform**: Works on macOS, Linux, Windows

---

## 📋 Hardware Requirements

| Component | Rocket | Ground | Model |
|-----------|--------|--------|-------|
| **Microcontroller** | ✅ | ✅ | Adafruit Feather M4 Express |
| **LoRa Radio** | ✅ | ✅ | RFM95W (915 MHz) |
| **Barometer** | ✅ | ❌ | BMP280 (SPI) |
| **IMU** | ✅ | ❌ | LSM6DSOX (I2C) |
| **Magnetometer** | ✅ | ❌ | LIS3MDL (I2C) |
| **GPS** | ✅ | ❌ | Adafruit Ultimate GPS |
| **USB Cable** | ❌ | ✅ | USB-C to connect to laptop |

**Total cost:** ~$150-200

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for complete wiring diagrams.

---

## 📁 Project Structure

```
slug-sight-avionics/
├── firmware_rocket/              # Rocket Feather M4 code
│   ├── src/main.cpp             # Sensor reading + LoRa TX
│   └── platformio.ini
│
├── firmware_ground/              # Ground Feather M4 code
│   ├── src/main.cpp             # LoRa RX + USB Serial bridge
│   └── platformio.ini
│
├── ground_station/               # Laptop Python GDS
│   ├── app.py                   # Flask web server
│   ├── serial_reader.py         # Read from ground Feather
│   ├── data/
│   │   ├── telemetry_parser.py
│   │   └── data_logger.py
│   └── templates/
│       └── dashboard.html       # Web UI
│
├── config/
│   └── ground_config.yaml       # Ground station settings
│
├── data/
│   └── flights/                 # CSV log files
│
└── docs/
    ├── ARCHITECTURE.md          # System architecture
    ├── hardware.md
    └── setup.md
```

---

## 🛠️ Quick Start

### 1. Flash Firmware

**Rocket Feather M4:**
```bash
cd firmware_rocket
pio run --target upload
```

**Ground Feather M4:**
```bash
cd firmware_ground
pio run --target upload
```

### 2. Setup Ground Station

```bash
cd ground_station
pip install -r ../requirements.txt
```

Edit `config/ground_config.yaml` and set your serial port:
```yaml
serial:
  serial_port: "/dev/cu.usbmodem14201"  # Update this!
```

To find your port:
```bash
# macOS/Linux
ls /dev/cu.usbmodem*

# Linux alternative
ls /dev/ttyACM*

# Windows: Check Device Manager
```

### 3. Run Ground Station

```bash
python app.py
```

Open browser to: **http://localhost:5000**

---

## 📊 Data Format

### Telemetry Packet (Binary, sent every 100ms):
| Field | Type | Size | Unit |
|-------|------|------|------|
| timestamp_ms | uint32 | 4 | milliseconds |
| altitude | float | 4 | meters |
| pressure | float | 4 | pascals |
| temperature | float | 4 | celsius |
| accel_x/y/z | float | 12 | m/s² |
| gyro_x/y/z | float | 12 | deg/s |
| mag_x/y/z | float | 12 | μT |
| gps_lat/lon/alt | float | 12 | degrees/meters |
| gps_satellites | uint8 | 1 | count |
| state | uint8 | 1 | enum |
| packet_num | uint16 | 2 | counter |

**Total:** ~66 bytes per packet

### CSV Output:
```csv
timestamp,altitude,pressure,temperature,accel_x,accel_y,accel_z,...
0.100,100.5,101325,25.3,0.1,0.2,9.8,...
0.200,150.2,98500,24.1,2.5,1.2,35.6,...
```

---

## 🧪 Testing

### Bench Test (Both Feathers)
1. Connect rocket Feather to USB
2. Open serial monitor: `pio device monitor`
3. Verify sensors initialize
4. Check LoRa transmission messages

### Range Test
1. Start ground station on laptop
2. Power rocket Feather with battery
3. Walk away while monitoring web interface
4. Record maximum reliable range

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete system architecture and data flow
- **[hardware.md](docs/hardware.md)** - Hardware specs, wiring, BOM
- **[setup.md](docs/setup.md)** - Detailed setup instructions

---

## ❓ FAQ

**Q: Why two Feather M4 boards?**  
A: The ground Feather acts as a reliable LoRa-to-USB bridge. This separates concerns and lets you hot-swap the laptop connection without affecting the LoRa link.

**Q: Timing issues with 5 sensors?**  
A: No! Feather M4 @ 120 MHz can easily handle all sensors at 60-100 Hz. Total loop time is ~3-5 ms.

**Q: Can I use one Feather and a LoRa USB dongle?**  
A: Yes, but Feather M4 is more reliable and gives you RSSI data. Plus you can add features to the ground Feather later.

**Q: BMP280 over SPI vs I2C?**  
A: SPI is faster (~0.5ms vs ~2ms) and frees up I2C bandwidth for other sensors.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test on hardware
4. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 👥 Team

**UCSC Rocket Team**  
Built for the UC Santa Cruz Rocketry Club

---

## 🙏 Acknowledgments

- Adafruit for excellent hardware and libraries
- RadioHead library by Mike McCauley
- Flask framework

---

**Ready to launch? 🚀**

Start with the [Architecture Guide](docs/ARCHITECTURE.md)

---

## 🚀 Features

### Flight Computer
- **Multi-sensor fusion**: IMU, magnetometer, GPS, barometer
- **LoRa telemetry**: Long-range wireless communication (2-5 km)
- **Dual data logging**: Real-time transmission + SD card backup
- **Flight state machine**: Automatic phase detection (PAD → BOOST → COAST → DESCENT → LANDED)
- **Configurable**: YAML-based configuration for easy tuning

### Ground Station
- **Real-time data reception**: Live telemetry via LoRa
- **CSV/JSON logging**: Automatic timestamped data files
- **Data validation**: Range checking and error detection
- **Console dashboard**: Live display of key metrics
- **Python-based**: Cross-platform (Linux/Mac/Windows)

---

## 📋 Hardware Components

| Component | Function | Example Model |
|-----------|----------|---------------|
| **Microcontroller** | Flight computer | ESP32, Teensy 4.1 |
| **IMU** | Acceleration & rotation | BMI088, MPU6050 |
| **Barometer** | Altitude measurement | BMP388, MS5611 |
| **Magnetometer** | Orientation | HMC5883L, QMC5883L |
| **GPS** | Position tracking | u-blox NEO-M9N |
| **LoRa Radio** | Telemetry (2x) | RFM95W (SX1276) |
| **Storage** | Data backup | MicroSD card module |
| **Power** | Battery | 2S LiPo + regulator |

**Total cost:** ~$135 (see detailed BOM in [`docs/hardware.md`](docs/hardware.md))

---

## 📁 Project Structure

```
slug-sight-avionics/
├── config/                      # Configuration files
│   ├── flight_config.yaml      # Flight computer settings
│   └── ground_config.yaml      # Ground station settings
│
├── firmware/                    # Flight computer code (C++)
│   ├── src/
│   │   ├── main.cpp            # Main program
│   │   ├── sensors/            # Sensor drivers
│   │   ├── communications/     # LoRa interface
│   │   ├── data/               # Telemetry & logging
│   │   └── state/              # Flight state machine
│   └── platformio.ini          # Build configuration
│
├── ground_station/              # Ground data system (Python)
│   ├── main.py                 # Main application
│   ├── receiver/               # LoRa receiver
│   ├── data/                   # Telemetry parser & logger
│   ├── gui/                    # Optional: Real-time display
│   └── utils/                  # Helper functions
│
├── data/                        # Stored flight data
│   ├── flights/                # CSV/JSON logs
│   └── raw/                    # Raw packet backup
│
├── analysis/                    # Post-flight analysis
│   └── plot_flight.py          # Visualization tools
│
├── docs/                        # Documentation
│   ├── hardware.md             # Hardware specifications
│   ├── protocol.md             # Communication protocol
│   └── setup.md                # Setup instructions
│
├── tests/                       # Unit tests
└── requirements.txt             # Python dependencies
```

---

## 🛠️ Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/UCSCRocketry/slug-sight-avionics.git
cd slug-sight-avionics
```

### 2. Firmware Setup

**Install PlatformIO:**
```bash
# Using VS Code extension (recommended)
# Or via pip:
pip install platformio
```

**Build and upload:**
```bash
cd firmware
pio run --target upload
```

See [`docs/setup.md`](docs/setup.md) for detailed instructions.

### 3. Ground Station Setup

**Install Python dependencies:**
```bash
cd ground_station
pip install -r ../requirements.txt
```

**Configure serial port:**
```bash
# Edit config/ground_config.yaml
# Set serial_port to your LoRa receiver port (e.g., /dev/ttyUSB0)
```

**Run ground station:**
```bash
python main.py
```

---

## 📊 Configuration

### Flight Computer (`config/flight_config.yaml`)

```yaml
sensors:
  imu:
    model: "BMI088"
    sample_rate_hz: 100
    accel_range: 16

lora:
  frequency_mhz: 915.0
  spreading_factor: 7
  transmit_interval_ms: 100
```

All parameters are documented with comments in the config files.

### Ground Station (`config/ground_config.yaml`)

```yaml
lora:
  serial_port: "/dev/ttyUSB0"  # Change to your port
  frequency_mhz: 915.0          # Must match flight computer

data_logging:
  format: "csv"                 # or "json"
  output_directory: "./data/flights"
```

---

## 📡 Communication Protocol

- **Binary packets**: 74 bytes, fixed size
- **Update rate**: 10 Hz (100ms interval)
- **Range**: 2-5 km line-of-sight
- **Error detection**: CRC16 checksum
- **Frequency**: 915 MHz (US) / 868 MHz (EU)

See [`docs/protocol.md`](docs/protocol.md) for complete specification.

---

## 📈 Example Flight Data

Telemetry CSV output format:

```csv
timestamp,state,altitude,pressure,temperature,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,...
0.100,PAD,100.5,101325,25.3,0.1,0.2,9.8,0.01,0.02,0.03,...
0.200,PAD,100.5,101324,25.3,0.1,0.2,9.8,0.02,0.01,0.04,...
1.500,BOOST,150.2,98500,24.1,2.5,1.2,35.6,5.2,2.1,1.8,...
```

---

## 🧪 Testing

### Sensor Test
```bash
cd firmware
pio run --target upload
# Open serial monitor to verify sensor readings
pio device monitor
```

### LoRa Range Test
1. Start ground station
2. Power flight computer with battery
3. Walk away while monitoring packet reception
4. Record maximum reliable range

### Full Integration Test
Simulate flight phases by moving the flight computer:
- PAD → Hold still
- BOOST → Rapid upward acceleration
- COAST → Steady upward motion
- DESCENT → Slow downward motion
- LANDED → Return to stationary

---

## 📚 Documentation

- **[Hardware Guide](docs/hardware.md)** - Component selection, wiring, BOM
- **[Setup Instructions](docs/setup.md)** - Step-by-step installation
- **[Protocol Specification](docs/protocol.md)** - Communication details
- **[Configuration Reference](config/)** - All config parameters explained

---

## 🤝 Contributing

We welcome contributions! Here's how to help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🐛 Troubleshooting

### Common Issues

**Q: Sensors not detected**
- Check I2C wiring (SDA/SCL)
- Verify I2C addresses in config
- Use I2C scanner sketch

**Q: No LoRa packets received**
- Verify frequency matches (915 MHz vs 868 MHz)
- Check antenna connection
- Reduce distance for initial testing

**Q: SD card write failures**
- Use high-quality SD card (Class 10+)
- Format as FAT32
- Check CS pin configuration

See [`docs/setup.md#troubleshooting`](docs/setup.md#troubleshooting) for more.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**UCSC Rocket Team**
- Built for the UC Santa Cruz Rocketry Club
- Designed for model rocketry competitions and research

---

## 🙏 Acknowledgments

- Adafruit for excellent sensor libraries
- Sandeep Mistry for LoRa Arduino library
- PlatformIO for the development platform
- UCSC Engineering Department

---

## 📞 Contact

- GitHub Issues: [Report bugs/requests](https://github.com/UCSCRocketry/slug-sight-avionics/issues)
- UCSC Rocket Team: [Website](https://ucscrocketry.org) (if applicable)

---

**Ready to launch? 🚀**

Start with the [Setup Guide](docs/setup.md) 
