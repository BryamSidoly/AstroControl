#include <AccelStepper.h>

// ================== PINOS ==================
#define AZ_STEP 2
#define AZ_DIR 3
#define ALT_STEP 4
#define ALT_DIR 5

// ================== MOTORES ==================
AccelStepper motorAz(AccelStepper::DRIVER, AZ_STEP, AZ_DIR);
AccelStepper motorAlt(AccelStepper::DRIVER, ALT_STEP, ALT_DIR);

// ================== CONFIG ==================
const float AZ_STEPS_PER_DEG = 20.0;
const float ALT_STEPS_PER_DEG = 20.0;

// Limites físicos
const float AZ_MIN = 0, AZ_MAX = 360;
const float ALT_MIN = 0, ALT_MAX = 90;

float currentAz = 0.0;
float currentAlt = 0.0;

float targetAz = 0.0;
float targetAlt = 0.0;

bool tracking = false;

float speedAz = 0;
float speedAlt = 0;

// ================== SETUP ==================
void setup() {
  Serial.begin(9600);

  motorAz.setMaxSpeed(800);
  motorAz.setAcceleration(400);

  motorAlt.setMaxSpeed(800);
  motorAlt.setAcceleration(400);

  Serial.println("READY");
}

// ================== LOOP ==================
void loop() {
  readCommand();

  if (tracking) {
    motorAz.setSpeed(speedAz);
    motorAlt.setSpeed(speedAlt);

    motorAz.runSpeed();
    motorAlt.runSpeed();
  } else {
    motorAz.run();
    motorAlt.run();
  }
}

// ================== SERIAL ==================
String inputString = "";
void readCommand() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      inputString.trim();
      parseCommand(inputString);
      inputString = "";
    } else {
      inputString += inChar;
    }
  }
}

void parseCommand(String cmd) {
  if (cmd.startsWith("GOTO")) {
    parseGoto(cmd);
    tracking = false;
    Serial.println("OK GOTO");
  } 
  else if (cmd.startsWith("TRACK")) {
    parseTrackSpeed(cmd);
    tracking = true;
    Serial.println("OK TRACK");
  }
  else if (cmd == "ZERO") {
    zeroPosition();
    Serial.println("OK ZERO");
  } 
  else if (cmd == "STOP") {
    speedAz = 0;
    speedAlt = 0;

    motorAz.setSpeed(0);
    motorAlt.setSpeed(0);

    motorAz.stop();
    motorAlt.stop();

    tracking = false;
    Serial.println("OK STOP");
  }
  else {
    Serial.println("ERR SYNTAX");
  }
}

// ================== GOTO / TRACK ==================
void parseGoto(String cmd) {
  float az, alt;

  int azIndex = cmd.indexOf("AZ=");
  int altIndex = cmd.indexOf("ALT=");

  if (azIndex < 0 || altIndex < 0) {
    Serial.println("ERR SYNTAX");
    return;
  }

  az = cmd.substring(azIndex + 3, cmd.indexOf(' ', azIndex + 3)).toFloat();
  alt = cmd.substring(altIndex + 4).toFloat();

  moveTo(az, alt);
}

// ================== MOVIMENTO ==================
void moveTo(float az, float alt) {
  // Respeita limites
  az = constrain(az, AZ_MIN, AZ_MAX);
  alt = constrain(alt, ALT_MIN, ALT_MAX);

  targetAz = az;
  targetAlt = alt;

  long azSteps = az * AZ_STEPS_PER_DEG;
  long altSteps = alt * ALT_STEPS_PER_DEG;

  motorAz.moveTo(azSteps);
  motorAlt.moveTo(altSteps);
}

// ================== ZERO ==================
void zeroPosition() {
  motorAz.setCurrentPosition(0);
  motorAlt.setCurrentPosition(0);

  currentAz = 0;
  currentAlt = 0;
}

void parseTrackSpeed(String cmd) {
  int azIndex = cmd.indexOf("VAZ=");
  int altIndex = cmd.indexOf("VALT=");

  if (azIndex < 0 || altIndex < 0) {
    Serial.println("ERR TRACK");
    return;
  }

  float vaz = cmd.substring(azIndex + 4, cmd.indexOf(' ', azIndex + 4)).toFloat();
  float valt = cmd.substring(altIndex + 5).toFloat();

  // converte °/s → steps/s
  speedAz = vaz * AZ_STEPS_PER_DEG;
  speedAlt = valt * ALT_STEPS_PER_DEG;

  // limite de segurança
  speedAz = constrain(speedAz, -200, 200);
  speedAlt = constrain(speedAlt, -200, 200);
}
