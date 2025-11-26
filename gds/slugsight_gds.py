# SlugSight Telemetry - Ground Station
# Copyright (c) 2025 UCSC Rocket Team
# Licensed under MIT License

import serial
import serial.tools.list_ports
import threading
import time
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request
from flask_sock import Sock

# --- Project Imports ---
from telemetry_parser import TelemetryParser
from data_logger import DataLogger

# --- Configuration ---
ARDUINO_VID_PIDS = [
    (0x2341, 0x0043), (0x2341, 0x0001), (0x1A86, 0x7523), (0x239A, 0x8022)
]

# --- Path Configuration ---
BASE_DIR = Path(__file__).parent.absolute()
LOG_DIR = BASE_DIR / 'flight_data'
LOG_DIR.mkdir(exist_ok=True)

# --- Global variables ---
global_data = {}
global_status = {
    "arduino_connected": False,
    "port": "Not Found"
}
data_lock = threading.Lock()
global_clients = []

# --- Part 1: Serial Reader Thread ---

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
                        if not line: continue

                        line_str = line.decode('utf-8').strip()
                        if not line_str: continue

                        parsed_telemetry = parser.parse(line_str)

                        if not parsed_telemetry:
                            continue

                        if parsed_telemetry.get('packet_count', 0) > 0:
                            datalogger.write(parsed_telemetry)

                        payload = None
                        with data_lock:
                            for key, value in parsed_telemetry.items():
                                if key in reverse_key_map:
                                    label = reverse_key_map[key]
                                    global_data[label] = str(value)

                            global_data['sys_status'] = parsed_telemetry.get('sys_status', 'active')

                            payload = json.dumps({
                                "type": "update",
                                "status": global_status,
                                "data": global_data
                            })

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
                        port = "NOT_FOUND"
                        break
                    except UnicodeDecodeError:
                        pass
                    except Exception as e:
                        print(f"Unexpected error in read loop: {e}")
                        time.sleep(1)

        except serial.SerialException as e:
            print(f"Serial connection error: {e}")
            port = "NOT_FOUND"
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

app = Flask(__name__)
sock = Sock(app)

@app.route('/')
def home():
    return render_template('index.html')

@sock.route('/ws')
def ws(ws):
    global global_clients
    print("WebSocket client connected.")
    with data_lock:
        global_clients.append(ws)

    try:
        # Send current state
        with data_lock:
            payload = json.dumps({
                "type": "update",
                "status": global_status,
                "data": global_data
            })
        ws.send(payload)
    except Exception: pass

    try:
        while True:
            if ws.receive(timeout=None) is None: break
    except Exception: pass
    finally:
        with data_lock:
            if ws in global_clients: global_clients.remove(ws)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = TelemetryParser()

    datalogger = DataLogger({
        'output_directory': str(LOG_DIR),
        'csv': {'include_header': True}
    })

    reverse_key_map = {v: k for k, v in parser.key_map.items()}

    global_data = {label: "0.0" for label in parser.DATA_LABELS}
    global_data['sys_status'] = 'active'

    port = find_arduino_port()
    if not port:
        global_status["port"] = "Not Found"
        port = "NOT_FOUND"
    else:
        global_status["port"] = port

    reader = threading.Thread(target=serial_reader_thread, args=(port or "NOT_FOUND", parser, datalogger, reverse_key_map), daemon=True)
    reader.start()

    print("\n--- Rocket Team - SlugSight Avionics GDS ---")
    print("Open this URL in your browser: http://127.0.0.1:8080")
    print("-----------------------------------------------------")
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        datalogger.close()
