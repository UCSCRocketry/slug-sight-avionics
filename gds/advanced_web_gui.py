import serial
import serial.tools.list_ports
import threading
import time
import json
import logging
from datetime import datetime
from flask import Flask, render_template_string, request
from flask_sock import Sock

# --- Project Imports ---
from telemetry_parser import TelemetryParser
from data_logger import DataLogger

# --- Configuration ---
ARDUINO_VID_PIDS = [
    (0x2341, 0x0043),  # Official Arduino Uno R3
    (0x2341, 0x0001),  # Another Arduino ID
    (0x1A86, 0x7523),  # Common CH340 clone (Nano, etc.)
    (0x239A, 0x8022),  # Adafruit Feather M4 (if used as receiver)
]

# --- Global variables ---
# We will initialize global_data in main() using the parser's labels
global_data = {} 
global_status = {
    "arduino_connected": False,
    "port": "Not Found"
}
data_lock = threading.Lock()
global_clients = []

# --- Part 1: Serial Reader Thread (Reworked) ---

def find_arduino_port():
    """Finds the GCS Receiver Arduino port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        for vid, pid in ARDUINO_VID_PIDS:
            if port.vid == vid and port.pid == pid:
                print(f"Found GCS Receiver on port: {port.device}")
                return port.device
    return None

def serial_reader_thread(port: str, parser: TelemetryParser, datalogger: DataLogger, reverse_key_map: dict):
    """
    Reads serial data, parses it, logs it, and prepares it for broadcast.
    
    Args:
        port: The serial port name (or "NOT_FOUND").
        parser: Instance of TelemetryParser.
        datalogger: Instance of DataLogger.
        reverse_key_map: A dict to map normalized keys (e.g., 'gps_lat')
                         back to GUI labels (e.g., 'GPS Lat').
    """
    global global_data, global_status, global_clients
    while True: # Connection loop
        if port == "NOT_FOUND":
            print("Serial port not found. Retrying in 5 seconds...")
            time.sleep(5)
            port = find_arduino_port() or "NOT_FOUND"
            if port != "NOT_FOUND":
                with data_lock:
                    global_status["port"] = port
            continue

        print(f"Attempting to connect to serial port {port}...")
        ser = None
        try:
            with serial.Serial(port, 115200, timeout=1) as ser:
                print(f"Serial connection to {port} established.")
                with data_lock:
                    global_status["arduino_connected"] = True
                
                while True: # Read loop
                    try:
                        line = ser.readline()
                        if not line:
                            continue # Timeout, just read again
                        
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue

                        # 1. Parse the raw string using TelemetryParser
                        parsed_telemetry = parser.parse(line_str)
                        
                        # 2. If parsing fails (returns None), skip this packet
                        if not parsed_telemetry:
                            logging.warning(f"Discarding bad packet: {line_str}")
                            continue # Bad packet, silently ignore

                        # 3. Log the valid, structured data
                        datalogger.write(parsed_telemetry)

                        # 4. Update global_data for the GUI and build payload
                        payload = None
                        with data_lock:
                            # Update global_data using the reverse map
                            # This updates the data store that the websocket sends
                            for key, value in parsed_telemetry.items():
                                if key in reverse_key_map:
                                    label = reverse_key_map[key]
                                    global_data[label] = str(value) # GUI expects strings
                            
                            # Create payload
                            payload = json.dumps({
                                "type": "update",
                                "status": global_status, 
                                "data": global_data
                            })
                        
                        # 5. Broadcast the payload (outside data_lock)
                        if payload: 
                            current_clients_copy = []
                            with data_lock:
                                current_clients_copy = list(global_clients) 

                            dead_clients = []
                            for client in current_clients_copy: 
                                try:
                                    client.send(payload)
                                except Exception as e:
                                    dead_clients.append(client)
                                    
                            if dead_clients:
                                with data_lock:
                                    for client in dead_clients:
                                        if client in global_clients:
                                            global_clients.remove(client)

                    except serial.SerialException as e:
                        print(f"Serial error (disconnect?): {e}")
                        port = "NOT_FOUND" # Trigger port re-find
                        break # Break inner 'Read loop'
                    except UnicodeDecodeError:
                        pass # Garbled data, skip line
                    except Exception as e:
                        print(f"Unexpected error in read loop: {e}")
                        time.sleep(1) 

        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            port = "NOT_FOUND" # Trigger port re-find
        except Exception as e:
            print(f"An unexpected error occurred in connection loop: {e}")
        finally:
            if ser and ser.is_open:
                ser.close()
            with data_lock:
                global_status["arduino_connected"] = False
            print("Retrying connection in 5 seconds...")
            time.sleep(5)


# --- Part 2: Web Server (Flask) ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SlugSight Ground Station</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@400;700&display.swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    
    <style>
        :root {
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-family-mono: 'Roboto Mono', 'Courier New', Courier, monospace;
            --bg-color: #f0f2f5;
            --card-bg: #ffffff;
            --text-color: #1c1e21;
            --text-secondary: #606770;
            --primary-color: #0d6efd;
            --purple-accent: #6f42c1; /* Added purple for gradient */
            --border-color: #e0e0e0;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            --shadow-hover: 0 6px 16px rgba(0, 0, 0, 0.12);
            --navbar-bg: #ffffff;
            --status-bg: #ffffff;
            --status-text: #606770;
            --status-connected: #28a745;
            --status-disconnected: #dc3545;
            --red-accent: #e74c3c;
            --log-bg: #f8f9fa;
        }

        body.dark-mode {
            --bg-color: #18191a;
            --card-bg: #242526;
            --text-color: #e4e6eb;
            --text-secondary: #b0b3b8;
            --primary-color: #409CFF;
            --purple-accent: #9370DB;
            --border-color: #3e4042;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            --shadow-hover: 0 6px 16px rgba(0, 0, 0, 0.3);
            --navbar-bg: #242526;
            --status-bg: #242526;
            --status-text: #b0b3b8;
            --red-accent: #FF6347;
            --log-bg: #1c1c1c;
        }

        body {
            font-family: var(--font-family);
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding-top: 70px;
            padding-bottom: 50px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        
        nav {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 60px;
            background-color: var(--navbar-bg);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            padding: 0 25px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 1000;
            border-bottom: 1px solid var(--border-color);
            transition: background-color 0.3s ease;
        }
        .nav-title {
            font-size: 1.5em;
            font-weight: 700;
            color: var(--primary-color);
        }
        
        .nav-status {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .nav-item {
            font-family: var(--font-family-mono);
            font-size: 0.9em;
            font-weight: 500;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
        }
        .nav-item .material-icons-outlined {
            font-size: 1.2em;
            vertical-align: -4px;
            margin-right: 6px;
        }
        #vbat-display.low-bat, #rssi-display.low-rssi {
            color: var(--red-accent);
            font-weight: 700;
        }
        
        .settings-menu {
            position: relative;
        }
        .settings-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            display: flex; 
            align-items: center;
            justify-content: center;
            color: var(--text-secondary); /* Icon color */
        }
        .settings-btn:hover {
            background-color: rgba(0,0,0,0.05);
        }
        body.dark-mode .settings-btn:hover {
            background-color: rgba(255,255,255,0.1);
        }
        .settings-dropdown {
            display: none;
            position: absolute;
            top: 45px;
            right: 0;
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border-color);
            width: 220px;
            z-index: 1001;
            padding: 10px;
        }
        .settings-dropdown.show {
            display: block;
        }
        .setting-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            font-size: 0.9em;
            color: var(--text-color);
        }
        .setting-item label {
            font-weight: 500;
        }
        .setting-item button {
            background: none;
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            text-align: left;
            font-size: 1em;
            font-family: var(--font-family);
            font-weight: 500;
        }
        .setting-item button:hover {
            border-color: var(--primary-color);
            background-color: rgba(0,0,0,0.05);
        }
        .setting-item select {
            padding: 5px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
            background-color: var(--bg-color);
            color: var(--text-color);
        }
        
        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }
        .switch input { display: none; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 24px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .slider {
            background-color: var(--primary-color);
        }
        input:checked + .slider:before {
            transform: translateX(20px);
        }

        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 40px;
            background-color: var(--status-bg);
            border-top: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 25px;
            z-index: 1000;
            transition: background-color 0.3s ease;
        }
        #arduino-status {
            font-weight: 600;
            color: var(--status-disconnected);
        }
        #arduino-status.connected {
            color: var(--status-connected);
        }
        #arduino-status::before {
            content: '●';
            margin-right: 8px;
            font-size: 1.2em;
        }
        #port-name {
            font-size: 0.9em;
            color: var(--text-secondary);
            margin-left: 15px;
        }
        
        h1 {
            text-align: center;
            color: var(--text-color);
            font-weight: 700;
            margin-top: 10px;
        }
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 20px auto;
        }
        .card {
            background-color: var(--card-bg);
            border-radius: 12px;
            box-shadow: var(--shadow);
            padding: 25px;
            transition: box-shadow 0.3s ease, background-color 0.3s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .card:hover {
            box-shadow: var(--shadow-hover);
        }
        .card-title {
            font-size: 1.1em;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 15px;
            text-align: center;
        }
        .value-display {
            font-size: 2.8em;
            font-weight: 700;
            color: var(--primary-color);
        }
        .unit {
            font-size: 1.2em;
            font-weight: 500;
            color: var(--text-secondary);
            margin-left: 8px;
        }
        
        .bubble-level {
            width: 150px;
            height: 150px;
            border: 3px solid var(--border-color);
            border-radius: 50%;
            position: relative;
            background: 
                radial-gradient(circle at 50% 50%, transparent 45%, var(--border-color) 45%, var(--border-color) 46%, transparent 46%),
                linear-gradient(to right, var(--border-color) 1px, transparent 1px) 50% 0,
                linear-gradient(to bottom, var(--border-color) 1px, transparent 1px) 0 50%;
            background-size: 100% 100%, 100% 10px, 10px 100%;
            background-repeat: no-repeat, repeat-y, repeat-x;
            transition: border-color 0.3s ease;
        }
        #bubble-ball {
            width: 25px;
            height: 25px;
            background-color: var(--primary-color);
            border-radius: 50%;
            position: absolute;
            top: 50%;
            left: 50%;
            margin-left: -12.5px;
            margin-top: -12.5px;
            border: 2px solid white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            transition: transform 0.1s linear, background-color 0.3s ease;
        }
        #accel-z-value {
            font-size: 1.2em;
            margin-top: 15px;
            color: var(--text-secondary);
        }

        .compass {
            width: 150px;
            height: 150px;
            border: 3px solid var(--border-color);
            border-radius: 50%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: border-color 0.3s ease;
        }
        .compass-rose {
            font-size: 1em;
            font-weight: 600;
            color: var(--text-secondary);
            position: absolute;
            transition: color 0.3s ease;
        }
        .rose-n { top: 5px; }
        .rose-s { bottom: 5px; }
        .rose-e { right: 10px; }
        .rose-w { left: 10px; }
        #compass-needle {
            width: 0;
            height: 0;
            border-left: 6px solid transparent;
            border-right: 6px solid transparent;
            border-bottom: 60px solid var(--red-accent);
            position: absolute;
            top: 15px;
            left: 50%;
            margin-left: -6px;
            transform-origin: 50% 60px;
            transition: transform 0.2s ease-out, border-bottom-color 0.3s ease;
            z-index: 10;
        }
        #compass-heading {
            font-size: 1.2em;
            margin-top: 15px;
            color: var(--text-secondary);
        }
        
        #p-gps {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto;
            gap: 15px;
            width: 100%;
            text-align: left;
        }
        .gps-readout { display: flex; flex-direction: column; }
        .gps-label { font-size: 0.8em; color: var(--text-secondary); text-transform: uppercase; }
        .gps-value {
            font-family: var(--font-family-mono);
            font-size: 1.2em;
            font-weight: 500;
            color: var(--text-color);
        }
        #data-fix-status { color: var(--red-accent); }
        #data-fix-status.locked { color: var(--status-connected); }
        
        /* --- Log Panel (Modal) --- */
        .log-overlay-bg {
            display: none; /* Hidden by default */
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5); /* Shadow effect */
            z-index: 1004;
        }
        .log-overlay-bg.show {
            display: block;
        }

        .log-panel {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%); /* Center it */
            width: 80%; /* Modal width */
            max-width: 900px; /* Max width */
            z-index: 1005; 
            max-height: 60vh; /* Max height */
            flex-direction: column;
            display: none; /* Hidden by default */
        }
        .log-panel.show {
            display: flex; /* Show as flex container */
        }
        
        .log-close-btn {
            position: absolute;
            top: 10px;
            right: 20px;
            background: none;
            border: none;
            font-size: 2.5em;
            font-weight: 300;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }
        .log-close-btn:hover {
            color: var(--text-color);
        }
        
        #log-panel-body {
            background-color: var(--log-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            height: auto; /* Remove fixed height */
            flex-grow: 1; /* Allow it to fill space */
            overflow-y: scroll; /* Enable vertical scroll *inside* the panel */
            font-family: var(--font-family-mono);
            font-size: 0.9em;
            color: var(--text-secondary);
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }
        .log-entry {
            padding: 2px 0;
            border-bottom: 1px dashed var(--border-color);
            white-space: pre-wrap;
            word-break: break-all;
        }
        .log-time {
            color: var(--primary-color);
            margin-right: 10px;
        }
        .log-status { font-weight: bold; }
        .log-status.connected { color: var(--status-connected); }
        .log-status.disconnected { color: var(--status-disconnected); }
    </style>
</head>
<body>
    <div class="log-overlay-bg" id="log-overlay-bg"></div>

    <nav>
        <div class="nav-title">SlugSight Sensor Dashboard</div>
        
        <div class="nav-status">
            <span class="nav-item" id="vbat-display">
                <span class="material-icons-outlined">battery_unknown</span>
                <span>--% (-- V)</span>
            </span>
            
            <span class="nav-item" id="rssi-display">
                <span class="material-icons-outlined">signal_cellular_off</span>
                <span>-- dBm</span>
            </span>
        
            <div class="settings-menu">
                <button class="settings-btn" id="settings-btn" aria-label="Settings">
                    <span class="material-icons-outlined">settings</span>
                </button>
                <div class="settings-dropdown" id="settings-dropdown">
                    <div class="setting-item">
                        <label for="dark-mode-toggle">Dark Mode</label>
                        <label class="switch">
                            <input type="checkbox" id="dark-mode-toggle">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div class="setting-item">
                        <label for="update-rate">UI Update Rate</label>
                        <select id="update-rate">
                            <option value="0">Real-time (10 Hz)</option>
                            <option value="200">5 Hz (0.2s)</option>
                            <option value="500" selected>2 Hz (0.5s)</option>
                            <option value="1000">1 Hz (1.0s)</option>
                        </select>
                    </div>
                    <div class="setting-item">
                        <button id="log-toggle-btn">Show Event Log</button>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <h1>Feather M4 LoRa Sensor Dashboard</h1>
    <div class="grid-container">
        <div class="card">
            <div class="card-title">Accelerometer (Tilt)</div>
            <div class="bubble-level">
                <div id="bubble-ball"></div>
            </div>
            <div id="accel-z-value">Z: 0.00 g</div>
        </div>

        <div class="card">
            <div class="card-title">Magnetometer (Compass)</div>
            <div class="compass">
                <div class="compass-rose rose-n">N</div>
                <div class="compass-rose rose-s">S</div>
                <div class="compass-rose rose-e">E</div>
                <div class="compass-rose rose-w">W</div>
                <div id="compass-needle"></div>
            </div>
            <div id="compass-heading">0°</div>
        </div>

        <div class="card">
            <div class="card-title">Atmospheric Pressure</div>
            <canvas id="pressure-gauge"></canvas>
            <div id="pressure-value" class="value-display" style="font-size: 2em; margin-top: -15px;">0 <span class="unit" style="font-size: 0.8em;">Pa</span></div>
        </div>

        <div class="card">
            <div class="card-title">IMU Temperature</div>
            <div class="value-display"><span id="bmp-temp-value">0.00</span><span class="unit">°C</span></div>
        </div>

        <div class="card">
            <div class="card-title">Altitude</div>
            <div class="value-display"><span id="bmp-alt-value">0.00</span><span class="unit">m</span></div>
        </div>
        
        <div class="card">
            <div class="card-title">Pitch</div>
            <canvas id="gyro-x-gauge"></canvas>
            <div id="gyro-x-value" class="value-display" style="font-size: 2em; margin-top: -15px;">0 <span class="unit" style="font-size: 0.8em;">deg</span></div>
        </div>

        <div class="card">
            <div class="card-title">Roll</div>
            <canvas id="gyro-y-gauge"></canvas>
            <div id="gyro-y-value" class="value-display" style="font-size: 2em; margin-top: -15px;">0 <span class="unit" style="font-size: 0.8em;">deg</span></div>
        </div>
        
        <div class="card">
            <div class="card-title">GPS Status</div>
            <div id="p-gps">
                <div class="gps-readout">
                    <div class="gps-label">Fix Status</div>
                    <div class="gps-value" id="data-fix-status">No Fix</div>
                </div>
                <div class="gps-readout">
                    <div class="gps-label">Satellites</div>
                    <div class="gps-value" id="data-sats">0</div>
                </div>
                <div class="gps-readout">
                    <div class="gps-label">Latitude</div>
                    <div class="gps-value" id="data-lat">0.000000</div>
                </div>
                <div class="gps-readout">
                    <div class="gps-label">Longitude</div>
                    <div class="gps-value" id="data-lon">0.000000</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="log-panel card" id="log-panel">
        <button class="log-close-btn" id="log-close-btn">&times;</button>
        <div class="card-title">Event Log</div>
        <div id="log-panel-body"></div>
    </div>
    
    <div class="status-bar">
        <span id="arduino-status">Connecting...</span>
        <span id="port-name"></span>
    </div>

    <script>
        // All JavaScript is unchanged
        // --- Global State ---
        let chartObjects = {};
        let currentUpdateRate = 500;
        let lastUpdateTime = 0;
        
        // --- JS Color Definitions ---
        const THEME_COLORS = {
            dark: {
                primary: '#409CFF',
                purple: '#9370DB',
                border: '#3e4042',
                red: '#FF6347'
            },
            light: {
                primary: '#0d6efd',
                purple: '#6f42c1',
                border: '#e0e0e0',
                red: '#e74c3c'
            }
        };

        // --- Chart.js Gauge Configuration ---
        const gaugeConfig = (min, max, label) => ({
            type: 'doughnut',
            data: {
                labels: [label, ''],
                datasets: [{
                    data: [0, max - min],
                    backgroundColor: [
                        THEME_COLORS.light.primary, // Default light mode
                        THEME_COLORS.light.border
                    ],
                    borderColor: 'rgba(0,0,0,0)',
                    borderWidth: 0,
                    circumference: 180,
                    rotation: -90,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2,
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                animation: { duration: 0 }
            }
        });
        
        // --- updateGauge function (unchanged) ---
        function updateGauge(chart, value, min, max, elementId, unit) {
            if (!chart) return;
            const val = parseFloat(value) || 0.0;
            const clampedVal = Math.max(min, Math.min(val, max));
            const dataValue = clampedVal - min;
            const range = max - min;
            
            chart.data.datasets[0].data[0] = dataValue;
            chart.data.datasets[0].data[1] = range - dataValue;
            
            const ctx = chart.ctx;
            const chartArea = chart.chartArea;
            
            if (chartArea) {
                const isDarkMode = document.body.classList.contains('dark-mode');
                const theme = isDarkMode ? THEME_COLORS.dark : THEME_COLORS.light;

                const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                gradient.addColorStop(0, theme.primary);
                gradient.addColorStop(1, theme.purple);
                chart.data.datasets[0].backgroundColor[0] = gradient;
                chart.data.datasets[0].backgroundColor[1] = theme.border;
            }
            
            chart.update('none');
            
            document.getElementById(elementId).innerHTML = `${val.toFixed(2)} <span class="unit" style="font-size: 0.8em;">${unit}</span>`;
        }
        
        // --- Initialize Charts (unchanged) ---
        function initializeCharts() {
            chartObjects.pressureGauge = new Chart(
                document.getElementById('pressure-gauge').getContext('2d'),
                gaugeConfig(90000, 105000, 'Pressure')
            );
            
            chartObjects.pitchGauge = new Chart(
                document.getElementById('gyro-x-gauge').getContext('2d'),
                gaugeConfig(-90, 90, 'Pitch')
            );
            chartObjects.rollGauge = new Chart(
                document.getElementById('gyro-y-gauge').getContext('2d'),
                gaugeConfig(-180, 180, 'Roll')
            );
            
            let imuTempCard = document.querySelector('#imu-temp-value');
            if (imuTempCard) imuTempCard.closest('.card').style.display = 'none';
        }

        // --- Battery Percentage Helper (unchanged) ---
        function voltageToPercentage(v) {
            const minV = 3.2;
            const maxV = 4.2;
            let percent = (v - minV) / (maxV - minV);
            percent = Math.max(0, Math.min(1, percent));
            return Math.round(percent * 100);
        }
        
        // --- Log Panel Function (unchanged) ---
        const logPanelBody = document.getElementById('log-panel-body');
        function logToPanel(message, type = 'data') {
            if (!logPanelBody) return;
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.classList.add('log-entry');
            let statusClass = '';
            if (type === 'connect') statusClass = 'log-status connected';
            if (type === 'disconnect') statusClass = 'log-status disconnected';
            
            entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="${statusClass}">${message}</span>`;
            
            logPanelBody.appendChild(entry);
            logPanelBody.scrollTop = logPanelBody.scrollHeight;
        }

        // --- Status Update Function (unchanged) ---
        let lastConnectionState = false;
        function updateStatus(status) {
            const statusEl = document.getElementById('arduino-status');
            const portEl = document.getElementById('port-name');
            
            if (status.arduino_connected) {
                statusEl.textContent = 'Connected';
                statusEl.classList.add('connected');
                portEl.textContent = `on ${status.port}`;
                if (!lastConnectionState) {
                    logToPanel("Connection established", "connect");
                    lastConnectionState = true;
                }
            } else {
                statusEl.textContent = 'Disconnected';
                statusEl.classList.remove('connected');
                portEl.textContent = `(${status.port})`;
                if (lastConnectionState) {
                    logToPanel("Connection lost", "disconnect");
                    lastConnectionState = false;
                }
            }
        }

        // --- GUI Update Function (unchanged) ---
        function updateGUI(data, timestamp) {
            try {
                // --- 1. Update Top Bar ---
                const vbat = parseFloat(data['VBat']) || 0.0;
                const rssi = parseFloat(data['RSSI']) || 0.0; 
                const vbatEl = document.getElementById('vbat-display').querySelector('span:last-child');
                const rssiEl = document.getElementById('rssi-display').querySelector('span:last-child');
                const vbatIcon = document.getElementById('vbat-display').querySelector('span:first-child');
                const rssiIcon = document.getElementById('rssi-display').querySelector('span:first-child');

                const percent = voltageToPercentage(vbat);
                let batIcon = 'battery_full';
                vbatEl.parentElement.classList.remove('low-bat');

                if (percent < 10) { batIcon = 'battery_alert'; vbatEl.parentElement.classList.add('low-bat'); }
                else if (percent < 25) { batIcon = 'battery_1_bar'; }
                else if (percent < 50) { batIcon = 'battery_3_bar'; }
                else if (percent < 75) { batIcon = 'battery_5_bar'; }
                vbatIcon.textContent = batIcon;
                vbatEl.textContent = ` ${percent}% (${vbat.toFixed(2)} V)`;

                let rssiStr = 'signal_cellular_4_bar'; 
                rssiEl.parentElement.classList.remove('low-rssi');
                if (rssi < -100) { rssiStr = 'signal_cellular_0_bar'; rssiEl.parentElement.classList.add('low-rssi'); }
                else if (rssi < -90) { rssiStr = 'signal_cellular_1_bar'; }
                else if (rssi < -80) { rssiStr = 'signal_cellular_2_bar'; }
                else if (rssi < -70) { rssiStr = 'signal_cellular_3_bar'; }
                rssiIcon.textContent = rssiStr;
                rssiEl.textContent = ` ${rssi.toFixed(0)} dBm`;


                // --- 2. Simple Text Values ---
                document.getElementById('bmp-temp-value').textContent = (parseFloat(data['IMU Temp C']) || 0.0).toFixed(2);
                document.getElementById('bmp-alt-value').textContent = (parseFloat(data['Altitude']) || 0.0).toFixed(2);
                document.getElementById('accel-z-value').textContent = `Z: ${(parseFloat(data['Accel Z']) || 0.0).toFixed(2)} g`;

                // --- 3. Bubble Level ---
                const accel_x = parseFloat(data['Accel X']) || 0.0;
                const accel_y = parseFloat(data['Accel Y']) || 0.0;
                
                const clamp = (val, min, max) => Math.max(min, Math.min(val, max));
                const maxPixelMove = 60; 
                const xPos = clamp(accel_x * (maxPixelMove / 1.0), -maxPixelMove, maxPixelMove);
                const yPos = clamp(-accel_y * (maxPixelMove / 1.0), -maxPixelMove, maxPixelMove);
                
                document.getElementById('bubble-ball').style.transform = `translate(${xPos}px, ${yPos}px)`;

                // --- 4. Compass ---
                let yaw = parseFloat(data['Yaw']) || 0.0;
                if (yaw < 0) yaw += 360; 
                let heading_for_needle = yaw - 90;
                
                document.getElementById('compass-needle').style.transform = `rotate(${heading_for_needle}deg)`;
                document.getElementById('compass-heading').textContent = `${yaw.toFixed(0)}°`;

                // --- 5. Gauges ---
                updateGauge(chartObjects.pressureGauge, data['Pressure Pa'], 90000, 105000, 'pressure-value', 'Pa');
                updateGauge(chartObjects.pitchGauge, data['Pitch'], -90, 90, 'gyro-x-value', 'deg');
                updateGauge(chartObjects.rollGauge, data['Roll'], -180, 180, 'gyro-y-value', 'deg');
                
                // --- 6. GPS Panel ---
                const fix = parseInt(data['GPS Fix'], 10) || 0;
                const fixEl = document.getElementById('data-fix-status');
                if (fix > 0) {
                    fixEl.textContent = '3D Fix Locked';
                    fixEl.classList.add('locked');
                } else {
                    fixEl.textContent = 'No Fix';
                    fixEl.classList.remove('locked');
                }
                document.getElementById('data-sats').textContent = data['GPS Sats'] || 0;
                document.getElementById('data-lat').textContent = (parseFloat(data['GPS Lat']) || 0.0).toFixed(6);
                document.getElementById('data-lon').textContent = (parseFloat(data['GPS Lon']) || 0.0).toFixed(6);
                
                // --- 7. Log Raw Data ---
                logToPanel(JSON.stringify(data));

            } catch (error) {
                console.error("Error updating GUI:", error);
                logToPanel(`Error: ${error.message}`, 'disconnect');
            }
        }
        
        // --- WebSocket Connection (unchanged) ---
        function connectWebSocket() {
            const wsProtocol = window.location.protocol === "https" ? "wss" : "ws";
            const wsURL = `${wsProtocol}://${window.location.host}/ws`;
            const ws = new WebSocket(wsURL);

            ws.onopen = () => {
                logToPanel("WebSocket connection established.", "connect");
            };

            ws.onmessage = (event) => {
                const now = new Date().getTime();
                if (currentUpdateRate > 0 && (now - lastUpdateTime < currentUpdateRate)) {
                    return; // Skip this frame (throttling)
                }
                lastUpdateTime = now;

                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'update') {
                        const timestamp = now;
                        updateStatus(message.status);
                        updateGUI(message.data, timestamp);
                    }
                } catch (e) {
                    console.error("Error parsing packet:", e);
                    logToPanel(`Error parsing packet: ${e.message}`, 'disconnect');
                }
            };

            ws.onclose = () => {
                logToPanel("WebSocket closed. Reconnecting in 3s...", "disconnect");
                updateStatus({ arduino_connected: false, port: "WebSocket Closed" });
                setTimeout(connectWebSocket, 3000); 
            };

            ws.onerror = (error) => {
                logToPanel(`WebSocket error`, 'disconnect');
                ws.close();
            };
        }

        // --- window.onload (unchanged) ---
        window.onload = () => {
            initializeCharts();
            logToPanel("Dashboard initialized. Waiting for data...");
            
            // Get all interactive elements
            const settingsBtn = document.getElementById('settings-btn');
            const settingsDropdown = document.getElementById('settings-dropdown');
            const darkModeToggle = document.getElementById('dark-mode-toggle');
            const updateRateSelect = document.getElementById('update-rate');
            
            const logToggleBtn = document.getElementById('log-toggle-btn');
            const logPanel = document.getElementById('log-panel');
            const logCloseBtn = document.getElementById('log-close-btn');
            const logOverlay = document.getElementById('log-overlay-bg');
            
            settingsBtn.addEventListener('click', () => {
                settingsDropdown.classList.toggle('show');
            });
            
            window.addEventListener('click', (e) => {
                if (settingsBtn && !settingsBtn.contains(e.target) && settingsDropdown && !settingsDropdown.contains(e.target)) {
                    settingsDropdown.classList.remove('show');
                }
            });

            darkModeToggle.addEventListener('change', () => {
                document.body.classList.toggle('dark-mode');
                if (document.body.classList.contains('dark-mode')) {
                    localStorage.setItem('darkMode', 'enabled');
                } else {
                    localStorage.setItem('darkMode', 'disabled');
                }
                updateAllChartColors();
            });
            
            if (localStorage.getItem('darkMode') !== 'disabled') {
                document.body.classList.add('dark-mode');
                darkModeToggle.checked = true;
            }
            updateAllChartColors();
            
            updateRateSelect.addEventListener('change', (e) => {
                currentUpdateRate = parseInt(e.target.value, 10);
                settingsDropdown.classList.remove('show');
            });
            currentUpdateRate = parseInt(updateRateSelect.value, 10);
            
            function openLogModal() {
                logPanel.classList.add('show');
                logOverlay.classList.add('show');
                logToggleBtn.textContent = 'Hide Event Log';
                settingsDropdown.classList.remove('show');
            }
            
            function closeLogModal() {
                logPanel.classList.remove('show');
                logOverlay.classList.remove('show');
                logToggleBtn.textContent = 'Show Event Log';
            }

            logToggleBtn.addEventListener('click', () => {
                if (logPanel.classList.contains('show')) {
                    closeLogModal();
                } else {
                    openLogModal();
                }
            });
            
            logCloseBtn.addEventListener('click', closeLogModal);
            logOverlay.addEventListener('click', closeLogModal); 
            
            // Start WebSocket connection
            connectWebSocket();
        };
        
        // --- updateAllChartColors (unchanged) ---
        function updateAllChartColors() {
            // Get current data values to redraw gauges
            const pressure = parseFloat(document.getElementById('pressure-value').textContent.split(' ')[0]) || 0;
            const pitch = parseFloat(document.getElementById('gyro-x-value').textContent.split(' ')[0]) || 0;
            const roll = parseFloat(document.getElementById('gyro-y-value').textContent.split(' ')[0]) || 0;

            updateGauge(chartObjects.pressureGauge, pressure, 90000, 105000, 'pressure-value', 'Pa');
            updateGauge(chartObjects.pitchGauge, pitch, -90, 90, 'gyro-x-value', 'deg');
            updateGauge(chartObjects.rollGauge, roll, -180, 180, 'gyro-y-value', 'deg');
            
            const isDarkMode = document.body.classList.contains('dark-mode');
            const theme = isDarkMode ? THEME_COLORS.dark : THEME_COLORS.light;
            document.getElementById('compass-needle').style.borderBottomColor = theme.red;
            document.getElementById('bubble-ball').style.backgroundColor = theme.primary;
        }
    </script>
</body>
</html>
"""

