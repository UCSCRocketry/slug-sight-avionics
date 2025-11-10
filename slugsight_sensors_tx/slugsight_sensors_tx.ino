/*
 * SlugSight FEATHER M4 - LORA TRANSMITTER (v11 - LED Heartbeat)
 *
 * - Adds a blink to the built-in RED LED (pin 13)
 * on every successful LoRa packet transmission.
 */

// --- Includes ---
#include <SPI.h>
#include <RH_RF95.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM6DSOX.h>
#include <Adafruit_LIS3MDL.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_GPS.h>
#include <Adafruit_AHRS.h>

// --- LoRa Setup ---
#define RFM95_CS   10
#define RFM95_RST  11
#define RFM95_INT  12
#define RF95_FREQ 915.0

RH_RF95 rf95(RFM95_CS, RFM95_INT);

// --- Sensor SPI CS Pins ---
#define BMP_CS      6
#define LSM_CS      9
#define LIS3MDL_CS  5

// --- Sensor Object Initialization ---
Adafruit_LSM6DSOX sox;
Adafruit_LIS3MDL  lis3mdl;
Adafruit_BMP280   bmp(BMP_CS);

// --- GPS Setup (Serial1) ---
#define GPS_SERIAL Serial1
Adafruit_GPS GPS(&GPS_SERIAL);

// --- Sensor Fusion ---
Adafruit_Mahony filter;
#define FILTER_UPDATE_RATE_HZ 100
#define LORA_SEND_RATE_HZ     10

// --- Timing ---
unsigned long last_filter_update = 0;
unsigned long last_send_time = 0;
#define SEA_LEVEL_PRESSURE_HPA (1013.25)

// --- Battery Pin ---
#define VBATPIN A6

// --- Global Data Variables ---
float pitch = 0.0, roll = 0.0, yaw = 0.0;
float fused_altitude_m = 0.0, vertical_velocity_mps = 0.0;
float accel_x_g = 0.0, accel_y_g = 0.0, accel_z_g = 0.0;
float bmp_pressure_pa = 0.0, imu_temp_c = 0.0;
int   gps_fix = 0, gps_sats = 0;
float gps_latitude = 0.0, gps_longitude = 0.0;
float gps_altitude_m = 0.0, gps_speed_mps = 0.0;
float vbat = 0.0;

float altitude_old = 0.0;
unsigned long vel_time_old = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("SlugSight LoRa Transmitter (v11 - LED Heartbeat)... Booting.");

  // --- Initialize LED Pin ---
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // --- Initialize LoRa Radio ---
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH); delay(100);
  digitalWrite(RFM95_RST, LOW);  delay(10);
  digitalWrite(RFM95_RST, HIGH); delay(10);

  if (!rf95.init()) {
    Serial.println("LoRa radio init failed!");
    while (1);
  }
  Serial.println("LoRa radio init OK!");
  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("setFrequency failed");
    while (1);
  }
  rf95.setTxPower(23, false);
  rf95.setModemConfig(RH_RF95::Bw500Cr45Sf128);
  Serial.println("Set LoRa data rate to Bw500Cr45Sf128 (Fastest)");

  // --- Initialize SPI Sensors ---
  Serial.println("Initializing SPI sensors...");
  
  if (!sox.begin_SPI(LSM_CS)) {
    Serial.println("Failed to find LSM6DSOX chip! Check wiring.");
    while (1);
  }
  Serial.println("LSM6DSOX (SPI) Found!");

  if (!lis3mdl.begin_SPI(LIS3MDL_CS)) {
    Serial.println("Failed to find LIS3MDL chip! Check wiring.");
    while (1);
  }
  Serial.println("LIS3MDL (SPI) Found!");

  if (!bmp.begin()) {
    Serial.println("Failed to find BMP280 chip! Check wiring.");
    while (1);
  }
  Serial.println("BMP280 (SPI) Found!");


  // --- Configure Sensors ---
  sox.setAccelRange(LSM6DS_ACCEL_RANGE_16_G);
  sox.setGyroRange(LSM6DS_GYRO_RANGE_2000_DPS);
  sox.setAccelDataRate(LSM6DS_RATE_104_HZ);
  sox.setGyroDataRate(LSM6DS_RATE_104_HZ);
  
  lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);
  lis3mdl.setDataRate(LIS3MDL_DATARATE_1000_HZ);

  // --- Initialize GPS at 115200 ---
  Serial.println("Initializing GPS...");
  GPS.begin(9600); // Start at the default 9600 baud
  
  // Send command to switch GPS module to 115200
  Serial.println("Setting GPS baud rate to 115200...");
  GPS.sendCommand("PMTK251,115200");
  
  // Re-init Serial1 at new speed
  GPS_SERIAL.end();
  GPS_SERIAL.begin(115200);

  // Configure GPS to send RMC and GGA
  GPS.sendCommand("PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0");
  // Set update rate to 5 Hz
  GPS.sendCommand("PMTK220,200"); 
  delay(1000); // Give GPS time to process commands
  Serial.println("GPS Initialized at 115200.");

  // --- Initialize Fusion Filter ---
  filter.begin(FILTER_UPDATE_RATE_HZ);
  vel_time_old = millis();
  altitude_old = bmp.readAltitude(SEA_LEVEL_PRESSURE_HPA);
  
  Serial.println("Boot complete. Starting data transmission.");
}

