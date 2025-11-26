
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TelemetryParser:
    """Parse CSV telemetry packets or Status messages from Arduino receiver"""

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
        self.config = config or {}
        self.packet_count = 0

        self.key_map = {}
        for lbl in self.DATA_LABELS:
            self.key_map[lbl] = self._sanitize_label(lbl)

        logger.info(f"Telemetry parser initialized.")

    def _sanitize_label(self, label: str) -> str:
        s = label.lower()
        s = re.sub(r'[^a-z0-9]+', '_', s)
        s = re.sub(r'__+', '_', s)
        return s.strip('_')

    def parse(self, raw_data: str) -> Optional[Dict[str, Any]]:
        if isinstance(raw_data, bytes):
            try:
                raw_data = raw_data.decode('utf-8').strip()
            except UnicodeDecodeError:
                return None
        else:
            raw_data = raw_data.strip()

        if not raw_data:
            return None

        if "Waiting for GPS Fix" in raw_data:
            telemetry = {k: 0.0 for k in self.key_map.values()}
            telemetry['timestamp'] = datetime.now().isoformat()
            telemetry['sys_status'] = 'waiting'
            parts = raw_data.split(',')
            if len(parts) > 1:
                try:
                    rssi_key = self.key_map['RSSI']
                    telemetry[rssi_key] = float(parts[-1])
                except ValueError:
                    pass
            return telemetry

        try:
            values = raw_data.split(',')
            expected_len = len(self.DATA_LABELS)

            if len(values) not in [expected_len, expected_len - 1]:
                if len(values) > 3:
                    logger.warning(f"Bad packet length: Expected {expected_len}, got {len(values)}.")
                return None

            telemetry = {
                'timestamp': datetime.now().isoformat(),
                'packet_count': self.packet_count,
                'sys_status': 'active'
            }

            for i, label in enumerate(self.DATA_LABELS):
                key = self.key_map[label]
                if i >= len(values):
                    telemetry[key] = 0.0
                    continue

                try:
                    val_str = values[i].strip()
                    if label in ["GPS Fix", "GPS Sats"]:
                        telemetry[key] = int(float(val_str))
                    else:
                        telemetry[key] = float(val_str)
                except (ValueError, IndexError):
                    telemetry[key] = 0.0

            rounding_map = {
                "gps_lat": 6, "gps_lon": 6, "gps_alt_m": 2,
                "vbat": 3, "imu_temp_c": 2, "pressure_pa": 2,
                "altitude": 2, "velocity": 2,
            }
            for k, p in rounding_map.items():
                if k in telemetry:
                    telemetry[k] = round(telemetry[k], p)

            self.packet_count += 1
            return telemetry

        except Exception as e:
            logger.error(f"Parser error: {e}")
            return None
