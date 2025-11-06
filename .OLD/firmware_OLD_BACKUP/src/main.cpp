/**
 * Slug Sight Avionics - Main Flight Computer
 * 
 * This is the main entry point for the rocket flight computer.
 * It initializes all sensors, manages the flight state machine,
 * and handles telemetry transmission via LoRa.
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>

// Sensor includes (implement these in respective files)
#include "sensors/imu.h"
#include "sensors/magnetometer.h"
#include "sensors/gps.h"
#include "sensors/barometer.h"

// Communication
#include "communications/lora.h"

// Data handling
#include "data/telemetry.h"
#include "data/logger.h"

// State machine
#include "state/flight_state.h"

// ==========================================
// GLOBAL OBJECTS
// ==========================================
IMU imu;
Magnetometer magnetometer;
GPS gps;
Barometer barometer;
LoRaRadio loraRadio;
TelemetryPacket telemetry;
DataLogger logger;
FlightState flightState;

// Timing
unsigned long lastTelemetrySend = 0;
unsigned long lastLogWrite = 0;
const unsigned long TELEMETRY_INTERVAL = 100;  // ms
const unsigned long LOG_INTERVAL = 50;         // ms

// ==========================================
// SETUP
// ==========================================
void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);
  while (!Serial && millis() < 5000);  // Wait up to 5s for serial
  
  Serial.println("=================================");
  Serial.println("  Slug Sight Avionics v1.0");
  Serial.println("  UCSC Rocket Team");
  Serial.println("=================================");
  
  // Initialize I2C
  Wire.begin();
  
  // Initialize SPI for LoRa and SD card
  SPI.begin();
  
  // Initialize sensors
  Serial.println("Initializing sensors...");
  
  if (!imu.begin()) {
    Serial.println("ERROR: IMU initialization failed!");
  } else {
    Serial.println("✓ IMU initialized");
  }
  
  if (!magnetometer.begin()) {
    Serial.println("ERROR: Magnetometer initialization failed!");
  } else {
    Serial.println("✓ Magnetometer initialized");
  }
  
  if (!gps.begin()) {
    Serial.println("ERROR: GPS initialization failed!");
  } else {
    Serial.println("✓ GPS initialized");
  }
  
  if (!barometer.begin()) {
    Serial.println("ERROR: Barometer initialization failed!");
  } else {
    Serial.println("✓ Barometer initialized");
  }
  
  // Initialize LoRa radio
  Serial.println("Initializing LoRa radio...");
  if (!loraRadio.begin()) {
    Serial.println("ERROR: LoRa initialization failed!");
  } else {
    Serial.println("✓ LoRa initialized");
  }
  
  // Initialize SD card logger
  Serial.println("Initializing SD card...");
  if (!logger.begin()) {
    Serial.println("WARNING: SD card initialization failed!");
    Serial.println("Continuing without SD logging...");
  } else {
    Serial.println("✓ SD card initialized");
  }
  
  // Initialize flight state machine
  flightState.setState(FLIGHT_STATE_PAD);
  Serial.println("✓ Flight state: PAD");
  
  Serial.println("=================================");
  Serial.println("System ready! Waiting for launch...");
  Serial.println("=================================");
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
  unsigned long currentTime = millis();
  
  // Update all sensors
  imu.update();
  magnetometer.update();
  gps.update();
  barometer.update();
  
  // Update flight state machine
  flightState.update(imu.getAccelZ(), barometer.getVelocity());
  
  // Populate telemetry packet
  telemetry.timestamp = currentTime / 1000.0;  // Convert to seconds
  telemetry.state = flightState.getCurrentState();
  
  // Barometer data
  telemetry.altitude = barometer.getAltitude();
  telemetry.pressure = barometer.getPressure();
  telemetry.temperature = barometer.getTemperature();
  
  // IMU data
  telemetry.accel_x = imu.getAccelX();
  telemetry.accel_y = imu.getAccelY();
  telemetry.accel_z = imu.getAccelZ();
  telemetry.gyro_x = imu.getGyroX();
  telemetry.gyro_y = imu.getGyroY();
  telemetry.gyro_z = imu.getGyroZ();
  
  // Magnetometer data
  telemetry.mag_x = magnetometer.getMagX();
  telemetry.mag_y = magnetometer.getMagY();
  telemetry.mag_z = magnetometer.getMagZ();
  
  // GPS data
  telemetry.gps_lat = gps.getLatitude();
  telemetry.gps_lon = gps.getLongitude();
  telemetry.gps_alt = gps.getAltitude();
  
  // Send telemetry via LoRa
  if (currentTime - lastTelemetrySend >= TELEMETRY_INTERVAL) {
    loraRadio.sendTelemetry(telemetry);
    lastTelemetrySend = currentTime;
  }
  
  // Log to SD card
  if (currentTime - lastLogWrite >= LOG_INTERVAL) {
    logger.writeTelemetry(telemetry);
    lastLogWrite = currentTime;
  }
  
  // Debug output (optional, can be disabled in flight)
  #ifdef DEBUG_SERIAL
  if (currentTime % 1000 < 10) {  // Print every ~1 second
    Serial.print("State: ");
    Serial.print(flightState.getStateName());
    Serial.print(" | Alt: ");
    Serial.print(telemetry.altitude, 1);
    Serial.print(" m | Accel: ");
    Serial.print(telemetry.accel_z, 2);
    Serial.println(" m/s²");
  }
  #endif
  
  // Small delay to maintain loop timing
  delay(10);
}
