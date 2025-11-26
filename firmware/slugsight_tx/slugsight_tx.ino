/*
 * SlugSight FEATHER M4 - LORA TRANSMITTER (v28 - L2/L3 Calibrate-Once)
 *
 * - MOUNTING: Vertical (Y-Axis = Up/Down).
 * - AXIS REMAP: Inputs swapped so filter handles vertical mount correctly.
 * - WORKFLOW:
 * 1. Set CALIBRATION_MODE to true. Upload.
 * 2. Rotate avionics sled in all directions. Copy "Hard Iron" values from Serial.
 * 3. Paste values below. Set CALIBRATION_MODE to false. Upload.
 * 4. FLY! (No calibration movement required on the pad).
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
#include <SD.h>
#include <Wire.h>
#include "RTClib.h"

// ===================================================================================
//  USER CONFIGURATION SECTION
// ===================================================================================

// STEP 1: Set TRUE to find your offsets. Set FALSE for flight.
#define CALIBRATION_MODE false

// STEP 2: Paste your calibrated Hard-Iron offsets here (from Serial Monitor):
// (These values correct for the magnetic field of your batteries/screws/sled)
float MAG_OFFSET_X = 0.0;
float MAG_OFFSET_Y = 0.0;
float MAG_OFFSET_Z = 0.0;

// ===================================================================================

// --- TIME SOURCE TOGGLE ---
const bool USE_SOFTWARE_RTC = false;
// --------------------------

// --- RTC Object ---
RTCMillis rtc;
bool rtc_ready = false;

// --- SD Card Setup ---
const int SD_CS_PIN = 13;
const char* FILENAME_BASE = "LOG";
File logFile;
char log_filename[15];
bool sd_initialized = false;

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

// --- Sensor Objects ---
Adafruit_LSM6DSOX sox;
Adafruit_LIS3MDL  lis3mdl;
Adafruit_BMP280   bmp(BMP_CS);

// --- GPS Setup ---
#define GPS_SERIAL Serial1
Adafruit_GPS GPS(&GPS_SERIAL);

// --- Sensor Fusion ---
Adafruit_Mahony filter;
#define FILTER_UPDATE_RATE_HZ 155
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


void initializeSDCard(DateTime log_time) {
  Serial.print("Initializing SD card (CS Pin ");
  Serial.print(SD_CS_PIN);
  Serial.println(")...");

  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("Card failed, or not present!");
    return;
  }
  Serial.println("SD card initialized.");

  sprintf(log_filename, "%s00.CSV", FILENAME_BASE);
  for (uint8_t i = 0; i < 100; i++) {
    log_filename[strlen(FILENAME_BASE)] = i / 10 + '0';
    log_filename[strlen(FILENAME_BASE)] = i % 10 + '0';
    if (!SD.exists(log_filename)) break;
  }

  Serial.print("Creating new file: ");
  Serial.println(log_filename);

  logFile = SD.open(log_filename, FILE_WRITE);
  if (logFile) {
    Serial.println("Writing file header...");
    logFile.println("--- SlugSight Telemetry Log ---");
    logFile.print("File Created: ");
    logFile.print(log_time.year(), DEC); logFile.print("/");
    logFile.print(log_time.month(), DEC); logFile.print("/");
    logFile.print(log_time.day(), DEC); logFile.print(" ");
    logFile.print(log_time.hour(), DEC); logFile.print(":");
    logFile.print(log_time.minute(), DEC); logFile.print(":");
    logFile.println(log_time.second(), DEC);
    logFile.print("File Name: "); logFile.println(log_filename);
    logFile.println("---------------------------------");
    logFile.println("Timestamp,Pitch,Roll,Yaw,Altitude,Velocity,Accel X,Accel Y,Accel Z,Pressure Pa,IMU Temp C,GPS Fix,GPS Sats,GPS Lat,GPS Lon,GPS Alt m,GPS Speed m/s,VBat");
    logFile.flush();
    Serial.println("Header written. SD Logging is active.");
    sd_initialized = true;
  } else {
    Serial.print("Error opening "); Serial.println(log_filename);
  }
}

// --- Calibration Loop (Blocking) ---
void runCalibrationMode() {
  Serial.println("ENTERING CALIBRATION MODE");
  Serial.println("Rotate the avionics sled in all directions (Figure 8).");
  Serial.println("Copy the final Min/Max/Offset values into the code.");
  Serial.println("--------------------------------------------------");

  float min_x = 10000, max_x = -10000;
  float min_y = 10000, max_y = -10000;
  float min_z = 10000, max_z = -10000;

  while (true) {
    sensors_event_t accel, gyro, temp_imu, mag;
    lis3mdl.getEvent(&mag);

    if (mag.magnetic.x < min_x) min_x = mag.magnetic.x;
    if (mag.magnetic.x > max_x) max_x = mag.magnetic.x;
    if (mag.magnetic.y < min_y) min_y = mag.magnetic.y;
    if (mag.magnetic.y > max_y) max_y = mag.magnetic.y;
    if (mag.magnetic.z < min_z) min_z = mag.magnetic.z;
    if (mag.magnetic.z > max_z) max_z = mag.magnetic.z;

    float off_x = (max_x + min_x) / 2.0;
    float off_y = (max_y + min_y) / 2.0;
    float off_z = (max_z + min_z) / 2.0;

    // Print offsets for the user to copy
    Serial.print("X: "); Serial.print(off_x);
    Serial.print("  Y: "); Serial.print(off_y);
    Serial.print("  Z: "); Serial.println(off_z);

    // Fast blink to indicate cal mode
    digitalWrite(LED_BUILTIN, HIGH); delay(50);
    digitalWrite(LED_BUILTIN, LOW); delay(50);
  }
}

void setup() {
  Serial.begin(115200);
  unsigned long s = millis();
  while (!Serial && (millis() - s < 2000));

  Serial.println("SlugSight LoRa Transmitter (v28 - L2/L3 Config)...");

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // --- Init Hardware ---
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH); delay(100);
  digitalWrite(RFM95_RST, LOW);  delay(10);
  digitalWrite(RFM95_RST, HIGH); delay(10);

  rf95.init();
  rf95.setFrequency(RF95_FREQ);
  rf95.setTxPower(23, false);
  rf95.setModemConfig(RH_RF95::Bw500Cr45Sf128);

  sox.begin_SPI(LSM_CS);
  lis3mdl.begin_SPI(LIS3MDL_CS);
  bmp.begin();

  // --- Config (OPTIMIZED RATES) ---
  sox.setAccelRange(LSM6DS_ACCEL_RANGE_16_G);
  sox.setGyroRange(LSM6DS_GYRO_RANGE_2000_DPS);
  sox.setAccelDataRate(LSM6DS_RATE_208_HZ);
  sox.setGyroDataRate(LSM6DS_RATE_208_HZ);

  lis3mdl.setPerformanceMode(LIS3MDL_ULTRAHIGHMODE);
  lis3mdl.setOperationMode(LIS3MDL_CONTINUOUSMODE);
  lis3mdl.setDataRate(LIS3MDL_DATARATE_155_HZ);
  lis3mdl.setRange(LIS3MDL_RANGE_4_GAUSS);
  lis3mdl.setIntThreshold(500);
  lis3mdl.configInterrupt(false, false, true, true, false, true);

  // --- Calibration Divert ---
  if (CALIBRATION_MODE) {
    runCalibrationMode(); // Infinite Loop
  }

  GPS.begin(9600);
  GPS.sendCommand("PMTK251,115200");
  GPS_SERIAL.end();
  GPS_SERIAL.begin(115200);
  GPS.sendCommand("PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0");
  GPS.sendCommand("PMTK220,200");

  if (USE_SOFTWARE_RTC) {
    rtc.begin(datetime.DateTime(F(__DATE__), F(__TIME__)));
    initializeSDCard(rtc.now());
  }

  filter.begin(FILTER_UPDATE_RATE_HZ);
  vel_time_old = millis();
  altitude_old = bmp.readAltitude(SEA_LEVEL_PRESSURE_HPA);
}

void loop() {
  GPS.read();
  if (GPS.newNMEAreceived()) GPS.parse(GPS.lastNMEA());

  // SD Init on GPS Lock
  if (!sd_initialized && !USE_SOFTWARE_RTC) {
    if (GPS.fix && GPS.year >= 20) {
      initializeSDCard(datetime.DateTime(2000 + GPS.year, GPS.month, GPS.day, GPS.hour, GPS.minute, GPS.seconds));
    }
  }

  // Sensor Fusion
  if (millis() - last_filter_update >= (1000 / FILTER_UPDATE_RATE_HZ)) {
    last_filter_update = millis();
    sensors_event_t accel, gyro, temp_imu, mag;
    sox.getEvent(&accel, &gyro, &temp_imu);
    lis3mdl.getEvent(&mag);

    // 1. Apply Saved Calibration Offsets
    float mx = mag.magnetic.x - MAG_OFFSET_X;
    float my = mag.magnetic.y - MAG_OFFSET_Y;
    float mz = mag.magnetic.z - MAG_OFFSET_Z;

    // 2. Axis Remapping for Vertical Board Mount (Y=Up)
    // Filter Inputs: (GX, GY, GZ, AX, AY, AZ, MX, MY, MZ)
    // Remap:
    //   Filter X (Forward) = -Sensor X
    //   Filter Y (Right)   = Sensor Z
    //   Filter Z (Down)    = -Sensor Y (Gravity)

    // FIX: Inverted 'mx' (-mx) to fix East/West mirroring
    filter.update(gyro.gyro.x * SENSORS_RADS_TO_DPS,
                  gyro.gyro.z * SENSORS_RADS_TO_DPS,
                 -gyro.gyro.y * SENSORS_RADS_TO_DPS,
                  accel.acceleration.x,
                  accel.acceleration.z,
                 -accel.acceleration.y,
                  -mx,
                  mz,
                 -my);

    pitch = filter.getPitch();
    roll  = filter.getRoll();
    yaw   = filter.getYaw();

    // Standard Normalize
    if (yaw < 0.0)   yaw += 360.0;
    if (yaw >= 360.0) yaw -= 360.0;

    imu_temp_c = temp_imu.temperature;
    accel_x_g = accel.acceleration.x / SENSORS_GRAVITY_STANDARD;
    accel_y_g = accel.acceleration.y / SENSORS_GRAVITY_STANDARD;
    accel_z_g = accel.acceleration.z / SENSORS_GRAVITY_STANDARD;
  }

  // Telemetry Send
  if (millis() - last_send_time >= (1000 / LORA_SEND_RATE_HZ)) {
    last_send_time = millis();
    digitalWrite(LED_BUILTIN, HIGH); // Heartbeat On

    gps_fix = (int)GPS.fix;
    gps_sats = (int)GPS.satellites;
    if (gps_fix) {
      gps_latitude = GPS.latitudeDegrees;
      gps_longitude = GPS.longitudeDegrees;
      gps_altitude_m = GPS.altitude;
      gps_speed_mps = GPS.speed * 0.514444;
    } else {
      gps_latitude = 0.0; gps_longitude = 0.0;
    }

    bmp_pressure_pa = bmp.readPressure();
    fused_altitude_m = bmp.readAltitude(SEA_LEVEL_PRESSURE_HPA);

    float dt = (millis() - vel_time_old) / 1000.0;
    if (dt > 0.001) {
      vertical_velocity_mps = (fused_altitude_m - altitude_old) / dt;
      altitude_old = fused_altitude_m;
      vel_time_old = millis();
    }

    vbat = analogRead(VBATPIN) * 2.0 * 3.3 / 1024.0;

    String csvData = "";
    csvData += String(pitch, 2) + "," + String(roll, 2) + "," + String(yaw, 2) + ",";
    csvData += String(fused_altitude_m, 2) + "," + String(vertical_velocity_mps, 2) + ",";
    csvData += String(accel_x_g, 3) + "," + String(accel_y_g, 3) + "," + String(accel_z_g, 3) + ",";
    csvData += String(bmp_pressure_pa, 2) + "," + String(imu_temp_c, 2) + ",";
    csvData += String(gps_fix) + "," + String(gps_sats) + ",";
    csvData += String(gps_latitude, 6) + "," + String(gps_longitude, 6) + ",";
    csvData += String(gps_altitude_m, 2) + "," + String(gps_speed_mps, 2) + ",";
    csvData += String(vbat, 2);

    char txBuffer[250];
    csvData.toCharArray(txBuffer, 250);
    rf95.send((uint8_t *)txBuffer, strlen(txBuffer));

    if (sd_initialized && logFile) {
      char ts[35];
      if (USE_SOFTWARE_RTC) {
        DateTime n = rtc.now();
        sprintf(ts, "%02d/%02d/%04d %02d:%02d:%02d.000", n.month(), n.day(), n.year(), n.hour(), n.minute(), n.second());
      } else {
        sprintf(ts, "%02d/%02d/%04d %02d:%02d:%02d.%03d", GPS.month, GPS.day, 2000 + GPS.year, GPS.hour, GPS.minute, GPS.seconds, GPS.milliseconds);
      }
      logFile.print(ts); logFile.print(","); logFile.println(csvData); logFile.flush();
    }

    rf95.waitPacketSent();
    digitalWrite(LED_BUILTIN, LOW); // Heartbeat Off
  }
}