# --- Part 3: Main Execution (Python) ---
app = Flask(__name__)
sock = Sock(app)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@sock.route('/ws')
def ws(ws):
    global global_clients
    print("WebSocket client connected.")
    with data_lock:
        global_clients.append(ws)
    
    try:
        # Send the *current* state immediately on connect
        with data_lock:
            payload = json.dumps({
                "type": "update",
                "status": global_status,
                "data": global_data
            })
        ws.send(payload)
    except Exception as e:
        print(f"Error on initial send to new client: {e}")

    try:
        while True:
            # Just wait for a disconnect.
            message = ws.receive(timeout=None) 
            if message is None: # Client sent a close frame
                break
    except Exception as e:
        pass # Client disconnected
    finally:
        # Clean up the client from the global list
        with data_lock:
            if ws in global_clients:
                global_clients.remove(ws)
        print("Client removed from list.")

if __name__ == "__main__":
    # 1. Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 2. Initialize Parser
    parser = TelemetryParser()
    logging.info("TelemetryParser initialized.")

    # 3. Initialize DataLogger
    logger_config = {
        'output_directory': './flight_data/',
        'auto_create_directory': True,
        'csv': {
            'include_header': True,
            'float_precision': 6
        },
        'buffer_size': 1 # Flush every write for real-time
    }
    datalogger = DataLogger(config=logger_config)
    logging.info(f"DataLogger initialized. Logging to: {datalogger.get_current_file()}")

    # 4. Create reverse map for GUI labels
    # Maps 'gps_lat' -> 'GPS Lat'
    reverse_key_map = {v: k for k, v in parser.key_map.items()}

    # 5. Initialize global_data with default values from parser's labels
    global_data = {label: "0.0" for label in parser.DATA_LABELS}

    # 6. Find the GCS Receiver Arduino
    arduino_port = find_arduino_port()
    if not arduino_port:
        logging.error("Could not find a GCS Receiver Arduino.")
        logging.warning("Please check connection and ARDUINO_VID_PIDS list.")
        with data_lock:
            global_status["port"] = "Not Found"
        arduino_port = "NOT_FOUND" # Set placeholder to retry
    else:
        with data_lock:
            global_status["port"] = arduino_port
    
    # 7. Start the serial reader thread and pass instances
    reader = threading.Thread(
        target=serial_reader_thread, 
        args=(arduino_port, parser, datalogger, reverse_key_map), 
        daemon=True
    )
    reader.start()

    # 8. Start the Flask web server
    print("\n--- SlugSight Ground Station Server ---")
    print(f"Open this URL in your browser: http://127.0.0.1:5200")
    print("-----------------------------------------------------")
    try:
        # --- THIS IS THE FIX ---
        # Removed the 'allow_unsafe_werkzeug' argument
        app.run(host='0.0.0.0', port=5300, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        # Cleanly close the log file
        print("Closing data logger...")
        datalogger.close()
        print("Shutdown complete.")