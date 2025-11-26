
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import pytz

logger = logging.getLogger(__name__)

class DataLogger:
    """Log telemetry data to CSV files"""

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = Path(config.get('output_directory', './flight_data'))
        self.csv_file = None
        self.csv_writer = None
        self.current_filename = None
        self.pacific_tz = pytz.timezone('America/Los_Angeles')

        if config.get('auto_create_directory', True):
            self.output_dir.mkdir(parents=True, exist_ok=True)

        self._initialize_file()

    def _initialize_file(self):
        # Get current time in Pacific Time
        timestamp = datetime.now(self.pacific_tz)
        filename_format = self.config.get('filename_format', '%Y-%m-%d_%H-%M-%S')
        filename_base = timestamp.strftime(filename_format)

        self.current_filename = self.output_dir / f"slugsight_{filename_base}.csv"
        self.csv_file = open(self.current_filename, 'w', newline='', encoding='utf-8')
        self.csv_writer = None
        logger.info(f"Logging to CSV: {self.current_filename}")

    def write(self, telemetry: Dict[str, Any]):
        self._write_csv(telemetry)

    def _write_csv(self, telemetry: Dict[str, Any]):
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

        formatted_telemetry = self._format_floats(telemetry)
        self.csv_writer.writerow(formatted_telemetry)

        if hasattr(self, '_write_count'):
            self._write_count += 1
        else:
            self._write_count = 1

        flush_interval = self.config.get('buffer_size', 10)
        if self._write_count % flush_interval == 0:
            self.csv_file.flush()

    def _format_floats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        precision = self.config.get('csv', {}).get('float_precision', 6)
        formatted = {}

        for key, value in data.items():
            if isinstance(value, float):
                formatted[key] = round(value, precision);
            else:
                formatted[key] = value

        return formatted

    def flush(self):
        if self.csv_file:
            self.csv_file.flush()

    def close(self):
        if self.current_filename:
            logger.info(f"Closing log file: {self.current_filename}")

        if self.csv_file:
            self.csv_file.flush()
            self.csv_file.close()

    def get_current_file(self) -> str:
        return str(self.current_filename) if self.current_filename else ""
