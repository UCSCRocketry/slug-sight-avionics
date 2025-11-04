"""
Telemetry Parser

Parses raw binary packets from the rocket into structured telemetry data.
"""

import struct
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TelemetryParser:
    """Parse binary telemetry packets"""
    
    # Flight state mapping
    FLIGHT_STATES = {
        0: 'PAD',
        1: 'BOOST',
        2: 'COAST',
        3: 'DESCENT',
        4: 'LANDED'
    }
    
    def __init__(self, config: dict):
        """
        Initialize telemetry parser
        
        Args:
            config: Telemetry configuration dictionary
        """
        self.config = config
        self.fields = config.get('fields', [])
        
        # Build struct format string for unpacking binary data
        # Format: '<' = little-endian
        # B = unsigned char (1 byte)
        # H = unsigned short (2 bytes)
        # f = float (4 bytes)
        self.struct_format = '<BHfBffffffffffffffH'  # Adjust based on TelemetryPacket
        self.expected_size = struct.calcsize(self.struct_format)
        
        logger.info(f"Telemetry parser initialized (expected packet size: {self.expected_size} bytes)")
    
    def parse(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse raw binary packet into telemetry dictionary
        
        Args:
            raw_data: Raw packet bytes
            
        Returns:
            Dictionary of telemetry values, or None if parsing fails
        """
        if len(raw_data) < self.expected_size:
            logger.warning(f"Packet too small: {len(raw_data)} < {self.expected_size}")
            return None
        
        try:
            # Unpack binary data
            unpacked = struct.unpack(self.struct_format, raw_data[:self.expected_size])
            
            # Extract fields
            packet_id = unpacked[0]
            sequence_number = unpacked[1]
            timestamp = unpacked[2]
            state_code = unpacked[3]
            altitude = unpacked[4]
            pressure = unpacked[5]
            temperature = unpacked[6]
            accel_x = unpacked[7]
            accel_y = unpacked[8]
            accel_z = unpacked[9]
            gyro_x = unpacked[10]
            gyro_y = unpacked[11]
            gyro_z = unpacked[12]
            mag_x = unpacked[13]
            mag_y = unpacked[14]
            mag_z = unpacked[15]
            gps_lat = unpacked[16]
            gps_lon = unpacked[17]
            gps_alt = unpacked[18]
            checksum = unpacked[19]
            
            # Verify checksum (optional but recommended)
            # TODO: Implement CRC16 verification
            
            # Build telemetry dictionary
            telemetry = {
                'packet_id': packet_id,
                'sequence_number': sequence_number,
                'timestamp': timestamp,
                'state': self.FLIGHT_STATES.get(state_code, 'UNKNOWN'),
                'altitude': altitude,
                'pressure': pressure,
                'temperature': temperature,
                'accel_x': accel_x,
                'accel_y': accel_y,
                'accel_z': accel_z,
                'gyro_x': gyro_x,
                'gyro_y': gyro_y,
                'gyro_z': gyro_z,
                'mag_x': mag_x,
                'mag_y': mag_y,
                'mag_z': mag_z,
                'gps_lat': gps_lat,
                'gps_lon': gps_lon,
                'gps_alt': gps_alt,
                'checksum': checksum
            }
            
            # Validate ranges (if enabled)
            if self.config.get('validation', {}).get('enable_range_check', True):
                if not self._validate_ranges(telemetry):
                    logger.warning("Telemetry values out of range")
                    return None
            
            return telemetry
            
        except struct.error as e:
            logger.error(f"Failed to unpack telemetry: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            return None
    
    def _validate_ranges(self, telemetry: Dict[str, Any]) -> bool:
        """
        Validate that telemetry values are within reasonable ranges
        
        Args:
            telemetry: Parsed telemetry dictionary
            
        Returns:
            True if all values are valid, False otherwise
        """
        ranges = self.config.get('validation', {}).get('ranges', {})
        
        # Check each field against its range
        for field, (min_val, max_val) in ranges.items():
            value = telemetry.get(field)
            
            if value is not None:
                # Handle vector fields (accel, gyro, mag)
                if field == 'accel':
                    for axis in ['accel_x', 'accel_y', 'accel_z']:
                        if not (min_val <= telemetry[axis] <= max_val):
                            logger.warning(f"{axis} out of range: {telemetry[axis]}")
                            return False
                elif field == 'gyro':
                    for axis in ['gyro_x', 'gyro_y', 'gyro_z']:
                        if not (min_val <= telemetry[axis] <= max_val):
                            logger.warning(f"{axis} out of range: {telemetry[axis]}")
                            return False
                else:
                    if not (min_val <= value <= max_val):
                        logger.warning(f"{field} out of range: {value}")
                        return False
        
        return True

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        'fields': [],
        'validation': {
            'enable_range_check': True,
            'ranges': {
                'altitude': [-100, 50000],
                'pressure': [10000, 110000],
                'temperature': [-50, 100],
                'accel': [-200, 200],
                'gyro': [-2000, 2000]
            }
        }
    }
    
    parser = TelemetryParser(test_config)
    
    # Create a test packet (example data)
    test_packet = struct.pack(
        '<BHfBffffffffffffffH',
        1,      # packet_id
        42,     # sequence_number
        10.5,   # timestamp
        1,      # state (BOOST)
        150.5,  # altitude
        95000,  # pressure
        20.5,   # temperature
        0.5, 1.0, 9.8,  # accel x,y,z
        0.1, 0.2, 0.3,  # gyro x,y,z
        25.0, 10.0, -30.0,  # mag x,y,z
        37.0, -122.0, 155.0,  # gps lat,lon,alt
        0xABCD  # checksum
    )
    
    result = parser.parse(test_packet)
    if result:
        print("Parsed telemetry:")
        for key, value in result.items():
            print(f"  {key}: {value}")
