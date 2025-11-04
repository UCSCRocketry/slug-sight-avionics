/**
 * IMU (Inertial Measurement Unit) Interface
 * 
 * Handles reading accelerometer and gyroscope data.
 * Supports multiple IMU models (BMI088, MPU6050, ICM20948, etc.)
 */

#ifndef IMU_H
#define IMU_H

#include <Arduino.h>
#include <Wire.h>

class IMU {
public:
  /**
   * Initialize the IMU sensor
   * @return true if successful, false otherwise
   */
  bool begin();
  
  /**
   * Update sensor readings (call in main loop)
   */
  void update();
  
  /**
   * Calibrate the IMU (call when stationary)
   */
  void calibrate();
  
  // Accelerometer getters (m/s²)
  float getAccelX() const { return accel_x; }
  float getAccelY() const { return accel_y; }
  float getAccelZ() const { return accel_z; }
  
  // Gyroscope getters (deg/s)
  float getGyroX() const { return gyro_x; }
  float getGyroY() const { return gyro_y; }
  float getGyroZ() const { return gyro_z; }
  
  // Get total acceleration magnitude
  float getAccelMagnitude() const;

private:
  // Raw sensor readings
  float accel_x, accel_y, accel_z;
  float gyro_x, gyro_y, gyro_z;
  
  // Calibration offsets
  float accel_offset_x, accel_offset_y, accel_offset_z;
  float gyro_offset_x, gyro_offset_y, gyro_offset_z;
  
  // Sensor-specific initialization
  bool initBMI088();
  bool initMPU6050();
};

#endif // IMU_H
