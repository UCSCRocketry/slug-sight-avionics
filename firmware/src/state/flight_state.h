/**
 * Flight State Machine
 * 
 * Manages the different phases of flight:
 * PAD -> BOOST -> COAST -> DESCENT -> LANDED
 */

#ifndef FLIGHT_STATE_H
#define FLIGHT_STATE_H

#include <Arduino.h>
#include "../data/telemetry.h"

class FlightState {
public:
  FlightState() : current_state(FLIGHT_STATE_PAD), state_start_time(0) {}
  
  /**
   * Update flight state based on sensor data
   * @param accel_z Vertical acceleration (m/s²)
   * @param velocity Vertical velocity (m/s)
   */
  void update(float accel_z, float velocity);
  
  /**
   * Get current flight state
   */
  uint8_t getCurrentState() const { return current_state; }
  
  /**
   * Set flight state (for initialization)
   */
  void setState(uint8_t state);
  
  /**
   * Get human-readable state name
   */
  const char* getStateName() const;

private:
  uint8_t current_state;
  unsigned long state_start_time;
  
  // State transition thresholds
  const float LAUNCH_ACCEL_THRESHOLD = 3.0;      // G's
  const float APOGEE_VELOCITY_THRESHOLD = -5.0;  // m/s
  const float LANDING_ACCEL_THRESHOLD = 0.5;     // G's
  const unsigned long LANDING_STABLE_TIME = 3000; // ms
  
  // Helper functions for state transitions
  bool detectLaunch(float accel_z);
  bool detectApogee(float velocity);
  bool detectLanding(float accel_z);
};

#endif // FLIGHT_STATE_H
