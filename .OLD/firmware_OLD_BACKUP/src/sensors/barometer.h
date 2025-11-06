/**
 * Barometer Interface
 * 
 * Handles reading atmospheric pressure and calculating altitude.
 * Supports BMP388, BMP280, MS5611, etc.
 */

#ifndef BAROMETER_H
#define BAROMETER_H

#include <Arduino.h>
#include <Wire.h>

class Barometer {
public:
  /**
   * Initialize the barometer sensor
   * @return true if successful, false otherwise
   */
  bool begin();
  
  /**
   * Update sensor readings (call in main loop)
   */
  void update();
  
  /**
   * Set reference pressure for altitude calculation
   * @param pressure Sea level pressure in pascals
   */
  void setSeaLevelPressure(float pressure);
  
  // Getters
  float getPressure() const { return pressure; }           // Pascals
  float getTemperature() const { return temperature; }     // Celsius
  float getAltitude() const { return altitude; }           // Meters
  float getVelocity() const { return velocity; }           // m/s (vertical)

private:
  float pressure;                // Current pressure (Pa)
  float temperature;             // Current temperature (°C)
  float altitude;                // Calculated altitude (m)
  float velocity;                // Vertical velocity (m/s)
  
  float sea_level_pressure;      // Reference pressure (Pa)
  float prev_altitude;           // For velocity calculation
  unsigned long prev_time;       // For velocity calculation
  
  // Calculate altitude from pressure using barometric formula
  float calculateAltitude(float pressure_pa);
};

#endif // BAROMETER_H
