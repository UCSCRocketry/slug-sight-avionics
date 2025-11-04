"""
Flight Data Plotter

This script loads CSV flight data and generates plots for analysis.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

def plot_flight(csv_file):
    """
    Create comprehensive flight analysis plots
    
    Args:
        csv_file: Path to CSV flight data file
    """
    # Load data
    print(f"Loading {csv_file}...")
    df = pd.read_csv(csv_file)
    
    print(f"Loaded {len(df)} data points")
    print(f"Flight duration: {df['timestamp'].max():.1f} seconds")
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle(f'Flight Analysis: {Path(csv_file).stem}', fontsize=16)
    
    # Plot 1: Altitude vs Time
    ax = axes[0, 0]
    ax.plot(df['timestamp'], df['altitude'], 'b-', linewidth=2)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Altitude (m)')
    ax.set_title('Altitude Profile')
    ax.grid(True, alpha=0.3)
    
    # Mark apogee
    max_alt_idx = df['altitude'].idxmax()
    max_alt = df.loc[max_alt_idx, 'altitude']
    max_alt_time = df.loc[max_alt_idx, 'timestamp']
    ax.plot(max_alt_time, max_alt, 'r*', markersize=15, label=f'Apogee: {max_alt:.1f}m')
    ax.legend()
    
    # Plot 2: Vertical Acceleration
    ax = axes[0, 1]
    ax.plot(df['timestamp'], df['accel_z'], 'g-', linewidth=1)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Acceleration (m/s²)')
    ax.set_title('Vertical Acceleration')
    ax.axhline(y=9.8, color='r', linestyle='--', label='1G', alpha=0.5)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Plot 3: 3D Acceleration
    ax = axes[1, 0]
    ax.plot(df['timestamp'], df['accel_x'], label='X', alpha=0.7)
    ax.plot(df['timestamp'], df['accel_y'], label='Y', alpha=0.7)
    ax.plot(df['timestamp'], df['accel_z'], label='Z', alpha=0.7)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Acceleration (m/s²)')
    ax.set_title('3-Axis Acceleration')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Rotation Rates
    ax = axes[1, 1]
    ax.plot(df['timestamp'], df['gyro_x'], label='Roll', alpha=0.7)
    ax.plot(df['timestamp'], df['gyro_y'], label='Pitch', alpha=0.7)
    ax.plot(df['timestamp'], df['gyro_z'], label='Yaw', alpha=0.7)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Rotation Rate (deg/s)')
    ax.set_title('Gyroscope Data')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 5: GPS Track
    ax = axes[2, 0]
    if 'gps_lat' in df.columns and df['gps_lat'].notna().any():
        # Color code by altitude
        scatter = ax.scatter(df['gps_lon'], df['gps_lat'], 
                           c=df['altitude'], cmap='viridis', 
                           s=10, alpha=0.6)
        ax.plot(df['gps_lon'].iloc[0], df['gps_lat'].iloc[0], 
               'go', markersize=10, label='Launch')
        ax.plot(df['gps_lon'].iloc[-1], df['gps_lat'].iloc[-1], 
               'ro', markersize=10, label='Landing')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title('GPS Ground Track')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax, label='Altitude (m)')
    else:
        ax.text(0.5, 0.5, 'No GPS Data', 
               horizontalalignment='center',
               verticalalignment='center',
               transform=ax.transAxes)
    
    # Plot 6: Flight States
    ax = axes[2, 1]
    if 'state' in df.columns:
        # Convert states to numbers for plotting
        state_map = {'PAD': 0, 'BOOST': 1, 'COAST': 2, 'DESCENT': 3, 'LANDED': 4}
        df['state_num'] = df['state'].map(state_map)
        
        ax.plot(df['timestamp'], df['state_num'], 'o-', markersize=3)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Flight State')
        ax.set_yticks([0, 1, 2, 3, 4])
        ax.set_yticklabels(['PAD', 'BOOST', 'COAST', 'DESCENT', 'LANDED'])
        ax.set_title('Flight State Machine')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_file = Path(csv_file).with_suffix('.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Plot saved to {output_file}")
    
    # Display
    plt.show()
    
    # Print statistics
    print("\n=== Flight Statistics ===")
    print(f"Maximum altitude: {df['altitude'].max():.1f} m")
    print(f"Maximum velocity: {df['accel_z'].max()/9.8:.1f} G")
    print(f"Flight duration: {df['timestamp'].max():.1f} s")
    if 'gps_lat' in df.columns:
        lat_change = abs(df['gps_lat'].iloc[-1] - df['gps_lat'].iloc[0])
        lon_change = abs(df['gps_lon'].iloc[-1] - df['gps_lon'].iloc[0])
        print(f"GPS drift: {lat_change:.6f}° lat, {lon_change:.6f}° lon")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python plot_flight.py <flight_data.csv>")
        print("\nExample:")
        print("  python plot_flight.py ../data/flights/2025-11-03_14-30-00.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not Path(csv_file).exists():
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    plot_flight(csv_file)

if __name__ == "__main__":
    main()
