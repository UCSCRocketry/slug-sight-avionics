/**
 * SLUG SIGHT AVIONICS - ROCKET FIRMWARE
 * 
 * Hardware: Adafruit Feather M4 Express
 * Function: Read sensors, transmit telemetry via LoRa
 * 
 * Sensors:
 *  - BMP280 (SPI) - Barometer
 *  - LSM6DSOX (I2C) - IMU  
 *  - LIS3MDL (I2C) - Magnetometer
 *  - Ultimate GPS (UART) - GPS
 *  - RFM95W (SPI) - LoRa Radio
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>

// RadioHead LoRa
#include <RH_RF95.h>

// Sensors
#include <Adafruit_BMP280.h>
#include <Adafruit_LSM6DSOX.h>
#include <Adafruit_LIS3MDL.h>
#include <Adafruit_GPS.h>

// ==========================================
// PIN DEFINITIONS
// ==========================================
// LoRa RFM95W
#define RFM95_CS    8
#define RFM95_RST   4
#define RFM95_INT   3

// BMP280 (SPI)
#define BMP280_CS   10

// Frequency
#define RF95_FREQ   915.0  // 915 MHz (US) or 868 MHz (EU)

// ==========================================
// TELEMETRY PACKET STRUCTURE
// ==========================================
struct TelemetryPacket {
    uint32_t timestamp_ms;      // Milliseconds since boot
    
    // Barometer (BMP280)
    float altitude;             // meters
    float pressure;             // pascals
    float temperature;          // celsius
    
    // IMU (LSM6DSOX)
    float accel_x;              // m/s²
    float accel_y;
    float accel_z;
    float gyro_x;               // deg/s
    float gyro_y;
    float gyro_z;
    
    // Magnetometer (LIS3MDL)
    float mag_x;                // μT
    float mag_y;
    float mag_z;
    
    // GPS
    float gps_lat;              // degrees
    float gps_lon;              // degrees
    float gps_alt;              // meters
    uint8_t gps_satellites;     // number of satellites
    
    // Flight state
    uint8_t state;              // 0=PAD, 1=BOOST, 2=COAST, 3=DESCENT, 4=LANDED
    
    uint16_t packet_num;        // Packet sequence number
} __attribute__((packed));

// ==========================================
// GLOBAL OBJECTS
// ==========================================
RH_RF95 rf95(RFM95_CS, RFM95_INT);

Adafruit_BMP280 bmp(BMP280_CS);  // Hardware SPI
Adafruit_LSM6DSOX lsm6ds;        // I2C
Adafruit_LIS3MDL lis3mdl;        // I2C
Adafruit_GPS GPS(&Serial1);      // Hardware Serial1

TelemetryPacket telemetry;
uint16_t packet_counter = 0;

// Timing
unsigned long lastTransmit = 0;
const unsigned long TX_INTERVAL = 100;  // ms (10 Hz)

// ==========================================
// SETUP
// ==========================================
void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);  // Wait max 3s
    
    Serial.println("\n========================================");
    Serial.println("  SLUG SIGHT AVIONICS - ROCKET");
    Serial.println("  Feather M4 + RadioHead LoRa");
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
    
    // RadioHead configuration
    rf95.setTxPower(23, false);           // 23 dBm max
    rf95.setSpreadingFactor(7);           // SF7 = fastest
    rf95.setSignalBandwidth(125000);      // 125 kHz
    rf95.setCodingRate4(5);               // 4/5 coding rate
    Serial.println("✓ LoRa configured");
    
    // ==========================================
    // Initialize BMP280 (SPI)
    // ==========================================
    Serial.print("Initializing BMP280 (SPI)... ");
    if (!bmp.begin()) {
        Serial.println("FAILED!");
    } else {
        Serial.println("OK");
        bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                       Adafruit_BMP280::SAMPLING_X2,
                       Adafruit_BMP280::SAMPLING_X16,
                       Adafruit_BMP280::FILTER_X16,
                       Adafruit_BMP280::STANDBY_MS_1);
    }
    
    // ==========================================
    // Initialize I2C sensors
    // ==========================================
    Wire.begin();
    Serial.println("I2C initialized");
    
    // LSM6DSOX IMU
    Serial.print("Initializing LSM6DSOX (I2C)... ");
    if (!lsm6ds.begin_I2C(0x6A)) {
        if (!lsm6ds.begin_I2C(0x6B)) {
            Serial.println("FAILED!");
        } else {
            Serial.println("OK (0x6B)");
        }
    } else {
        Serial.println("OK (0x6A)");
    }
    
    lsm6ds.setAccelRange(LSM6DS_ACCEL_RANGE_16_G);
    lsm6ds.setGyroRange(LSM6DS_GYRO_RANGE_2000_DPS);
    lsm6ds.setAccelDataRate(LSM6DS_RATE_104_HZ);
    lsm6ds.setGyroDataRate(LSM6DS_RATE_104_HZ);
    
    // LIS3MDL Magnetometer
    Serial.print("Initializing LIS3MDL (I2C)... ");
    if (!lis3mdl.begin_I2C(0x1C)) {
        if (!lis3mdl.begin_I2C(0x1E)) {
            Serial.println("FAILED!");
        } else {
            Serial.println("OK (0x1E)");
        }
    } else {
        Serial.println("OK (0x1C)");
    }
    
    lis3mdl.setPerformanceMode(LIS3MDL_MEDIUMMODE);
    lis3mdl.setOperationMode(LIS3MDL_CONTINUOUSMODE);
    lis3mdl.setDataRate(LIS3MDL_DATARATE_155_HZ);
    lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);
    
    // ==========================================
    // Initialize GPS (UART)
    // ==========================================
    Serial.print("Initializing GPS (UART)... ");
    GPS.begin(9600);
    GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
    GPS.sendCommand(PMTK_SET_NMEA_UPDATE_10HZ);
    Serial.println("OK (waiting for fix)");
    
    Serial.println("\n========================================");
    Serial.println("SYSTEM READY - Waiting for launch...");
    Serial.println("========================================\n");
    
    digitalWrite(LED_BUILTIN, HIGH);
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
    unsigned long currentTime = millis();
    
    // Read GPS continuously (non-blocking)
    char c = GPS.read();
    if (GPS.newNMEAreceived()) {
        GPS.parse(GPS.lastNMEA());
    }
    
    // ==========================================
    // Read sensors and transmit
    // ==========================================
    if (currentTime - lastTransmit >= TX_INTERVAL) {
        // Read BMP280
        telemetry.pressure = bmp.readPressure();
        telemetry.temperature = bmp.readTemperature();
        telemetry.altitude = bmp.readAltitude(1013.25);  // Adjust sea level pressure
        
        // Read LSM6DSOX
        sensors_event_t accel, gyro, temp;
        lsm6ds.getEvent(&accel, &gyro, &temp);
        telemetry.accel_x = accel.acceleration.x;
        telemetry.accel_y = accel.acceleration.y;
        telemetry.accel_z = accel.acceleration.z;
        telemetry.gyro_x = gyro.gyro.x * 57.2958;  // rad/s to deg/s
        telemetry.gyro_y = gyro.gyro.y * 57.2958;
        telemetry.gyro_z = gyro.gyro.z * 57.2958;
        
        // Read LIS3MDL
        sensors_event_t mag;
        lis3mdl.getEvent(&mag);
        telemetry.mag_x = mag.magnetic.x;
        telemetry.mag_y = mag.magnetic.y;
        telemetry.mag_z = mag.magnetic.z;
        
        // GPS data
        if (GPS.fix) {
            telemetry.gps_lat = GPS.latitudeDegrees;
            telemetry.gps_lon = GPS.longitudeDegrees;
            telemetry.gps_alt = GPS.altitude;
            telemetry.gps_satellites = GPS.satellites;
        } else {
            telemetry.gps_lat = 0;
            telemetry.gps_lon = 0;
            telemetry.gps_alt = 0;
            telemetry.gps_satellites = 0;
        }
        
        // Metadata
        telemetry.timestamp_ms = currentTime;
        telemetry.packet_num = packet_counter++;
        telemetry.state = 0;  // TODO: Implement flight state machine
        
        // ==========================================
        // Transmit via LoRa
        // ==========================================
        uint8_t *packet_bytes = (uint8_t*)&telemetry;
        rf95.send(packet_bytes, sizeof(TelemetryPacket));
        rf95.waitPacketSent();
        
        lastTransmit = currentTime;
        
        // Blink LED
        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
        
        // Debug output
        Serial.print("["); Serial.print(packet_counter); Serial.print("] ");
        Serial.print("Alt: "); Serial.print(telemetry.altitude, 1); Serial.print("m | ");
        Serial.print("AccZ: "); Serial.print(telemetry.accel_z, 2); Serial.print(" m/s² | ");
        Serial.print("GPS: ");
        if (GPS.fix) {
            Serial.print(telemetry.gps_satellites); Serial.print(" sats");
        } else {
            Serial.print("NO FIX");
        }
        Serial.println();
    }
}
