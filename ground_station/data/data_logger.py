"""
Data Logger

Handles writing telemetry data to CSV files.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DataLogger:
    """Log telemetry data to CSV or JSON files"""
    
    def __init__(self, config: dict):
        """
        Initialize data logger
        
        Args:
            config: Data logging configuration dictionary
        """
        self.config = config
        self.format = config.get('format', 'csv')
        self.output_dir = Path(config.get('output_directory', './data/flights'))
        self.csv_file = None
        self.csv_writer = None
        self.json_data = []
        self.current_filename = None
        
        # Create output directory if it doesn't exist
        if config.get('auto_create_directory', True):
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file
        self._initialize_file()
    
    def _initialize_file(self):
        """Create and open a new log file"""
        # Generate filename with timestamp
        timestamp = datetime.now()
        filename_format = self.config.get('filename_format', '%Y-%m-%d_%H-%M-%S')
        filename_base = timestamp.strftime(filename_format)
        
        if self.format == 'csv':
            self.current_filename = self.output_dir / f"{filename_base}.csv"
            self.csv_file = open(self.current_filename, 'w', newline='')
            self.csv_writer = None  # Will be created when we know the fields
            logger.info(f"Logging to CSV: {self.current_filename}")
        
        elif self.format == 'json':
            self.current_filename = self.output_dir / f"{filename_base}.json"
            logger.info(f"Logging to JSON: {self.current_filename}")
        
        else:
            raise ValueError(f"Unsupported format: {self.format}")
    
    def write(self, telemetry: Dict[str, Any]):
        """
        Write telemetry data to file
        
        Args:
            telemetry: Dictionary of telemetry values
        """
        if self.format == 'csv':
            self._write_csv(telemetry)
        elif self.format == 'json':
            self._write_json(telemetry)
    
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
    
    def _write_json(self, telemetry: Dict[str, Any]):
        """Write telemetry to JSON file (buffered)"""
        formatted_telemetry = self._format_floats(telemetry)
        self.json_data.append(formatted_telemetry)
        
        # Flush to disk periodically
        buffer_size = self.config.get('buffer_size', 100)
        if len(self.json_data) >= buffer_size:
            self.flush()
    
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
        """Flush data to disk"""
        if self.format == 'csv' and self.csv_file:
            self.csv_file.flush()
        
        elif self.format == 'json' and self.json_data:
            with open(self.current_filename, 'w') as f:
                json.dump(self.json_data, f, indent=2)
            logger.info(f"Flushed {len(self.json_data)} records to JSON")
    
    def close(self):
        """Close log file and flush remaining data"""
        logger.info(f"Closing log file: {self.current_filename}")
        
        if self.format == 'csv' and self.csv_file:
            self.csv_file.flush()
            self.csv_file.close()
        
        elif self.format == 'json':
            self.flush()
        
        logger.info(f"Data saved to: {self.current_filename}")
    
    def get_current_file(self) -> str:
        """Get path to current log file"""
        return str(self.current_filename)

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        'format': 'csv',
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
