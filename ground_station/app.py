"""
Slug Sight Ground Station - Web Interface
Flask web server with live telemetry visualization
"""

import sys
import time
import signal
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify
from collections import deque

from serial_reader import SerialReader, TelemetryParser
from data.data_logger import DataLogger
from utils.helpers import load_config, setup_logging

# ==========================================
# Flask Web Application
# ==========================================
app = Flask(__name__)

# Global state
running = True
latest_telemetry = {}
telemetry_history = deque(maxlen=1000)  # Last 1000 packets

# Statistics
packet_count = 0
error_count = 0
start_time = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\nShutdown signal received...")
    running = False

# ==========================================
# Web Routes
# ==========================================
@app.route('/')
def index():
    """Main dashboard page"""
    try:
        return render_template('dashboard.html')
    except:
        # Fallback if template not found
        return """
        <html>
        <head><title>Slug Sight GDS</title></head>
        <body>
            <h1>Slug Sight Ground Station</h1>
            <p>Telemetry dashboard - Template coming soon!</p>
            <p>Check <a href="/api/telemetry/latest">/api/telemetry/latest</a> for latest data</p>
            <p>Check <a href="/api/stats">/api/stats</a> for statistics</p>
        </body>
        </html>
        """

@app.route('/api/telemetry/latest')
def get_latest_telemetry():
    """API endpoint for latest telemetry data"""
    return jsonify(latest_telemetry if latest_telemetry else {"status": "waiting"})

@app.route('/api/telemetry/history')
def get_telemetry_history():
    """API endpoint for telemetry history"""
    return jsonify(list(telemetry_history)[-100:])  # Last 100 points

@app.route('/api/stats')
def get_stats():
    """API endpoint for statistics"""
    global start_time, packet_count, error_count
    
    elapsed_time = time.time() - start_time if start_time else 0
    packet_rate = packet_count / elapsed_time if elapsed_time > 0 else 0
    
    return jsonify({
        'packet_count': packet_count,
        'error_count': error_count,
        'elapsed_time': round(elapsed_time, 1),
        'packet_rate': round(packet_rate, 2),
        'latest_telemetry': latest_telemetry
    })

# ==========================================
# Telemetry Reception Thread
# ==========================================
def telemetry_thread(config, data_logger):
    """Background thread for receiving and logging telemetry"""
    global running, latest_telemetry, telemetry_history
    global packet_count, error_count, start_time
    
    log = setup_logging(config)
    
    try:
        # Initialize serial reader and parser
        reader = SerialReader(config['serial'])
        parser = TelemetryParser()
        
        log.info(f"Connected to ground Feather on {config['serial']['serial_port']}")
        log.info(f"Logging to: {data_logger.get_current_file()}")
        
        start_time = time.time()
        
        # Main receive loop
        while running:
            try:
                # Read packet from ground Feather
                packet = reader.read_packet()
                
                if packet is not None:
                    # Parse telemetry
                    telemetry = parser.parse(packet['data'], packet)
                    
                    if telemetry is not None:
                        # Update global state
                        latest_telemetry.update(telemetry)
                        telemetry_history.append(telemetry.copy())
                        
                        # Log to CSV file
                        data_logger.write(telemetry)
                        
                        # Update statistics
                        packet_count += 1
                        
                        # Console output
                        if config.get('display', {}).get('enable_console_output', True):
                            print_telemetry_compact(telemetry)
                    else:
                        error_count += 1
                        log.warning("Failed to parse telemetry packet")
                        
            except Exception as e:
                error_count += 1
                log.error(f"Error processing packet: {e}")
            
            time.sleep(0.01)
            
    except Exception as e:
        log.error(f"Telemetry thread error: {e}")
    finally:
        reader.close()
        data_logger.close()

def print_telemetry_compact(telemetry):
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
    
    print(f"[{telemetry.get('packet_num', 0):04d}] "
          f"{color}{state:8s}{reset} | "
          f"Alt: {telemetry.get('altitude', 0):7.1f}m | "
          f"AccZ: {telemetry.get('accel_z', 0):6.2f} m/s² | "
          f"RSSI: {telemetry.get('ground_rssi', 0):4d}dBm | "
          f"GPS: {telemetry.get('gps_satellites', 0)} sats")

# ==========================================
# Main Entry Point
# ==========================================
def main():
    """Main ground station entry point"""
    global running
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("  SLUG SIGHT GROUND STATION v2.0")
    print("  UCSC Rocket Team")
    print("  Feather M4 + Web Interface")
    print("=" * 60)
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "ground_config.yaml"
    config = load_config(config_path)
    
    # Initialize data logger
    data_logger = DataLogger(config['data_logging'])
    
    print("\n✓ Ground station ready!")
    print(f"✓ Logging to: {data_logger.get_current_file()}")
    print(f"\n Web interface: http://localhost:5000")
    print("   Open in your browser to view live telemetry")
    print("\n" + "-" * 60 + "\n")
    
    # Start telemetry reception thread
    telemetry_worker = threading.Thread(
        target=telemetry_thread,
        args=(config, data_logger),
        daemon=True
    )
    telemetry_worker.start()
    
    # Start Flask web server
    try:
        print("Starting web server...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        telemetry_worker.join(timeout=2)
        
        print("\n" + "=" * 60)
        print("Ground station stopped.")
        print("=" * 60)

if __name__ == "__main__":
    main()
