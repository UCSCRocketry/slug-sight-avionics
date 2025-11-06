/**
 * GPS Interface
 * 
 * Handles reading GPS position and velocity data.
 * Supports NEO-M9N, NEO-6M, SAM-M8Q, etc.
 */

#ifndef GPS_H
#define GPS_H

#include <Arduino.h>
#include <TinyGPSPlus.h>

class GPS {
public:
  /**
   * Initialize the GPS module
   * @return true if successful, false otherwise
   */
  bool begin();
  
  /**
   * Update GPS readings (call in main loop)
   */
  void update();
  
  /**
   * Check if GPS has a valid fix
   * @return true if position is valid
   */
  bool hasFix() const { return has_fix; }
  
  // Position getters
  float getLatitude() const { return latitude; }       // Degrees
  float getLongitude() const { return longitude; }     // Degrees
  float getAltitude() const { return altitude; }       // Meters
  
  // Velocity getters
  float getSpeed() const { return speed; }             // m/s
  float getCourse() const { return course; }           // Degrees
  
  // Quality indicators
  uint8_t getSatellites() const { return satellites; }
  float getHDOP() const { return hdop; }

private:
  TinyGPSPlus gps_parser;
  HardwareSerial* gps_serial;
  
  bool has_fix;
  float latitude;
  float longitude;
  float altitude;
  float speed;
  float course;
  uint8_t satellites;
  float hdop;
};

#endif // GPS_H
