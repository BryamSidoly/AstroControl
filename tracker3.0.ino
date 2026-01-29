// FIRMWARE PARA CONTROLE DE TELESCOPIO (LAT359.999/ALT90) COM MOTOR DE PASSO NEMA (RECOMENDADO) 17 EM ARDUINO UNO
// VERSAO 3.0 STABLE DESENVOLVIDA POR BRYAM S. SIERPINSKI EM 01/2026
// USO LIVRE :)

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

// Limites físicos do hardware
const float AZ_MIN = 0, AZ_MAX = 359.999; // Eixo horizontal
const float ALT_MIN = 0, ALT_MAX = 90;    // Eixo vertical (azimute 90)

// LIMPAR VARIÁVEIS
float currentAz = 0.0;
float currentAlt = 0.0;

float targetAz = 0.0;
float targetAlt = 0.0;

bool tracking = false;

float speedAz = 0;
float speedAlt = 0;

// compensação de folga de mudança de direção
const int BACKLASH_AZ_STEPS = 5;
const int BACKLASH_ALT_STEPS = 5;

// ================== SETUP ==================
void setup()
{
  Serial.begin(9600);

  motorAz.setMaxSpeed(800);
  motorAz.setAcceleration(400);

  motorAlt.setMaxSpeed(800);
  motorAlt.setAcceleration(400);

  Serial.println("READY");
}

// ================== LOOP ==================
void loop()
{
  if (!readBinaryTrack())
  {
    readCommand();
  }

  if (tracking)
  {
    motorAz.setSpeed(speedAz);
    motorAlt.setSpeed(speedAlt);
    motorAz.runSpeed();
    motorAlt.runSpeed();
  }
  else
  {
    motorAz.run();
    motorAlt.run();

    if (!motorAz.isRunning() && !motorAlt.isRunning())
    {
      currentAz = motorAz.currentPosition() / AZ_STEPS_PER_DEG;
      currentAlt = motorAlt.currentPosition() / ALT_STEPS_PER_DEG;
    }
  }
}

// ================== SERIAL ==================
String inputString = "";
void readCommand()
{
  while (Serial.available())
  {
    char inChar = (char)Serial.read();
    if (inChar == '\n')
    {
      inputString.trim();
      parseCommand(inputString);
      inputString = "";
    }
    else
    {
      inputString += inChar;
    }
  }
}

void parseCommand(String cmd)
{
  if (cmd.startsWith("GOTO"))
  {
    parseGoto(cmd);
    tracking = false;
    Serial.println("OK GOTO");
  }
  else if (cmd.startsWith("TRACK"))
  {
    parseTrackSpeed(cmd);
    tracking = true;
    Serial.println("OK TRACK");
  }
  else if (cmd == "ZERO")
  {
    zeroPosition();
    Serial.println("OK ZERO");
  }
  else if (cmd == "STOP")
  {
    speedAz = 0;
    speedAlt = 0;

    motorAz.setSpeed(0);
    motorAlt.setSpeed(0);

    motorAz.stop();
    motorAlt.stop();
    motorAz.moveTo(motorAz.currentPosition());
    motorAlt.moveTo(motorAlt.currentPosition());

    tracking = false;
    Serial.println("OK STOP");
  }
  else
  {
    Serial.println("ERR SYNTAX");
  }
}

// ================== GOTO / TRACK ==================
void parseGoto(String cmd)
{
  float az, alt;

  int azIndex = cmd.indexOf("AZ=");
  int altIndex = cmd.indexOf("ALT=");

  if (azIndex < 0 || altIndex < 0)
  {
    Serial.println("ERR SYNTAX");
    return;
  }

  az = cmd.substring(azIndex + 3, cmd.indexOf(' ', azIndex + 3)).toFloat();
  alt = cmd.substring(altIndex + 4).toFloat();

  moveTo(az, alt);
}

// ================== MOVIMENTO ==================
void applyBacklash(long nextAzSteps, long nextAltSteps)
{
  // Se direção mudou, empurra para compensar folga
  if (nextAzSteps > motorAz.currentPosition())
    nextAzSteps += BACKLASH_AZ_STEPS;
  else if (nextAzSteps < motorAz.currentPosition())
    nextAzSteps -= BACKLASH_AZ_STEPS;
  if (nextAltSteps > motorAlt.currentPosition())
    nextAltSteps += BACKLASH_ALT_STEPS;
  else if (nextAltSteps < motorAlt.currentPosition())
    nextAltSteps -= BACKLASH_ALT_STEPS;

  motorAz.moveTo(nextAzSteps);
  motorAlt.moveTo(nextAltSteps);
}

void moveTo(float az, float alt)
{
  // Respeita limites fisicos
  az = constrain(az, AZ_MIN, AZ_MAX);
  alt = constrain(alt, ALT_MIN, ALT_MAX);

  // Calcular menor delta (menor caminho) para voltas maiores que 180 nao derem a volta contando - graus
  float deltaAz = az - currentAz;
  if (deltaAz > 180)
    deltaAz -= 360;
  if (deltaAz < -180)
    deltaAz += 360;

  long azSteps = (currentAz + deltaAz) * AZ_STEPS_PER_DEG;
  long altSteps = alt * ALT_STEPS_PER_DEG;

  applyBacklash(azSteps, altSteps);

  targetAz = az;
  targetAlt = alt;

  currentAz = az;
  currentAlt = alt;
}

// ================== ZERO ==================
void zeroPosition()
{
  motorAz.setCurrentPosition(0);
  motorAlt.setCurrentPosition(0);

  currentAz = 0;
  currentAlt = 0;
}

// ================== TRACKER SPEED ==================
void parseTrackSpeed(String cmd)
{
  int azIndex = cmd.indexOf("VAZ=");
  int altIndex = cmd.indexOf("VALT=");

  if (azIndex < 0 || altIndex < 0)
  {
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

// ================== BYNARY TRACKER ==================
bool readBinaryTrack()
{
  if (Serial.available() < 12)
    return false;

  if (Serial.read() != 0x02)
    return false;

  char cmd = Serial.read();
  if (cmd != 'T')
    return false;

  int32_t vaz_i = 0;
  int32_t valt_i = 0;

  Serial.readBytes((byte *)&vaz_i, 4);
  Serial.readBytes((byte *)&valt_i, 4);

  byte chk = Serial.read();
  if (Serial.read() != 0x03)
    return false;

  // converte milideg/s → steps/s
  speedAz = (vaz_i / 1000.0) * AZ_STEPS_PER_DEG;
  speedAlt = (valt_i / 1000.0) * ALT_STEPS_PER_DEG;

  speedAz = constrain(speedAz, -200, 200);
  speedAlt = constrain(speedAlt, -200, 200);

  tracking = true;
  return true;
}
