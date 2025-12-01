# SlugSight Avionics GDS
# Copyright (c) 2025 Rocket Team
# Licensed under the MIT License (See LICENSE file for full terms)
# ---------------------------------------------------------------------------

import unittest
import os
import shutil
from telemetry_parser import TelemetryParser
from data_logger import DataLogger

class TestTelemetryIntegration(unittest.TestCase):
    
    def setUp(self):
        """Setup a clean environment for each test"""
        self.test_dir = "./test_logs"
        self.parser = TelemetryParser()
        
        # Configure Logger to use a test directory
        self.logger_config = {
            'output_directory': self.test_dir,
            'auto_create_directory': True,
            'csv': {'include_header': True, 'float_precision': 6},
            'buffer_size': 1
        }
        self.datalogger = DataLogger(self.logger_config)

    def tearDown(self):
        """Clean up log files after tests"""
        self.datalogger.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_full_packet_flow(self):
        """Test a valid packet from RX -> Parser -> CSV Log"""
        # 1. Simulate a raw string from the Receiver (18 fields including RSSI)
        # Pitch, Roll, Yaw, Alt, Vel, AccX, AccY, AccZ, Pres, Temp, Fix, Sats, Lat, Lon, GAlt, GSpd, VBat, RSSI
        raw_rx_data = "1.5, 2.3, 45.0, 120.5, 15.2, 0.1, 0.2, 9.8, 101300, 25.0, 1, 7, 37.123456, -122.123456, 150.0, 1.2, 3.9, -85"
        
        # 2. Parse
        data = self.parser.parse(raw_rx_data)
        
        # Assertions on Parsing
        self.assertIsNotNone(data, "Parser returned None on valid packet")
        
        # FIX: Use snake_case keys ('pitch', 'rssi') not Title Case ('Pitch', 'RSSI')
        self.assertEqual(data['pitch'], 1.5)
        self.assertEqual(data['rssi'], -85.0)
        self.assertEqual(data['sys_status'], 'active')

        # 3. Log to CSV
        self.datalogger.write(data)
        
        # 4. Verify CSV Content
        log_file = self.datalogger.get_current_file()
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        # Expect 2 lines: Header and 1 Data Row
        self.assertEqual(len(lines), 2)
        # Check if RSSI (last column) was written
        self.assertIn("-85", lines[1]) 

    def test_waiting_state_logic(self):
        """Test that 'Waiting' messages trigger the correct status flag"""
        raw_msg = "Waiting for GPS Fix...,-90"
        
        data = self.parser.parse(raw_msg)
        
        self.assertIsNotNone(data)
        self.assertEqual(data['sys_status'], 'waiting')
        
        # FIX: Use snake_case keys here too
        self.assertEqual(data['rssi'], -90.0)
        # Ensure critical flight data is zeroed out, not None
        self.assertEqual(data['altitude'], 0.0) 

    def test_malformed_packet_resilience(self):
        """Test that the system drops bad packets instead of crashing"""
        # Packet with only 4 fields (Sender cut off?)
        bad_data = "1.5, 2.3, 45.0, 120.5" 
        
        data = self.parser.parse(bad_data)
        
        # Parser should return None, and Logger should typically NOT be called
        self.assertIsNone(data)

    def test_file_playback(self):
        """Test the system by replaying a full flight log file."""
        filename = "sample_telemetry.txt"
        
        # Ensure the file exists before testing
        if not os.path.exists(filename):
            self.skipTest(f"File {filename} not found. Skipping playback test.")

        print(f"\n[Test] Replaying {filename}...")
        
        valid_packets = 0
        
        with open(filename, 'r') as f:
            for line in f:
                raw_line = line.strip()
                if not raw_line: continue
                
                # Pass line to parser
                telemetry = self.parser.parse(raw_line)
                
                # Assertion: Parser should never crash on this sample data
                self.assertIsNotNone(telemetry, f"Failed to parse line: {raw_line}")
                
                # Handle logic transitions
                if telemetry.get('sys_status') == 'waiting':
                    # FIX: Check for snake_case 'rssi'
                    if 'rssi' in telemetry:
                        self.assertLess(telemetry['rssi'], 0)
                
                elif telemetry.get('sys_status') == 'active':
                    valid_packets += 1
                    # Log active data
                    self.datalogger.write(telemetry)

        # Verify we processed the active flight lines
        print(f"[Test] Processed {valid_packets} active flight packets.")
        self.assertGreater(valid_packets, 0)
        
        # Check if the CSV log was actually created
        log_file = self.datalogger.get_current_file()
        self.assertTrue(os.path.exists(log_file), "DataLogger failed to create output file")

if __name__ == '__main__':
    print("Running Telemetry Integration Tests...")
    unittest.main()
