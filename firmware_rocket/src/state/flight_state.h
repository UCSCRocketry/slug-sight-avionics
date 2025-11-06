/**
 * Flight State Machine for Slug Sight Avionics
 * 
 * Manages the different phases of flight:
 * PAD -> BOOST -> COAST -> DESCENT -> LANDED
 * 
 * This detects transitions automatically based on sensor data.
 */

#ifndef FLIGHT_STATE_H
#define FLIGHT_STATE_H

#include <Arduino.h>

// Flight state enumeration (matches telemetry packet)
enum FlightState {
    FLIGHT_STATE_PAD = 0,      // On launch pad, waiting
    FLIGHT_STATE_BOOST = 1,    // Motor burning, high acceleration
    FLIGHT_STATE_COAST = 2,    // Motor burned out, coasting upward
    FLIGHT_STATE_DESCENT = 3,  // Falling, parachute deployed
    FLIGHT_STATE_LANDED = 4    // Landed, stationary on ground
};

class FlightStateMachine {
public:
    FlightStateMachine() : 
        current_state(FLIGHT_STATE_PAD),
        state_start_time(0),
        launch_detected(false),
        max_altitude(0.0),
        pad_altitude(0.0) {}
    
    /**
     * Initialize state machine with ground-level altitude
     */
    void begin(float ground_altitude) {
        pad_altitude = ground_altitude;
        max_altitude = ground_altitude;
        current_state = FLIGHT_STATE_PAD;
        state_start_time = millis();
    }
    
    /**
     * Update flight state based on sensor data
     * Call this in your main loop after reading sensors
     * 
     * @param accel_z Vertical acceleration in m/s² (positive = up)
     * @param altitude Current altitude in meters
     * @param velocity Vertical velocity in m/s (positive = up)
     */
    void update(float accel_z, float altitude, float velocity) {
        unsigned long now = millis();
        
        // Track maximum altitude
        if (altitude > max_altitude) {
            max_altitude = altitude;
        }
        
        switch (current_state) {
            case FLIGHT_STATE_PAD:
                // Detect launch: high vertical acceleration
                if (accel_z > LAUNCH_ACCEL_THRESHOLD) {
                    changeState(FLIGHT_STATE_BOOST, now);
                    launch_detected = true;
                }
                break;
                
            case FLIGHT_STATE_BOOST:
                // Detect burnout: acceleration returns to ~1G (gravity)
                // Allow some time for motor to burn
                if ((now - state_start_time) > MIN_BOOST_TIME && 
                    accel_z < BURNOUT_ACCEL_THRESHOLD) {
                    changeState(FLIGHT_STATE_COAST, now);
                }
                break;
                
            case FLIGHT_STATE_COAST:
                // Detect apogee: negative velocity (falling)
                // Or altitude starts decreasing
                if (velocity < APOGEE_VELOCITY_THRESHOLD) {
                    changeState(FLIGHT_STATE_DESCENT, now);
                }
                break;
                
            case FLIGHT_STATE_DESCENT:
                // Detect landing: low altitude and stable acceleration
                if ((altitude - pad_altitude) < LANDING_ALTITUDE_THRESHOLD &&
                    abs(accel_z - 9.8) < LANDING_ACCEL_THRESHOLD) {
                    
                    // Require stable for a period
                    if ((now - state_start_time) > LANDING_STABLE_TIME) {
                        changeState(FLIGHT_STATE_LANDED, now);
                    }
                }
                break;
                
            case FLIGHT_STATE_LANDED:
                // Stay landed forever
                break;
        }
    }
    
    /**
     * Get current flight state
     */
    uint8_t getState() const { 
        return current_state; 
    }
    
    /**
     * Get human-readable state name
     */
    const char* getStateName() const {
        return getStateNameStatic(current_state);
    }
    
    /**
     * Static version for converting state enum to string
     */
    static const char* getStateNameStatic(uint8_t state) {
        switch (state) {
            case FLIGHT_STATE_PAD:     return "PAD";
            case FLIGHT_STATE_BOOST:   return "BOOST";
            case FLIGHT_STATE_COAST:   return "COAST";
            case FLIGHT_STATE_DESCENT: return "DESCENT";
            case FLIGHT_STATE_LANDED:  return "LANDED";
            default:                   return "UNKNOWN";
        }
    }
    
    /**
     * Get time in current state (milliseconds)
     */
    unsigned long getTimeInState() const {
        return millis() - state_start_time;
    }
    
    /**
     * Get maximum altitude reached
     */
    float getMaxAltitude() const {
        return max_altitude;
    }
    
    /**
     * Check if launch has been detected
     */
    bool hasLaunched() const {
        return launch_detected;
    }

private:
    uint8_t current_state;
    unsigned long state_start_time;
    bool launch_detected;
    float max_altitude;
    float pad_altitude;
    
    // Threshold constants (tunable based on your rocket)
    const float LAUNCH_ACCEL_THRESHOLD = 20.0;      // m/s² (~2G acceleration)
    const float BURNOUT_ACCEL_THRESHOLD = 15.0;     // m/s² (back to ~1.5G)
    const unsigned long MIN_BOOST_TIME = 500;       // ms (minimum motor burn time)
    const float APOGEE_VELOCITY_THRESHOLD = -2.0;   // m/s (falling)
    const float LANDING_ALTITUDE_THRESHOLD = 50.0;  // meters above pad
    const float LANDING_ACCEL_THRESHOLD = 2.0;      // m/s² (nearly 1G = stationary)
    const unsigned long LANDING_STABLE_TIME = 3000; // ms (3 seconds stable)
    
    /**
     * Change to new state and log transition
     */
    void changeState(uint8_t new_state, unsigned long now) {
        if (new_state != current_state) {
            Serial.print("State transition: ");
            Serial.print(getStateNameStatic(current_state));
            Serial.print(" -> ");
            Serial.println(getStateNameStatic(new_state));
            
            current_state = new_state;
            state_start_time = now;
        }
    }
};

#endif // FLIGHT_STATE_H
