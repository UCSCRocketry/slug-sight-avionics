# Data Directory

This directory contains flight data logged by the ground station.

## Directory Structure

```
data/
├── flights/          # CSV flight data files (timestamped)
│   └── .gitkeep      # Keeps directory in git
└── raw/              # Raw binary packet backups (optional)
    └── .gitkeep      # Keeps directory in git
```

## Git Ignore Rules

All data files are **automatically ignored by git** and will NOT be committed:

- `data/flights/*.csv` - Flight telemetry CSV files
- `data/flights/*.json` - Any JSON files (not used anymore)
- `data/raw/*` - Raw packet data

Only the `.gitkeep` files are tracked to preserve the directory structure.

## Flight Data Files

When you run the ground station (`python app.py`), it creates CSV files with timestamps:

```
data/flights/2025-11-06_14-16-09.csv
data/flights/2025-11-06_15-30-42.csv
data/flights/2025-11-07_10-05-18.csv
```

Each file contains telemetry from one ground station session.

## CSV Format

Example CSV contents:

```csv
timestamp,altitude,pressure,temperature,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,mag_x,mag_y,mag_z,gps_lat,gps_lon,gps_alt,gps_satellites,state,packet_num,ground_rssi
0.100,0.500,101325.0,20.5,0.0,0.0,9.81,0.0,0.0,0.0,25.0,10.0,-30.0,37.0,-122.0,155.0,0,PAD,1,-85
0.200,0.600,101324.8,20.5,0.0,0.0,9.80,0.0,0.0,0.0,25.0,10.0,-30.0,37.0,-122.0,155.0,0,PAD,2,-84
0.300,10.300,101200.5,20.3,2.5,1.2,25.45,0.5,0.2,0.1,25.1,10.1,-30.1,37.0,-122.0,155.1,8,BOOST,3,-83
```

## Backing Up Flight Data

Since flight data is **not committed to git**, make sure to:

1. **Back up important flights** to a separate location
2. **Use cloud storage** (Google Drive, Dropbox, etc.)
3. **Copy to external drive** before cleaning up

## Cleaning Up Old Data

To free up disk space:

```bash
# Delete old CSV files (BE CAREFUL!)
rm data/flights/*.csv

# Or move to archive
mkdir ~/flight-data-archive
mv data/flights/*.csv ~/flight-data-archive/
```

## File Locations

- Ground station config: `config/ground_config.yaml`
- Output directory setting:
  ```yaml
  data_logging:
    output_directory: "./data/flights"
  ```

---

**Remember:** Flight data files are ignored by git, so they won't clutter your repository or show up in `git status`! ✅
