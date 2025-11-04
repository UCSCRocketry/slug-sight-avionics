"""
Serial Reader for Ground Feather M4

Reads packets from the ground Feather M4 via USB serial connection.
Parses the packet format and extracts telemetry data.
"""

import serial
import struct
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SerialReader:
    """Read packets from ground Feather M4 via USB Serial"""
    
    def __init__(self, config: dict):
        """
        Initialize serial reader
        
        Args:
            config: Serial configuration dictionary
        """
        self.config = config
        self.serial_port = None
        self.connected = False
        
        # Connect to ground Feather
        self._connect()
    
    def _connect(self):
        """Establish serial connection to ground Feather"""
        try:
            port = self.config.get('serial_port', '/dev/cu.usbmodem14201')
            baud = self.config.get('baud_rate', 115200)
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=1.0
            )
            
            # Wait for connection
            import time
            time.sleep(2)
            
            self.connected = True
            logger.info(f"Connected to ground Feather on {port}")
            
        except serial.SerialException as e:
            logger.error(f"Failed to connect to ground Feather: {e}")
            raise
    
    def read_packet(self) -> Optional[Dict[str, Any]]:
        """
        Read a packet from the ground Feather
        
        Returns:
            Dictionary with 'data' (bytes) and 'metadata' (rssi, timestamp, etc.)
            or None if no packet available
        """
        if not self.connected:
            return None
        
        try:
            if self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8').strip()
                
                # Parse packet format: PKT:<num>,<time>,<len>,<rssi>,<hex_data>
                if line.startswith('PKT:'):
                    parts = line[4:].split(',')
                    
                    if len(parts) >= 5:
                        packet_num = int(parts[0])
                        timestamp_ms = int(parts[1])
                        packet_len = int(parts[2])
                        rssi = int(parts[3])
                        hex_data = parts[4]
                        
                        # Convert hex string to bytes
                        data_bytes = bytes.fromhex(hex_data)
                        
                        return {
                            'data': data_bytes,
                            'packet_num': packet_num,
                            'timestamp_ms': timestamp_ms,
                            'length': packet_len,
                            'rssi': rssi
                        }
                
                # Handle heartbeat
                elif line.startswith('HB:'):
                    logger.debug(f"Heartbeat: {line}")
                
                # Log other messages
                else:
                    logger.info(f"Ground Feather: {line}")
            
            return None
            
        except Exception as e:
            logger.error(f"Serial read error: {e}")
            self.connected = False
            return None
    
    def close(self):
        """Close serial connection"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            logger.info("Serial connection closed")
        self.connected = False


class TelemetryParser:
    """Parse binary telemetry packets from rocket"""
    
    # Telemetry packet structure (matches rocket firmware)
    # struct TelemetryPacket {
    #     uint32_t timestamp_ms;
    #     float altitude, pressure, temperature;
    #     float accel_x, accel_y, accel_z;
    #     float gyro_x, gyro_y, gyro_z;
    #     float mag_x, mag_y, mag_z;
    #     float gps_lat, gps_lon, gps_alt;
    #     uint8_t gps_satellites;
    #     uint8_t state;
    #     uint16_t packet_num;
    # } __attribute__((packed));
    
    STRUCT_FORMAT = '<I 3f 3f 3f 3f 3f BB H'  # Little-endian
    EXPECTED_SIZE = struct.calcsize(STRUCT_FORMAT)
    
    FLIGHT_STATES = {
        0: 'PAD',
        1: 'BOOST',
        2: 'COAST',
        3: 'DESCENT',
        4: 'LANDED'
    }
    
    def __init__(self):
        logger.info(f"Telemetry parser initialized (packet size: {self.EXPECTED_SIZE} bytes)")
    
    def parse(self, data: bytes, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse binary telemetry packet
        
        Args:
            data: Raw packet bytes
            metadata: Metadata from ground Feather (RSSI, etc.)
            
        Returns:
            Dictionary of telemetry values or None if parsing fails
        """
        if len(data) != self.EXPECTED_SIZE:
            logger.warning(f"Invalid packet size: {len(data)} != {self.EXPECTED_SIZE}")
            return None
        
        try:
            # Unpack binary data
            values = struct.unpack(self.STRUCT_FORMAT, data)
            
            telemetry = {
                # Metadata
                'timestamp_ms': values[0],
                'timestamp': values[0] / 1000.0,  # Convert to seconds
                'ground_rssi': metadata.get('rssi', 0),
                'ground_time': metadata.get('timestamp_ms', 0) / 1000.0,
                
                # Barometer
                'altitude': values[1],
                'pressure': values[2],
                'temperature': values[3],
                
                # IMU - Accelerometer
                'accel_x': values[4],
                'accel_y': values[5],
                'accel_z': values[6],
                
                # IMU - Gyroscope
                'gyro_x': values[7],
                'gyro_y': values[8],
                'gyro_z': values[9],
                
                # Magnetometer
                'mag_x': values[10],
                'mag_y': values[11],
                'mag_z': values[12],
                
                # GPS
                'gps_lat': values[13],
                'gps_lon': values[14],
                'gps_alt': values[15],
                'gps_satellites': values[16],
                
                # State
                'state': self.FLIGHT_STATES.get(values[17], 'UNKNOWN'),
                'state_code': values[17],
                
                # Packet info
                'packet_num': values[18]
            }
            
            return telemetry
            
        except Exception as e:
            logger.error(f"Failed to parse telemetry: {e}")
            return None


if __name__ == "__main__":
    # Test serial reader
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'serial_port': '/dev/cu.usbmodem14201',  # Update for your system
        'baud_rate': 115200
    }
    
    reader = SerialReader(config)
    parser = TelemetryParser()
    
    print("Listening for packets... (Ctrl+C to stop)")
    try:
        while True:
            packet = reader.read_packet()
            if packet:
                telemetry = parser.parse(packet['data'], packet)
                if telemetry:
                    print(f"[{telemetry['packet_num']:04d}] "
                          f"Alt: {telemetry['altitude']:.1f}m | "
                          f"RSSI: {telemetry['ground_rssi']}dBm")
            
            import time
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.close()
