# Communication Protocol

This document describes the telemetry communication protocol between the flight computer and ground station.

## Overview

The Slug Sight Avionics system uses a **binary packet protocol** over LoRa radio for efficient, reliable telemetry transmission.

### Key Features
- Fixed-size packets for predictable timing
- Binary encoding for bandwidth efficiency
- CRC16 checksum for error detection
- Sequence numbers for packet tracking
- State machine integration

## Packet Structure

### Binary Packet Format

Total packet size: **74 bytes**

| Field | Type | Size (bytes) | Description |
|-------|------|--------------|-------------|
| packet_id | uint8 | 1 | Packet type identifier (always 0x01 for telemetry) |
| sequence_number | uint16 | 2 | Incremental packet counter (wraps at 65535) |
| timestamp | float | 4 | Flight computer time since boot (seconds) |
| state | uint8 | 1 | Flight state (0=PAD, 1=BOOST, 2=COAST, 3=DESCENT, 4=LANDED) |
| altitude | float | 4 | Barometric altitude (meters) |
| pressure | float | 4 | Atmospheric pressure (pascals) |
| temperature | float | 4 | Ambient temperature (celsius) |
| accel_x | float | 4 | X-axis acceleration (m/s²) |
| accel_y | float | 4 | Y-axis acceleration (m/s²) |
| accel_z | float | 4 | Z-axis acceleration (m/s²) |
| gyro_x | float | 4 | X-axis rotation rate (deg/s) |
| gyro_y | float | 4 | Y-axis rotation rate (deg/s) |
| gyro_z | float | 4 | Z-axis rotation rate (deg/s) |
| mag_x | float | 4 | X-axis magnetic field (μT) |
| mag_y | float | 4 | Y-axis magnetic field (μT) |
| mag_z | float | 4 | Z-axis magnetic field (μT) |
| gps_lat | float | 4 | GPS latitude (degrees) |
| gps_lon | float | 4 | GPS longitude (degrees) |
| gps_alt | float | 4 | GPS altitude (meters) |
| checksum | uint16 | 2 | CRC16 checksum of all previous fields |

### Byte Ordering
- **Little-endian** (LSB first)
- Consistent with most microcontrollers (ARM, ESP32)

## Packet Types

### Telemetry Packet (0x01)
- Standard telemetry data
- Sent every 100ms during flight
- Contains all sensor readings

### Future Packet Types (Extensible)
- 0x02: Command packet (ground → rocket)
- 0x03: Status packet (system health)
- 0x04: Event packet (state transitions)

## Flight States

| State Code | Name | Description |
|------------|------|-------------|
| 0 | PAD | On launch pad, waiting for launch |
| 1 | BOOST | Motor burning, accelerating |
| 2 | COAST | Unpowered flight to apogee |
| 3 | DESCENT | Falling (parachute deployed) |
| 4 | LANDED | On ground after flight |

## Checksum Calculation

### CRC16-CCITT

```c
uint16_t calculate_crc16(uint8_t *data, size_t length) {
    uint16_t crc = 0xFFFF;
    
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x0001) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    
    return crc;
}
```

**Note:** Checksum is calculated over all fields except the checksum field itself.

## LoRa Configuration

### Radio Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Frequency | 915 MHz | US ISM band (868 MHz for EU) |
| Bandwidth | 125 kHz | Balance of range vs. data rate |
| Spreading Factor | 7 | SF7 = fastest data rate |
| Coding Rate | 4/5 | Error correction overhead |
| TX Power | 20 dBm | Maximum legal power |
| Sync Word | 0x12 | Private network identifier |

### Data Rate Calculation

With SF7, BW=125kHz:
- **Air time per packet**: ~60-80 ms
- **Maximum throughput**: ~12-15 packets/sec
- **Configured rate**: 10 packets/sec (100ms interval)

## Transmission Schedule

### Normal Flight
```
t=0ms:    Sensor update
t=10ms:   Prepare telemetry packet
t=20ms:   Transmit via LoRa (60-80ms)
t=100ms:  Next cycle
```

### High-Rate Mode (Optional)
- Increase to 20 Hz during critical phases (launch, apogee)
- Requires SF6 or higher bandwidth

## Error Handling

### Packet Loss
- Ground station detects missing sequence numbers
- Logged as gaps in data
- No retransmission (real-time system)

### Corrupted Packets
- CRC mismatch → discard packet
- Log error, continue receiving
- Validation ranges in ground station

### Radio Disconnection
- Ground station auto-reconnect
- Flight computer continues transmitting
- All data logged to SD card as backup

## Example Packet

### Binary (Hex Dump)
```
01 00 2A 00 41 28 00 00 01 43 14 66 42 42 76 8A
41 41 A0 00 00 3E CC CC CD 3F 80 00 00 41 1C CC
CD 3D CC CC CD 3E 4C CC CD 3E 99 99 9A 42 48 00
00 41 44 00 00 C1 F0 00 00 42 13 D7 0A C2 F4 8F
5C 42 1A 66 66 AB CD
```

### Decoded
```json
{
  "packet_id": 1,
  "sequence_number": 42,
  "timestamp": 10.5,
  "state": 1,
  "altitude": 150.5,
  "pressure": 95000.0,
  "temperature": 20.5,
  "accel_x": 0.5,
  "accel_y": 1.0,
  "accel_z": 9.8,
  "gyro_x": 0.1,
  "gyro_y": 0.2,
  "gyro_z": 0.3,
  "mag_x": 45.0,
  "mag_y": 12.0,
  "mag_z": -30.0,
  "gps_lat": 37.0,
  "gps_lon": -122.0,
  "gps_alt": 155.0,
  "checksum": 0xCDAB
}
```

## Ground Station Reception

### Receive Flow
1. LoRa module receives packet
2. Serial data to computer
3. Python parser validates checksum
4. Range validation
5. Write to CSV file
6. Display on console

### Data Validation

```python
# Reasonable ranges for sanity checking
RANGES = {
    'altitude': (-100, 50000),      # meters
    'pressure': (10000, 110000),    # pascals
    'temperature': (-50, 100),      # celsius
    'accel': (-200, 200),           # m/s²
    'gyro': (-2000, 2000),          # deg/s
}
```

## Future Enhancements

### Bidirectional Communication
- Commands from ground station
- Parachute deployment override
- Data rate adjustment

### Adaptive Data Rate
- Increase rate during critical events
- Decrease when signal weak
- Optimize for range vs. throughput

### Data Compression
- Differential encoding for IMU
- Reduce packet size to ~40 bytes
- Double the effective data rate

### Encryption (Optional)
- Prevent interference from other systems
- AES-128 encryption
- Minimal overhead with hardware crypto

## Testing

### Bench Test
1. Connect flight computer and ground station via cable
2. Verify packet parsing
3. Check all sensor values

### Range Test
1. Place ground station at launch site
2. Walk with flight computer
3. Record maximum reliable range
4. Adjust antenna/power as needed

### Interference Test
1. Test near other LoRa devices
2. Verify sync word isolation
3. Check packet error rate

## Regulatory Compliance

### United States (FCC Part 15)
- 915 MHz ISM band
- Maximum 1W EIRP
- No license required

### Europe (ETSI)
- 868 MHz ISM band
- Maximum 25mW ERP
- Duty cycle limits may apply

### Other Regions
- Check local regulations
- May need different frequency
