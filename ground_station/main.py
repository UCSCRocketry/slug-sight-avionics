"""
Slug Sight Ground Station
Main entry point for the ground data receiving system.

This script:
1. Connects to the LoRa receiver
2. Receives telemetry packets
3. Logs data to CSV files
4. (Optional) Displays real-time data
"""

import sys
import time
import signal
from datetime import datetime
from pathlib import Path

from receiver.lora_receiver import LoRaReceiver
from data.telemetry_parser import TelemetryParser
from data.data_logger import DataLogger
from utils.helpers import load_config, setup_logging

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\nShutdown signal received. Closing...")
    running = False

def main():
    """Main ground station loop"""
    global running
    
    # Setup signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 50)
    print("  Slug Sight Ground Station v1.0")
    print("  UCSC Rocket Team")
    print("=" * 50)
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "ground_config.yaml"
    config = load_config(config_path)
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("Ground station starting...")
    
    # Initialize components
    try:
        # LoRa receiver
        lora_receiver = LoRaReceiver(config['lora'])
        logger.info(f"Connected to LoRa on {config['lora']['serial_port']}")
        
        # Telemetry parser
        parser = TelemetryParser(config['telemetry'])
        
        # Data logger
        data_logger = DataLogger(config['data_logging'])
        logger.info(f"Logging to: {data_logger.get_current_file()}")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)
    
    print("\nGround station ready!")
    print(f"Logging to: {data_logger.get_current_file()}")
    print("Waiting for telemetry...\n")
    print("-" * 50)
    
    # Statistics
    packet_count = 0
    error_count = 0
    start_time = time.time()
    last_packet_time = 0
    
    # Main receive loop
    try:
        while running:
            # Receive packet from LoRa
            raw_packet = lora_receiver.receive_packet()
            
            if raw_packet is not None:
                current_time = time.time()
                
                try:
                    # Parse telemetry
                    telemetry = parser.parse(raw_packet)
                    
                    if telemetry is not None:
                        # Add ground receive timestamp
                        telemetry['ground_time'] = current_time
                        
                        # Log to file
                        data_logger.write(telemetry)
                        
                        # Update statistics
                        packet_count += 1
                        last_packet_time = current_time
                        
                        # Console output (compact format)
                        if config['display']['enable_console_output']:
                            print_telemetry_compact(telemetry, packet_count)
                        
                    else:
                        error_count += 1
                        logger.warning("Failed to parse telemetry packet")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing packet: {e}")
            
            # Small delay to prevent CPU spinning
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        pass
    
    finally:
        # Cleanup
        print("\n" + "=" * 50)
        print("Shutting down ground station...")
        
        # Print statistics
        elapsed_time = time.time() - start_time
        print(f"\nSession Statistics:")
        print(f"  Duration: {elapsed_time:.1f} seconds")
        print(f"  Packets received: {packet_count}")
        print(f"  Errors: {error_count}")
        if packet_count > 0:
            print(f"  Average rate: {packet_count/elapsed_time:.1f} packets/sec")
        
        # Close connections
        data_logger.close()
        lora_receiver.close()
        
        print("\nGround station stopped.")
        print("=" * 50)

def print_telemetry_compact(telemetry, count):
    """Print telemetry in compact format"""
    state_colors = {
        'PAD': '\033[37m',      # White
        'BOOST': '\033[92m',    # Green
        'COAST': '\033[93m',    # Yellow
        'DESCENT': '\033[94m',  # Blue
        'LANDED': '\033[91m'    # Red
    }
    reset = '\033[0m'
    
    state = telemetry.get('state', 'UNKNOWN')
    color = state_colors.get(state, '')
    
    print(f"[{count:04d}] {color}{state:8s}{reset} | "
          f"Alt: {telemetry.get('altitude', 0):7.1f}m | "
          f"AccZ: {telemetry.get('accel_z', 0):6.2f} m/s² | "
          f"GPS: ({telemetry.get('gps_lat', 0):.5f}, {telemetry.get('gps_lon', 0):.5f})")

if __name__ == "__main__":
    main()
