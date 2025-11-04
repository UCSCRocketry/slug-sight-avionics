/**
 * LoRa Radio Communication
 * 
 * Handles sending telemetry packets via LoRa radio.
 */

#ifndef LORA_H
#define LORA_H

#include <Arduino.h>
#include <LoRa.h>
#include "../data/telemetry.h"

class LoRaRadio {
public:
  /**
   * Initialize LoRa radio
   * @return true if successful, false otherwise
   */
  bool begin();
  
  /**
   * Send telemetry packet
   * @param packet Telemetry data to send
   * @return true if sent successfully
   */
  bool sendTelemetry(TelemetryPacket& packet);
  
  /**
   * Set transmission power
   * @param power_dbm Power in dBm (2-20)
   */
  void setTxPower(int power_dbm);

private:
  uint16_t sequence_number;
  
  // LoRa configuration
  const long FREQUENCY = 915E6;        // 915 MHz (US)
  const int SPREADING_FACTOR = 7;
  const long BANDWIDTH = 125E3;        // 125 kHz
  const int CODING_RATE = 5;
  const byte SYNC_WORD = 0x12;
};

#endif // LORA_H
