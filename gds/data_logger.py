"""
Data Logger

Handles writing telemetry data to CSV files.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DataLogger:
    """Log telemetry data to CSV files"""
    
    def __init__(self, config: dict):
        """
        Initialize data logger
        
        Args:
            config: Data logging configuration dictionary
        """
        self.config = config
        self.output_dir = Path(config.get('output_directory', './data/flights'))
        self.csv_file = None
        self.csv_writer = None
        self.current_filename = None
        
        # Create output directory if it doesn't exist
        if config.get('auto_create_directory', True):
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file
        self._initialize_file()
    
    def _initialize_file(self):
        """Create and open a new CSV log file"""
        # Generate filename with timestamp
        timestamp = datetime.now()
        filename_format = self.config.get('filename_format', '%Y-%m-%d_%H-%M-%S')
        filename_base = timestamp.strftime(filename_format)
        
        self.current_filename = self.output_dir / f"{filename_base}.csv"
        # Open with explicit encoding for broader compatibility
        self.csv_file = open(self.current_filename, 'w', newline='', encoding='utf-8')
        self.csv_writer = None  # Will be created when we know the fields
        logger.info(f"Logging to CSV: {self.current_filename}")
    
    def write(self, telemetry: Dict[str, Any]):
        """
        Write telemetry data to CSV file
        
        Args:
            telemetry: Dictionary of telemetry values
        """
        self._write_csv(telemetry)
    
    def _write_csv(self, telemetry: Dict[str, Any]):
        """Write telemetry to CSV file"""
        # Create CSV writer on first write (now we know the fields)
        if self.csv_writer is None:
            fieldnames = list(telemetry.keys())
            
            if self.config.get('csv', {}).get('include_header', True):
                self.csv_writer = csv.DictWriter(
                    self.csv_file,
                    fieldnames=fieldnames,
                    delimiter=self.config.get('csv', {}).get('delimiter', ',')
                )
                self.csv_writer.writeheader()
            else:
                self.csv_writer = csv.DictWriter(
                    self.csv_file,
                    fieldnames=fieldnames,
                    delimiter=self.config.get('csv', {}).get('delimiter', ',')
                )
        
        # Format float precision
        formatted_telemetry = self._format_floats(telemetry)
        
        # Write row
        self.csv_writer.writerow(formatted_telemetry)
        
        # Flush to disk periodically
        if hasattr(self, '_write_count'):
            self._write_count += 1
        else:
            self._write_count = 1
        
        flush_interval = self.config.get('buffer_size', 10)
        if self._write_count % flush_interval == 0:
            self.csv_file.flush()
    
    def _format_floats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format floating point numbers to specified precision"""
        precision = self.config.get('csv', {}).get('float_precision', 6)
        formatted = {}
        
        for key, value in data.items():
            if isinstance(value, float):
                formatted[key] = round(value, precision)
            else:
                formatted[key] = value
        
        return formatted
    
    def flush(self):
        """Flush CSV data to disk"""
        if self.csv_file:
            self.csv_file.flush()
    
    def close(self):
        """Close CSV file and flush remaining data"""
        logger.info(f"Closing log file: {self.current_filename}")
        
        if self.csv_file:
            self.csv_file.flush()
            self.csv_file.close()
        
        logger.info(f"Data saved to: {self.current_filename}")
    
    def get_current_file(self) -> str:
        """Get path to current log file"""
        return str(self.current_filename) if self.current_filename else ""

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        'output_directory': './test_data',
        'filename_format': '%Y-%m-%d_%H-%M-%S',
        'auto_create_directory': True,
        'csv': {
            'delimiter': ',',
            'include_header': True,
            'float_precision': 3
        },
        'buffer_size': 5
    }
    
    logger_instance = DataLogger(test_config)
    
    # Write some test data
    for i in range(10):
        test_telemetry = {
            'timestamp': i * 0.1,
            'altitude': 100.0 + i * 10,
            'pressure': 101325.0,
            'temperature': 20.5,
            'state': 'BOOST'
        }
        logger_instance.write(test_telemetry)
    
    logger_instance.close()
    print(f"Test data written to: {logger_instance.get_current_file()}")
