/**
 * Data Logger
 * 
 * Handles logging telemetry data to SD card.
 */

#ifndef LOGGER_H
#define LOGGER_H

#include <Arduino.h>
#include <SD.h>
#include "telemetry.h"

class DataLogger {
public:
  /**
   * Initialize SD card and create log file
   * @return true if successful, false otherwise
   */
  bool begin();
  
  /**
   * Write telemetry packet to SD card
   * @param packet Telemetry data to log
   */
  void writeTelemetry(const TelemetryPacket& packet);
  
  /**
   * Flush buffer to SD card
   */
  void flush();
  
  /**
   * Close log file
   */
  void close();

private:
  File log_file;
  String filename;
  bool is_initialized;
  
  // Generate timestamped filename
  String generateFilename();
  
  // Write CSV header
  void writeHeader();
};

#endif // LOGGER_H
