# Hardware Specification

This document describes the hardware components used in the Slug Sight Avionics system.

## Flight Computer

### Microcontroller Options

1. **ESP32 DevKit** (Recommended for beginners)
   - Dual-core 240 MHz processor
   - Built-in WiFi and Bluetooth
   - 520 KB SRAM
   - Cost: ~$10-15
   - Pros: Cheap, well-documented, lots of libraries
   - Cons: Lower reliability than Teensy

2. **Teensy 4.1**
   - 600 MHz ARM Cortex-M7
   - 1024 KB RAM
   - Built-in SD card slot
   - Cost: ~$30
   - Pros: Very fast, reliable, excellent for high-speed data logging
   - Cons: More expensive

## Sensors

### IMU (Inertial Measurement Unit)

**Recommended: BMI088**
- 6-axis (3-axis accelerometer + 3-axis gyroscope)
- Accelerometer range: ±3g to ±24g
- Gyroscope range: ±125°/s to ±2000°/s
- Interface: SPI or I2C
- Cost: ~$15-20
- High performance for rocketry applications

**Alternative: MPU6050**
- 6-axis IMU
- Lower cost (~$5-8)
- Good for low-budget projects
- Less accurate than BMI088

### Barometer

**Recommended: BMP388**
- Pressure range: 300-1250 hPa
- Altitude resolution: ~8 cm
- Temperature sensor included
- Interface: I2C or SPI
- Cost: ~$10-12
- Excellent altitude tracking

**Alternative: MS5611**
- Very accurate
- Popular in rocketry
- Cost: ~$8-15

### Magnetometer

**Recommended: HMC5883L**
- 3-axis digital compass
- Resolution: 1-2 degrees
- Interface: I2C
- Cost: ~$5-8
- Widely used and supported

**Alternative: QMC5883L**
- Compatible with HMC5883L
- Slightly cheaper
- Similar performance

### GPS

**Recommended: u-blox NEO-M9N**
- High accuracy (~1.5m)
- 25 Hz update rate
- Concurrent GPS, GLONASS, Galileo, BeiDou
- Interface: UART
- Cost: ~$30-40
- Best for precision tracking

**Alternative: NEO-6M**
- Budget option (~$10-15)
- 5 Hz update rate
- Good enough for basic tracking

## Communications

### LoRa Radio

**Recommended: RFM95W (SX1276)**
- Frequency: 915 MHz (US) or 868 MHz (EU)
- Range: 2-5 km (line of sight)
- Interface: SPI
- Cost: ~$10-15 per module (need 2: flight + ground)
- Excellent range for rocketry

**Module Breakout Boards:**
- Adafruit RFM95W LoRa Radio
- HopeRF RFM95W
- DIY options available

## Storage

### SD Card Module
- MicroSD card adapter
- SPI interface
- Cost: ~$2-5
- Use high-quality SD card (Class 10 or better)
- Recommended: 8-32 GB

## Power System

### Flight Computer Power

**Option 1: LiPo Battery (Recommended)**
- 2S or 3S LiPo (7.4V or 11.1V)
- Capacity: 500-2000 mAh (depending on flight duration)
- With step-down regulator to 5V or 3.3V
- Cost: ~$15-25

**Option 2: 9V Battery**
- Simple but less capacity
- Use with voltage regulator
- Cost: ~$5

### Voltage Regulators
- **For ESP32:** 5V to 3.3V regulator (built-in on most dev boards)
- **For Teensy:** Can handle 3.6-5.5V directly

## Assembly Components

### PCB Options

1. **Protoboard/Breadboard** (Development)
   - Quick prototyping
   - Not suitable for flight

2. **Custom PCB** (Flight-ready)
   - Designed in KiCAD or Eagle
   - Manufactured by JLCPCB, PCBWay, etc.
   - Cost: ~$20 for 5 boards

3. **Breakout Boards** (Quick assembly)
   - Use sensor breakout boards
   - Wire together with header pins
   - Add hot glue for mechanical stability

