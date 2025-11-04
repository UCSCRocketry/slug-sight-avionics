"""
LoRa Receiver Interface

Handles communication with the LoRa radio module to receive
telemetry packets from the rocket.
"""

import serial
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LoRaReceiver:
    """Interface for LoRa radio receiver"""
    
    def __init__(self, config: dict):
        """
        Initialize LoRa receiver
        
        Args:
            config: LoRa configuration dictionary
        """
        self.config = config
        self.serial_port = None
        self.connected = False
        
        # Connect to LoRa module
        self._connect()
    
    def _connect(self):
        """Establish connection to LoRa module"""
        try:
            self.serial_port = serial.Serial(
                port=self.config['serial_port'],
                baudrate=self.config['baud_rate'],
                timeout=self.config.get('timeout_s', 1.0)
            )
            
            # Wait for connection to stabilize
            time.sleep(2)
            
            # Configure LoRa parameters
            self._configure_lora()
            
            self.connected = True
            logger.info(f"Connected to LoRa on {self.config['serial_port']}")
            
        except serial.SerialException as e:
            logger.error(f"Failed to connect to LoRa: {e}")
            raise
    
    def _configure_lora(self):
        """
        Configure LoRa radio parameters
        This depends on your specific LoRa module (RFM95, SX1276, etc.)
        """
        # TODO: Implement module-specific configuration
        # For now, assume the module is pre-configured
        logger.info("LoRa configuration (assuming pre-configured module)")
        logger.info(f"  Frequency: {self.config['frequency_mhz']} MHz")
        logger.info(f"  Bandwidth: {self.config['bandwidth_khz']} kHz")
        logger.info(f"  Spreading Factor: {self.config['spreading_factor']}")
    
    def receive_packet(self) -> Optional[bytes]:
        """
        Receive a telemetry packet from LoRa
        
        Returns:
            Raw packet bytes, or None if no packet available
        """
        if not self.connected:
            if self.config.get('auto_reconnect', True):
                try:
                    self._connect()
                except Exception:
                    time.sleep(self.config.get('reconnect_delay_s', 2))
                    return None
            else:
                return None
        
        try:
            # Check if data is available
            if self.serial_port.in_waiting > 0:
                # Read packet (size depends on your protocol)
                packet_size = self.config.get('packet_size_bytes', 64)
                data = self.serial_port.read(packet_size)
                
                if len(data) == packet_size:
                    return data
                else:
                    logger.warning(f"Incomplete packet: {len(data)}/{packet_size} bytes")
                    return None
            
            return None
            
        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            self.connected = False
            return None
    
    def close(self):
        """Close LoRa connection"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            logger.info("LoRa connection closed")
        self.connected = False

# Example usage for testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        'serial_port': '/dev/ttyUSB0',
        'baud_rate': 115200,
        'frequency_mhz': 915.0,
        'bandwidth_khz': 125,
        'spreading_factor': 7,
        'packet_size_bytes': 64,
        'timeout_s': 1.0,
        'auto_reconnect': True
    }
    
    logging.basicConfig(level=logging.INFO)
    
    receiver = LoRaReceiver(test_config)
    
    print("Listening for packets... (Ctrl+C to stop)")
    try:
        while True:
            packet = receiver.receive_packet()
            if packet:
                print(f"Received {len(packet)} bytes: {packet.hex()}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        receiver.close()
