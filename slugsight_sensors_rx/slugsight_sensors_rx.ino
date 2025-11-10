/*
 * SlugSight ARDUINO - LORA RECEIVER (v3 - Final)
 *
 * This is the LoRa-to-USB Bridge for the GCS.
 * It runs on the Arduino connected to your computer.
 *
 * 1. Receives the 17-point packet from the rocket.
 * 2. Grabs the RSSI (18th point).
 * 3. Prints the full 18-point CSV string to the USB Serial port
 * (at 115200 baud) for the Python GCS script to read.
 */

#include <SPI.h>
#include <RH_RF95.h>

// --- LoRa Setup (for Arduino Uno/Nano/etc.) ---
#define RFM95_CS   10
#define RFM95_RST  7
#define RFM95_INT  2  // Must be an interrupt pin (2 or 3 on Uno)
#define RF95_FREQ 915.0 // MUST MATCH TRANSMITTER

// Singleton instance of the radio driver
RH_RF95 rf95(RFM95_CS, RFM95_INT);

void setup() {
  // This Serial port is for communicating with Python
  // The baud rate MUST match your Python script (115200)
  Serial.begin(115200);
  
  // --- Initialize LoRa Radio ---
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);
  delay(100);
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  if (!rf95.init()) {
    while (1); // Halt if radio init fails
  }
  if (!rf95.setFrequency(RF95_FREQ)) {
    while (1); // Halt if frequency set fails
  }

  // Set the fastest data rate to MATCH the transmitter
  rf95.setModemConfig(RH_RF95::Bw500Cr45Sf128);
}


void loop() {
  if (rf95.available()) {
    // A message was received
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      // 1. Get the 17-point CSV string from the rocket
      // We must explicitly null-terminate the string
      buf[len] = '\0'; 
      String csvData = (char*)buf;
      
      // 2. Get the RSSI of the packet we just received
      int rssi = rf95.lastRssi();
      
      // 3. Create the new 18-point string
      String outputData = csvData + "," + String(rssi);

      // 4. Send the 18-point string to the Python GCS
      Serial.println(outputData);
      
    }
  }
}
