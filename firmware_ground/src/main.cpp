/**
 * SLUG SIGHT AVIONICS - GROUND RECEIVER
 * 
 * Hardware: Adafruit Feather M4 Express
 * Function: LoRa-to-USB Serial Bridge
 * 
 * This firmware:
 * 1. Receives LoRa packets from rocket
 * 2. Forwards raw bytes to laptop via USB Serial
 * 3. Simple, reliable bridge - no parsing needed
 */

#include <Arduino.h>
#include <SPI.h>
#include <RH_RF95.h>

// ==========================================
// PIN DEFINITIONS
// ==========================================
#define RFM95_CS    8
#define RFM95_RST   4
#define RFM95_INT   3
#define RF95_FREQ   915.0  // Must match rocket

// ==========================================
// GLOBAL OBJECTS
// ==========================================
RH_RF95 rf95(RFM95_CS, RFM95_INT);

// Packet buffer
uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
uint8_t len = sizeof(buf);

unsigned long lastPacketTime = 0;
uint32_t packetCount = 0;

// ==========================================
// SETUP
// ==========================================
void setup() {
    // USB Serial to laptop
    Serial.begin(115200);
    while (!Serial && millis() < 3000);
    
    Serial.println("\n========================================");
    Serial.println("  SLUG SIGHT - GROUND RECEIVER");
    Serial.println("  LoRa-to-USB Bridge");
    Serial.println("  UCSC Rocket Team");
    Serial.println("========================================\n");
    
    pinMode(LED_BUILTIN, OUTPUT);
    
    // ==========================================
    // Initialize LoRa Radio
    // ==========================================
    pinMode(RFM95_RST, OUTPUT);
    digitalWrite(RFM95_RST, HIGH);
    delay(10);
    digitalWrite(RFM95_RST, LOW);
    delay(10);
    digitalWrite(RFM95_RST, HIGH);
    delay(10);
    
    Serial.print("Initializing RFM95W LoRa... ");
    if (!rf95.init()) {
        Serial.println("FAILED!");
        while (1);
    }
    Serial.println("OK");
    
    if (!rf95.setFrequency(RF95_FREQ)) {
        Serial.println("setFrequency failed!");
        while (1);
    }
    Serial.print("Frequency set to "); Serial.print(RF95_FREQ); Serial.println(" MHz");
    
    // Match rocket configuration
    rf95.setSpreadingFactor(7);
    rf95.setSignalBandwidth(125000);
    rf95.setCodingRate4(5);
    
    Serial.println("✓ LoRa configured");
    Serial.println("\n========================================");
    Serial.println("READY - Listening for packets...");
    Serial.println("========================================\n");
    
    // Signal format for laptop parser
    Serial.println("---PACKET_START---");  // Header marker
    
    digitalWrite(LED_BUILTIN, HIGH);
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
    // Check for incoming LoRa packet
    if (rf95.available()) {
        len = sizeof(buf);
        
        if (rf95.recv(buf, &len)) {
            unsigned long currentTime = millis();
            int16_t rssi = rf95.lastRssi();
            
            packetCount++;
            
            // Blink LED on packet receive
            digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
            
            // ==========================================
            // Forward packet to laptop via USB Serial
            // ==========================================
            // Format: <START_MARKER><LENGTH><DATA><RSSI><END_MARKER>
            
            Serial.print("PKT:");          // Packet marker
            Serial.print(packetCount);     // Packet number
            Serial.print(",");
            Serial.print(currentTime);     // Timestamp
            Serial.print(",");
            Serial.print(len);             // Packet length
            Serial.print(",");
            Serial.print(rssi);            // Signal strength
            Serial.print(",");
            
            // Send raw packet bytes as hex
            for (uint8_t i = 0; i < len; i++) {
                if (buf[i] < 0x10) Serial.print("0");
                Serial.print(buf[i], HEX);
            }
            
            Serial.println();  // End of packet
            
            lastPacketTime = currentTime;
        }
    }
    
    // Heartbeat every 5 seconds if no packets
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastPacketTime > 5000 && millis() - lastHeartbeat > 5000) {
        Serial.print("HB:");              // Heartbeat marker
        Serial.print(millis());
        Serial.print(",");
        Serial.print(packetCount);
        Serial.println();
        
        lastHeartbeat = millis();
        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    }
}