void loop() {
  
  // 1. Read GPS
  GPS.read();

  // 2. Update Fusion Filter
  if (millis() - last_filter_update >= (1000 / FILTER_UPDATE_RATE_HZ)) {
    last_filter_update = millis();
    
    sensors_event_t accel, gyro, temp_imu, mag;
    sox.getEvent(&accel, &gyro, &temp_imu);
    lis3mdl.getEvent(&mag);

    filter.update(gyro.gyro.x, gyro.gyro.y, gyro.gyro.z,
                  accel.acceleration.x, accel.acceleration.y, accel.acceleration.z,
                  mag.magnetic.x, mag.magnetic.y, mag.magnetic.z);
    
    pitch = filter.getPitch();
    roll  = filter.getRoll();
    yaw   = filter.getYaw();

    imu_temp_c = temp_imu.temperature;
    accel_x_g = accel.acceleration.x / SENSORS_GRAVITY_STANDARD;
    accel_y_g = accel.acceleration.y / SENSORS_GRAVITY_STANDARD;
    accel_z_g = accel.acceleration.z / SENSORS_GRAVITY_STANDARD;
  }

  // 3. Parse, Format, and Send
  if (millis() - last_send_time >= (1000 / LORA_SEND_RATE_HZ)) {
    last_send_time = millis();
    
    // --- Turn LED ON during packet creation/send ---
    digitalWrite(LED_BUILTIN, HIGH);

    // 3a. GPS
    if (GPS.newNMEAreceived()) {
      if (GPS.parse(GPS.lastNMEA())) {
        gps_fix = (int)GPS.fix;
        gps_sats = (int)GPS.satellites;
        if (gps_fix) {
          gps_latitude = GPS.latitudeDegrees;
          gps_longitude = GPS.longitudeDegrees;
          gps_altitude_m = GPS.altitude;
          gps_speed_mps = GPS.speed * 0.514444; // knots to m/s
        }
      }
    }

    // 3b. Barometer
    bmp_pressure_pa = bmp.readPressure();
    fused_altitude_m = bmp.readAltitude(SEA_LEVEL_PRESSURE_HPA);

    // 3c. Velocity
    float dt = (millis() - vel_time_old) / 1000.0;
    if (dt > 0.001) {
      vertical_velocity_mps = (fused_altitude_m - altitude_old) / dt;
      altitude_old = fused_altitude_m;
      vel_time_old = millis();
    }

    // 3d. Battery
    vbat = analogRead(VBATPIN);
    vbat *= 2.0;    // reverse the 1:1 voltage divider
    vbat *= 3.3;    // multiply by 3.3V reference
    vbat /= 4095.0; // convert to voltage (12-bit ADC)

    // 3e. Build the 17-point CSV String
    String csvData = "";
    csvData += String(pitch, 2);                   // 1
    csvData += ",";
    csvData += String(roll, 2);                    // 2
    csvData += ",";
    csvData += String(yaw, 2);                     // 3
    csvData += ",";
    csvData += String(fused_altitude_m, 2);        // 4
    csvData += ",";
    csvData += String(vertical_velocity_mps, 2);   // 5
    csvData += ",";
    csvData += String(accel_x_g, 3);               // 6
    csvData += ",";
    csvData += String(accel_y_g, 3);               // 7
    csvData += ",";
    csvData += String(accel_z_g, 3);               // 8
    csvData += ",";
    csvData += String(bmp_pressure_pa, 2);         // 9
    csvData += ",";
    csvData += String(imu_temp_c, 2);              // 10
    csvData += ",";
    csvData += String(gps_fix);                    // 11
    csvData += ",";
    csvData += String(gps_sats);                   // 12
    csvData += ",";
    csvData += String(gps_latitude, 6);            // 13
    csvData += ",";
    csvData += String(gps_longitude, 6);           // 14
    csvData += ",";
    csvData += String(gps_altitude_m, 2);          // 15
    csvData += ",";
    csvData += String(gps_speed_mps, 2);           // 16
    csvData += ",";
    csvData += String(vbat, 2);                    // 17

    // 3f. Send over LoRa
    
    char txBuffer[250];
    csvData.toCharArray(txBuffer, 250);
    
    rf95.send((uint8_t *)txBuffer, strlen(txBuffer));
    rf95.waitPacketSent();

    // --- Turn LED OFF after send is complete ---
    digitalWrite(LED_BUILTIN, LOW);
  }
}