### Connectors
- JST connectors for sensors
- Header pins for programming
- Screw terminals for power

## Ground Station Hardware

### LoRa Receiver
- Same RFM95W module as flight computer
- Connected to laptop/computer via:
  - USB-Serial adapter (CP2102, FTDI)
  - Arduino/ESP32 as bridge

### Antenna
- 915 MHz quarter-wave antenna (~8 cm)
- Or commercial LoRa antenna
- Ground plane important for performance

### Laptop/Computer
- Any laptop running Python
- USB port for LoRa receiver
- Linux/Mac/Windows compatible

## Mechanical Integration

### Enclosure
- 3D printed case
- Shock-absorbing foam
- Ventilation for barometer
- Access to SD card

### Mounting
- Secure to rocket airframe
- Vibration dampening
- Center of gravity considerations

## Wiring Diagram

```
ESP32 Connections:
├── IMU (BMI088)
│   ├── SDA → GPIO 21
│   ├── SCL → GPIO 22
│   ├── VCC → 3.3V
│   └── GND → GND
├── Barometer (BMP388)
│   ├── SDA → GPIO 21 (shared I2C)
│   ├── SCL → GPIO 22 (shared I2C)
│   ├── VCC → 3.3V
│   └── GND → GND
├── Magnetometer (HMC5883L)
│   ├── SDA → GPIO 21 (shared I2C)
│   ├── SCL → GPIO 22 (shared I2C)
│   ├── VCC → 3.3V
│   └── GND → GND
├── GPS (NEO-M9N)
│   ├── TX → GPIO 16 (ESP32 RX)
│   ├── RX → GPIO 17 (ESP32 TX)
│   ├── VCC → 3.3V or 5V (check module)
│   └── GND → GND
├── LoRa (RFM95W)
│   ├── MOSI → GPIO 23
│   ├── MISO → GPIO 19
│   ├── SCK → GPIO 18
│   ├── CS → GPIO 5
│   ├── RST → GPIO 14
│   ├── DIO0 → GPIO 2
│   ├── VCC → 3.3V
│   └── GND → GND
└── SD Card
    ├── MOSI → GPIO 23 (shared SPI)
    ├── MISO → GPIO 19 (shared SPI)
    ├── SCK → GPIO 18 (shared SPI)
    ├── CS → GPIO 10
    ├── VCC → 3.3V
    └── GND → GND
```

## Bill of Materials (BOM)

| Component | Quantity | Unit Cost | Total |
|-----------|----------|-----------|-------|
| ESP32 DevKit | 1 | $12 | $12 |
| BMI088 IMU | 1 | $18 | $18 |
| BMP388 Barometer | 1 | $11 | $11 |
| HMC5883L Magnetometer | 1 | $6 | $6 |
| NEO-M9N GPS | 1 | $35 | $35 |
| RFM95W LoRa (x2) | 2 | $12 | $24 |
| MicroSD Module | 1 | $3 | $3 |
| LiPo Battery (2S 1000mAh) | 1 | $15 | $15 |
| Voltage Regulator | 1 | $2 | $2 |
| Connectors/Wire | - | $10 | $10 |
| **Total** | | | **~$136** |

*Note: Prices approximate as of 2025. Shop around for best deals.*

## Recommended Suppliers

- **Adafruit** - Quality breakout boards, good documentation
- **SparkFun** - Wide selection of sensors
- **Amazon** - Generic modules (cheaper but variable quality)
- **AliExpress/eBay** - Budget options (longer shipping)
- **Digi-Key/Mouser** - Professional components

## Safety Considerations

1. **LiPo Battery Safety**
   - Use LiPo charging bag
   - Don't over-discharge
   - Monitor temperature

2. **Antenna Safety**
   - Don't transmit without antenna
   - Can damage LoRa module

3. **ESD Protection**
   - Use anti-static precautions
   - Ground yourself when handling

4. **Testing**
   - Test all components before integration
   - Bench test complete system
   - Ground test before flight
