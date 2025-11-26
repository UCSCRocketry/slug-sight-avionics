/*
 * SlugSight GROUND STATION RECEIVER (Arduino Uno Version)
 * * HARDWARE: Arduino Uno + RFM95W LoRa Module
 * * FUNCTION:
 * 1. Receives LoRa packets (17-point CSV) from the rocket.
 * 2. Appends RSSI (Signal Strength) to the end.
 * 3. Prints 18-point CSV to Serial for the Python GCS.
 */

#include <SPI.h>
#include <RH_RF95.h>

// --- Pinout for Arduino Uno ---
// Pins 11, 12, 13 are handled automatically by the SPI library
#define RFM95_CS   10  // Default Chip Select
#define RFM95_INT  2   // Default Interrupt (Pin 2 = INT0 on Uno)
#define RFM95_RST  9   // Default Reset

// --- Frequency (Must match TX) ---
#define RF95_FREQ 915.0

// Singleton instance of the radio driver
RH_RF95 rf95(RFM95_CS, RFM95_INT);

void setup() {
  // Start Serial at 115200 to match your Python GCS
  Serial.begin(115200);

  // Wait briefly for serial to stabilize
  delay(1000);

  // Manual Reset of LoRa Module
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH); delay(100);
  digitalWrite(RFM95_RST, LOW);  delay(10);
  digitalWrite(RFM95_RST, HIGH); delay(10);

  if (!rf95.init()) {
    Serial.println("LoRa radio init failed");
    Serial.println("Check wiring: CS->10, INT->2, RST->9, MOSI->11, MISO->12, SCK->13");
    while (1);
  }

  // Set frequency
  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("setFrequency failed");
    while (1);
  }

  // Set Max Power (23dBm)
  rf95.setTxPower(23, false);

  // Set Modem Config to match the Transmitter
  // This is CRITICAL. Must match the Bw500Cr45Sf128 used in the TX code.
  rf95.setModemConfig(RH_RF95::Bw500Cr45Sf128);

  Serial.println("SlugSight RX (Uno) Ready. Waiting for packets...");
}

void loop() {
  if (rf95.available()) {
    // Buffer to hold the received message
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      // 1. Force null termination so we can treat it as a string
      buf[len] = 0;

      // 2. Print the raw CSV data from the rocket (Fields 1-17)
      Serial.print((char*)buf);

      // 3. Append the RSSI (Field 18)
      Serial.print(",");
      Serial.println(rf95.lastRssi(), DEC);

      // 4. Blink LED to show activity
      // Note: On Uno, Pin 13 is also SCK. If this interferes with SPI, comment it out.
      digitalWrite(LED_BUILTIN, HIGH);
      delay(10);
      digitalWrite(LED_BUILTIN, LOW);

    } else {
      Serial.println("Receive failed");
    }
  }
}
