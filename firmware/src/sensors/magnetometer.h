/**
 * Magnetometer Interface
 * 
 * Handles reading magnetic field data for orientation.
 * Supports HMC5883L, QMC5883L, LIS3MDL, etc.
 */

#ifndef MAGNETOMETER_H
#define MAGNETOMETER_H

#include <Arduino.h>
#include <Wire.h>

class Magnetometer {
public:
  /**
   * Initialize the magnetometer sensor
   * @return true if successful, false otherwise
   */
  bool begin();
  
  /**
   * Update sensor readings (call in main loop)
   */
  void update();
  
  /**
   * Calibrate the magnetometer
   */
  void calibrate();
  
  // Magnetic field getters (μT - microteslas)
  float getMagX() const { return mag_x; }
  float getMagY() const { return mag_y; }
  float getMagZ() const { return mag_z; }
  
  /**
   * Calculate heading angle (0-360 degrees)
   * @return Heading in degrees from magnetic north
   */
  float getHeading() const;

private:
  float mag_x, mag_y, mag_z;
  
  // Calibration offsets
  float mag_offset_x, mag_offset_y, mag_offset_z;
  float mag_scale_x, mag_scale_y, mag_scale_z;
};

#endif // MAGNETOMETER_H
