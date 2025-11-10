"""
Telemetry Parser

Parses CSV telemetry data from the rocket receiver into structured telemetry data.
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TelemetryParser:
	"""Parse CSV telemetry packets from Arduino receiver"""
	
	# 18-POINT DATA CONTRACT (17 from TX + RSSI from RX)
	DATA_LABELS = [
		"Pitch", "Roll", "Yaw",
		"Altitude", "Velocity",
		"Accel X", "Accel Y", "Accel Z",
		"Pressure Pa", "IMU Temp C",
		"GPS Fix", "GPS Sats",
		"GPS Lat", "GPS Lon", "GPS Alt m", "GPS Speed m/s",
		"VBat", "RSSI"
	]
	
	def __init__(self, config: dict = None):
		"""
		Initialize telemetry parser
		
		Args:
			config: Telemetry configuration dictionary (optional)
		"""
		self.config = config or {}
		self.packet_count = 0

		# Build a mapping from human labels to normalized safe keys for downstream use (snake_case)
		self.key_map = {}
		for lbl in self.DATA_LABELS:
			self.key_map[lbl] = self._sanitize_label(lbl)
		
		logger.info(f"Telemetry parser initialized for CSV format with {len(self.DATA_LABELS)} fields")
	
	def _sanitize_label(self, label: str) -> str:
		"""Convert human label into a stable snake_case key (e.g., 'GPS Lat' -> 'gps_lat')"""
		# Lowercase, replace non-alphanum with underscore, collapse underscores
		s = label.lower()
		s = re.sub(r'[^a-z0-9]+', '_', s)
		s = re.sub(r'__+', '_', s)
		return s.strip('_')
	
	def parse(self, raw_data: str) -> Optional[Dict[str, Any]]:
		"""
		Parse CSV string into telemetry dictionary
		
		Args:
			raw_data: CSV string from receiver (e.g., "1.5,2.3,45.6,...")
			
		Returns:
			Dictionary of telemetry values, or None if parsing fails
		"""
		# Handle both string and bytes input
		if isinstance(raw_data, bytes):
			try:
				raw_data = raw_data.decode('utf-8').strip()
			except UnicodeDecodeError as e:
				logger.error(f"Failed to decode telemetry bytes: {e}")
				return None
		else:
			raw_data = raw_data.strip()
		
		if not raw_data:
			return None
		
		try:
			# Split CSV string
			values = raw_data.split(',')
			
			# Verify we have the correct number of fields
			if len(values) != len(self.DATA_LABELS):
				logger.warning(f"Incorrect field count: expected {len(self.DATA_LABELS)}, got {len(values)}")
				return None
			
			# Build telemetry dictionary with normalized keys
			telemetry = {
				'timestamp': datetime.now().isoformat(),
				'packet_count': self.packet_count
			}
			
			# Parse each field into normalized key
			for i, label in enumerate(self.DATA_LABELS):
				key = self.key_map[label]
				try:
					# Convert to appropriate type
					if label in ["GPS Fix", "GPS Sats"]:
						# Integer fields
						telemetry[key] = int(float(values[i]))
					else:
						# Float fields
						telemetry[key] = float(values[i])
				except (ValueError, IndexError) as e:
					logger.warning(f"Failed to parse field '{label}' with value '{values[i] if i < len(values) else None}': {e}")
					telemetry[key] = 0.0

			# --- NEW: Apply sensible rounding for certain fields for consistent logs ---
			# Keep numeric types (floats/ints), but round to reasonable precision
			rounding_map = {
				self._sanitize_label("GPS Lat"): 6,
				self._sanitize_label("GPS Lon"): 6,
				self._sanitize_label("GPS Alt m"): 2,
				self._sanitize_label("VBat"): 3,
				self._sanitize_label("IMU Temp C"): 2,
				self._sanitize_label("Pressure Pa"): 2,
				self._sanitize_label("Altitude"): 2,
				self._sanitize_label("Velocity"): 2,
			}
			for key, prec in rounding_map.items():
				if key in telemetry and isinstance(telemetry[key], float):
					telemetry[key] = round(telemetry[key], prec)

			# Validate ranges (if enabled)
			if self.config.get('validation', {}).get('enable_range_check', False):
				if not self._validate_ranges(telemetry):
					logger.warning("Telemetry values out of range")
					return None

			self.packet_count += 1
			return telemetry
			
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
			# Accept either original label names or normalized keys in the config
			if field in telemetry:
				value = telemetry.get(field)
			else:
				# Try sanitizing the config field name to find matching telemetry key
				sanit = self._sanitize_label(field)
				value = telemetry.get(sanit)
			
			if value is not None:
				try:
					if not (min_val <= value <= max_val):
						logger.warning(f"{field} out of range: {value}")
						return False
				except TypeError:
					# In case types are mismatched, consider invalid
					logger.warning(f"Type error validating {field}: {value}")
					return False
		
		return True

# Example usage
if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	
	# Test configuration (note: ranges can use original labels or normalized keys)
	test_config = {
		'validation': {
			'enable_range_check': True,
			'ranges': {
				'Altitude': [-100, 50000],
				'Pressure Pa': [10000, 110000],
				'IMU Temp C': [-50, 100]
			}
		}
	}
	
	parser = TelemetryParser(test_config)
	
	# Create a test CSV string (18 values)
	test_csv = "5.2,-3.1,45.8,125.5,15.3,0.5,0.2,9.8,101325.0,22.5,1,8,37.123456,-122.345678,130.2,12.5,3.85,-95"
	
	result = parser.parse(test_csv)
	if result:
		print("Parsed telemetry:")
		for key, value in result.items():
			print(f"  {key}: {value}")
	else:
		print("Failed to parse telemetry")
