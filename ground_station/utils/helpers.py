"""
Helper Utilities

Common utility functions for the ground station.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        print(f"Error parsing YAML config: {e}")
        raise

def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        config: Ground station configuration
        
    Returns:
        Configured logger instance
    """
    system_config = config.get('system', {})
    
    log_level_str = system_config.get('log_level', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(system_config.get('log_file', 'ground_station.log'))
        ]
    )
    
    logger = logging.getLogger('ground_station')
    return logger

def calculate_crc16(data: bytes) -> int:
    """
    Calculate CRC16 checksum
    
    Args:
        data: Bytes to calculate checksum for
        
    Returns:
        CRC16 checksum value
    """
    crc = 0xFFFF
    
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    
    return crc

def format_bytes(data: bytes, bytes_per_line: int = 16) -> str:
    """
    Format bytes as hex dump
    
    Args:
        data: Bytes to format
        bytes_per_line: Number of bytes per line
        
    Returns:
        Formatted hex dump string
    """
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i+bytes_per_line]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'{i:04x}  {hex_part:<48}  {ascii_part}')
    
    return '\n'.join(lines)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    
    Args:
        lat1, lon1: First coordinate (degrees)
        lat2, lon2: Second coordinate (degrees)
        
    Returns:
        Distance in meters
    """
    import math
    
    # Earth radius in meters
    R = 6371000
    
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance

# Example usage
if __name__ == "__main__":
    # Test CRC16
    test_data = b"Hello, World!"
    checksum = calculate_crc16(test_data)
    print(f"CRC16 of '{test_data.decode()}': 0x{checksum:04X}")
    
    # Test hex dump
    print("\nHex dump:")
    print(format_bytes(test_data))
    
    # Test haversine distance
    # Santa Cruz, CA to San Francisco, CA
    distance = haversine_distance(36.9741, -122.0308, 37.7749, -122.4194)
    print(f"\nDistance Santa Cruz to SF: {distance/1000:.2f} km")
