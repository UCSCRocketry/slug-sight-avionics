#!/usr/bin/env python3
"""
Test script for telemetry parser and data logger integration
"""

import sys
import logging
from pathlib import Path

# Add gds directory to path
sys.path.insert(0, str(Path(__file__).parent))

from telemetry_parser import TelemetryParser
from data_logger import DataLogger

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_parser():
    """Test the telemetry parser with sample data"""
    logger.info("=" * 60)
    logger.info("Testing Telemetry Parser")
    logger.info("=" * 60)
    
    # Initialize parser
    parser = TelemetryParser()
    
    # Test CSV strings (18 values)
    test_cases = [
        # pitch, roll, yaw, alt, vel, ax, ay, az, pressure, temp, fix, sats, lat, lon, gps_alt, gps_speed, vbat, rssi
        "5.2,-3.1,45.8,125.5,15.3,0.5,0.2,9.8,101325.0,22.5,1,8,37.123456,-122.345678,130.2,12.5,3.85,-95",
        "12.3,5.7,92.1,350.8,45.2,2.1,0.8,10.2,98500.0,24.3,1,9,37.124567,-122.346789,355.0,50.3,3.82,-88",
        "0.0,0.0,0.0,0.0,0.0,0.0,0.0,9.81,101325.0,20.0,0,0,0.0,0.0,0.0,0.0,4.1,-100"
    ]
    
    for i, test_csv in enumerate(test_cases, 1):
        logger.info(f"\nTest Case {i}:")
        logger.info(f"Input CSV: {test_csv}")
        
        result = parser.parse(test_csv)
        
        if result:
            logger.info("✓ Parse successful!")
            logger.info("Parsed data:")
            for key, value in result.items():
                logger.info(f"  {key:20s}: {value}")
        else:
            logger.error("✗ Parse failed!")
    
    logger.info("\n" + "=" * 60)

def test_logger():
    """Test the data logger with sample telemetry"""
    logger.info("=" * 60)
    logger.info("Testing Data Logger")
    logger.info("=" * 60)
    
    # Configure logger for test
    logger_config = {
        'output_directory': str(Path(__file__).parent / 'test_flight_data'),
        'filename_format': 'test_%Y%m%d_%H%M%S',
        'auto_create_directory': True,
        'csv': {
            'delimiter': ',',
            'include_header': True,
            'float_precision': 6
        },
        'buffer_size': 5
    }
    
    # Initialize components
    parser = TelemetryParser()
    data_logger_instance = DataLogger(logger_config)
    
    logger.info(f"Logging to: {data_logger_instance.get_current_file()}")
    
    # Simulate receiving telemetry packets
    test_packets = [
        "0.0,0.0,0.0,0.0,0.0,0.0,0.0,9.81,101325.0,20.0,0,0,0.0,0.0,0.0,0.0,4.1,-100",
        "2.5,-1.2,15.3,25.5,5.2,0.3,0.1,9.9,101200.0,21.2,0,3,37.100000,-122.300000,28.0,3.5,4.05,-98",
        "8.3,-3.5,45.8,125.5,25.8,1.2,0.5,11.2,98500.0,23.5,1,7,37.123456,-122.345678,130.5,28.5,3.95,-92",
        "15.2,2.8,78.9,285.3,45.2,2.8,1.2,13.5,92000.0,25.8,1,9,37.145678,-122.367890,290.0,55.3,3.88,-85",
        "12.5,5.1,92.5,425.8,38.5,2.1,0.9,12.8,88500.0,27.2,1,10,37.167890,-122.389012,430.2,48.7,3.82,-83",
    ]
    
    logger.info(f"\nSimulating {len(test_packets)} telemetry packets...")
    
    for i, packet in enumerate(test_packets, 1):
        telemetry = parser.parse(packet)
        if telemetry:
            data_logger_instance.write(telemetry)
            logger.info(f"  Packet {i}: Altitude={telemetry['Altitude']:.1f}m, "
                       f"Velocity={telemetry['Velocity']:.1f}m/s, "
                       f"VBat={telemetry['VBat']:.2f}V")
        else:
            logger.error(f"  Packet {i}: Failed to parse")
    
    # Close logger
    data_logger_instance.close()
    
    logger.info(f"\n✓ Test complete! Data saved to: {data_logger_instance.get_current_file()}")
    logger.info("=" * 60)

def test_integration():
    """Test full integration: parse and log"""
    logger.info("\n" + "=" * 60)
    logger.info("Integration Test: Parser + Logger")
    logger.info("=" * 60)
    
    test_parser()
    test_logger()
    
    logger.info("\n✓ All tests completed!")
    logger.info("=" * 60)

if __name__ == "__main__":
    test_integration()
