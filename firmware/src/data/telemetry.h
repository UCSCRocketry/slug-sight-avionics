/**
 * Telemetry Packet Structure
 * 
 * Defines the structure of telemetry data sent from the rocket
 * to the ground station via LoRa.
 */

#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <Arduino.h>

// Flight states
enum FlightStateEnum {
  FLIGHT_STATE_PAD = 0,
  FLIGHT_STATE_BOOST = 1,
  FLIGHT_STATE_COAST = 2,
  FLIGHT_STATE_DESCENT = 3,
  FLIGHT_STATE_LANDED = 4
};

/**
 * Main telemetry packet structure
 * Keep this packed and size-efficient for LoRa transmission
 */
struct TelemetryPacket {
  // Header
  uint8_t packet_id;          // Packet identifier
  uint16_t sequence_number;   // Incremental sequence number
  
  // Timing
  float timestamp;            // Time since boot (seconds)
  
  // Flight state
  uint8_t state;              // Current flight state
  
  // Barometer
  float altitude;             // Altitude (meters)
  float pressure;             // Pressure (pascals)
  float temperature;          // Temperature (celsius)
  
  // IMU - Accelerometer
  float accel_x;              // X acceleration (m/s²)
  float accel_y;              // Y acceleration (m/s²)
  float accel_z;              // Z acceleration (m/s²)
  
  // IMU - Gyroscope
  float gyro_x;               // X rotation rate (deg/s)
  float gyro_y;               // Y rotation rate (deg/s)
  float gyro_z;               // Z rotation rate (deg/s)
  
  // Magnetometer
  float mag_x;                // X magnetic field (μT)
  float mag_y;                // Y magnetic field (μT)
  float mag_z;                // Z magnetic field (μT)
  
  // GPS
  float gps_lat;              // Latitude (degrees)
  float gps_lon;              // Longitude (degrees)
  float gps_alt;              // GPS altitude (meters)
  
  // Footer
  uint16_t checksum;          // CRC16 checksum
};

/**
 * Calculate CRC16 checksum for telemetry packet
 */
uint16_t calculateChecksum(const TelemetryPacket& packet);

/**
 * Verify telemetry packet checksum
 */
bool verifyChecksum(const TelemetryPacket& packet);

/**
 * Convert flight state enum to string
 */
const char* getStateName(uint8_t state);

#endif // TELEMETRY_H
