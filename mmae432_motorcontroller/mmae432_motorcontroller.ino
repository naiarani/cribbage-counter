//// StepperEqualityTest.ino
////
//// Moves Motor1 then Motor2 the same number of steps so you can
//// visually (or with a ruler) confirm they travel the same distance.
//
//#define STEP1_PIN     2
//#define DIR1_PIN      5
//#define ENABLE1_PIN   8
//
//#define STEP2_PIN     3
//#define DIR2_PIN      6
//#define ENABLE2_PIN   9
//
//const int STEP_DELAY_US = 800;    // microseconds between pulses
//const long TEST_STEPS  = 200;    // try one full revolution (~200 for 1.8° motor)
//
//void setup() {
//  // init pins
//  pinMode(STEP1_PIN,   OUTPUT);
//  pinMode(DIR1_PIN,    OUTPUT);
//  pinMode(ENABLE1_PIN, OUTPUT);
//  pinMode(STEP2_PIN,   OUTPUT);
//  pinMode(DIR2_PIN,    OUTPUT);
//  pinMode(ENABLE2_PIN, OUTPUT);
//
//  // enable drivers (LOW = enabled on most DRV8825/A4988 boards)
//  digitalWrite(ENABLE1_PIN, LOW);
//  digitalWrite(ENABLE2_PIN, LOW);
//
//  // choose forward direction
//  digitalWrite(DIR1_PIN, HIGH);
//  digitalWrite(DIR2_PIN, HIGH);
//
//  Serial.begin(9600);
//  Serial.println("=== Stepper Equality Test ===");
//}
//
//void loop() {
//  Serial.println("Motor 1: stepping forward 200 steps");
//  stepMotor(TEST_STEPS, STEP1_PIN, DIR1_PIN);
//  delay(1000);
//
//  Serial.println("Motor 2: stepping forward 200 steps");
//  stepMotor(TEST_STEPS, STEP2_PIN, DIR2_PIN);
//  delay(1000);
//
//  Serial.println("Test complete. Halting.");
//  while (true) {
//    // do nothing
//  }
//}
//
//// step 'n' pulses on (stepPin), toggling dirPin beforehand
//void stepMotor(long steps, int stepPin, int dirPin) {
//  // ensure direction already set
//  for (long i = 0; i < steps; i++) {
//    digitalWrite(stepPin, HIGH);
//    delayMicroseconds(5);
//    digitalWrite(stepPin, LOW);
//    delayMicroseconds(STEP_DELAY_US);
//  }
//}
//
//
//
//
//#define STEP1_PIN       2
//#define DIR1_PIN        5
//#define ENABLE1_PIN     8
//
//#define STEP2_PIN       3
//#define DIR2_PIN        6
//#define ENABLE2_PIN     9
//
//const int STEP_DELAY_US   = 800;
//const int STEPS_PER_POINT = 200;
//
//long pos1 = 0;
//long pos2 = 0;
//
//void setup() {
//  Serial.begin(9600);
//
//  pinMode(STEP1_PIN,   OUTPUT);
//  pinMode(DIR1_PIN,    OUTPUT);
//  pinMode(ENABLE1_PIN, OUTPUT);
//  pinMode(STEP2_PIN,   OUTPUT);
//  pinMode(DIR2_PIN,    OUTPUT);
//  pinMode(ENABLE2_PIN, OUTPUT);
//
//  digitalWrite(ENABLE1_PIN, LOW);
//  digitalWrite(DIR1_PIN,    HIGH);
//  digitalWrite(ENABLE2_PIN, LOW);
//  digitalWrite(DIR2_PIN,    HIGH);
//}
//
//void loop() {
//  if (!Serial.available()) return;
//
//  String line = Serial.readStringUntil('\n');
//  line.trim();
//  int comma = line.indexOf(',');
//  if (comma < 0) return;
//
//  int player = line.substring(0, comma).toInt();
//  int score  = line.substring(comma+1).toInt();
//
//  if (score < 0 || score > 121) return;
//
//  long target = (long)score * STEPS_PER_POINT;
//  long delta;
//
//  if (player == 1) {
//    delta = target - pos1;
//    moveStepper(delta, STEP1_PIN, DIR1_PIN);
//    pos1 = target;
//  }
//  else if (player == 2) {
//    delta = target - pos2;
//    moveStepper(delta, STEP2_PIN, DIR2_PIN);
//    pos2 = target;
//  }
//}
//
//void moveStepper(long steps, int stepPin, int dirPin) {
//  bool dir = (steps >= 0);
//  digitalWrite(dirPin, dir ? HIGH : LOW);
//  long n = abs(steps);
//  for (long i = 0; i < n; i++) {
//    digitalWrite(stepPin, HIGH);
//    delayMicroseconds(5);
//    digitalWrite(stepPin, LOW);
//    delayMicroseconds(STEP_DELAY_US);
//  }
//}
//


// CribbageStepperByPoints.ino
// Listens for lines "<axis>,<totalPoints>\n" and moves each motor
// by (deltaPoints × mm_per_point) distance, swapping in a larger
// mm_per_point for points 26–29 and 56–60.

#include <Arduino.h>

// step & dir pins for the two motors
#define X_STEP_PIN     2
#define X_DIR_PIN      5
#define Y_STEP_PIN     3
#define Y_DIR_PIN      6
#define ENABLE_PIN     8

// manual‐jog buttons
#define BUTTON1_PIN    A0  // jog X motor
#define BUTTON2_PIN    A1  // jog Y motor

// mechanical constants
const float MM_PER_REV        = 25.13;  // mm per 200‐step revolution
const int   STEPS_PER_REV     = 200;
const int   STEP_DELAY_US     = 800;

// how many mm per cribbage point
const float MM_PER_POINT      = 5.1;   // normal
const float MM_PER_POINT_BEND = 3.0;   // for totals 26–29 or 56–60

// jog distance when a button is pressed
const float JOG_DISTANCE_MM   = 2.0;   

long lastScore1 = 0;
long lastScore2 = 0;

void setup() {
  Serial.begin(9600);

  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN,  OUTPUT);
  pinMode(Y_STEP_PIN, OUTPUT);
  pinMode(Y_DIR_PIN,  OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);

  // enable drivers
  digitalWrite(ENABLE_PIN, LOW);
  // default forward
  digitalWrite(X_DIR_PIN, HIGH);
  digitalWrite(Y_DIR_PIN, HIGH);

  // configure jog buttons
  pinMode(BUTTON1_PIN, INPUT_PULLUP);
  pinMode(BUTTON2_PIN, INPUT_PULLUP);

  Serial.println("Ready: send <axis>,<totalPoints>");
}

void loop() {
  // ── manual jog ─────────────────────────────────────────
  if (digitalRead(BUTTON1_PIN) == LOW) {
    jogMotor(X_STEP_PIN, X_DIR_PIN, JOG_DISTANCE_MM);
    delay(200);
  }
  if (digitalRead(BUTTON2_PIN) == LOW) {
    jogMotor(Y_STEP_PIN, Y_DIR_PIN, JOG_DISTANCE_MM);
    delay(200);
  }

  // ── serial‐driven point moves ──────────────────────────
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() < 3) return;

  int comma = line.indexOf(',');
  if (comma < 1) {
    Serial.println("ERR: bad format");
    return;
  }

  int axis      = line.substring(0, comma).toInt();
  long totalPts = line.substring(comma + 1).toInt();
  if (totalPts < 0) totalPts = 0;

  long deltaPts;
  if (axis == 1) {
    deltaPts   = totalPts - lastScore1;
    lastScore1 = totalPts;
  } else if (axis == 2) {
    deltaPts   = totalPts - lastScore2;
    lastScore2 = totalPts;
  } else {
    Serial.println("ERR: bad axis");
    return;
  }

  if (deltaPts <= 0) {
    char buf[64];
    snprintf(buf, sizeof(buf), "Axis=%d no new points (total=%ld)", axis, totalPts);
    Serial.println(buf);
    return;
  }

  // choose mm/point
  float mm_per_point = MM_PER_POINT;
  if ((totalPts >= 25 && totalPts <= 30) ||
      (totalPts >= 55 && totalPts <= 60)) {
    mm_per_point = MM_PER_POINT_BEND;
  }

  // compute how many steps = *one* cribbage point
  long steps_per_point = (long)((mm_per_point / MM_PER_REV) * STEPS_PER_REV + 0.5);

  {
    char buf[80];
    snprintf(buf, sizeof(buf),
      "Axis=%d  total=%ld  Δpts=%ld  steps/pt=%ld",
      axis, totalPts, deltaPts, steps_per_point);
    Serial.println(buf);
  }

  // now do *deltaPts* individual moves
  for (long p = 0; p < deltaPts; p++) {
    if (axis == 1) {
      driveMotor(steps_per_point, X_STEP_PIN, X_DIR_PIN);
    } else {
      driveMotor(steps_per_point, Y_STEP_PIN, Y_DIR_PIN);
    }
    delay(1200);  // small pause between each point‐step
  }
}

//───────────────────────────────────────────────────────────
// driveMotor: pulses stepPin/dirPin “steps” times
void driveMotor(long steps, int stepPin, int dirPin) {
  bool forward = (steps >= 0);
  digitalWrite(dirPin, forward ? HIGH : LOW);
  long n = labs(steps);
  for (long i = 0; i < n; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(5);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(STEP_DELAY_US);
  }
}

// jogMotor: small manual jog in mm
void jogMotor(int stepPin, int dirPin, float distance_mm) {
  long steps_to_move = (long)((distance_mm / MM_PER_REV) * STEPS_PER_REV + 0.5);
  driveMotor(steps_to_move, stepPin, dirPin);
}

//
//// Motor 1 (X Axis)
//#define X_STEP_PIN 2
//#define X_DIR_PIN 5
//
//// Motor 2 (Y Axis)
//#define Y_STEP_PIN 3
//#define Y_DIR_PIN 6
//
//// Shared ENABLE pin for CNC Shield
//#define ENABLE_PIN 8
//
//// Button Pins
//#define BUTTON1_PIN A0  // Button for Motor 1 (X-axis)
//#define BUTTON2_PIN A1  // Button for Motor 2 (Y-axis)
//
//// Constants
//const float MM_PER_REV = 25.13;      // Chain travel per full 200-step revolution
//const int STEPS_PER_REV = 200;        // Full steps per revolution
//const int STEP_DELAY_US = 1800;       // Microseconds between steps (lower = faster)
//const float MOVE_DISTANCE_MM = 3;   // Distance to move around corners
//const float MOVE_DISTANCE_MM = 3;   // Distance to move per straight line
//
//
//void setup() {
//  pinMode(X_STEP_PIN, OUTPUT);
//  pinMode(X_DIR_PIN, OUTPUT);
//
//  pinMode(Y_STEP_PIN, OUTPUT);
//  pinMode(Y_DIR_PIN, OUTPUT);
//
//  pinMode(ENABLE_PIN, OUTPUT);
//
//  pinMode(BUTTON1_PIN, INPUT_PULLUP); // Buttons with pull-up
//  pinMode(BUTTON2_PIN, INPUT_PULLUP);
//
//  // Enable motors (LOW to enable drivers)
//  digitalWrite(ENABLE_PIN, LOW);
//
//  // Set motor directions forward
//  digitalWrite(X_DIR_PIN, HIGH);
//  digitalWrite(Y_DIR_PIN, HIGH);
//}
//
//void loop() {
//  // Check Button 1
//  if (digitalRead(BUTTON1_PIN) == LOW) {
//    moveMotor(X_STEP_PIN, MOVE_DISTANCE_MM);
//    delay(100); // Small delay to prevent multiple triggers per press
//  }
//
//  // Check Button 2
//  if (digitalRead(BUTTON2_PIN) == LOW) {
//    moveMotor(Y_STEP_PIN, MOVE_DISTANCE_MM);
//    delay(100); // Small delay to prevent multiple triggers per press
//  }
//}
//
//
//
//
//
//
//// Function to move a single motor a specific distance in mm
//void moveMotor(int stepPin, float distance_mm) {
//  int steps_to_move = (int)((distance_mm / MM_PER_REV) * STEPS_PER_REV);
//
//  for (int i = 0; i < steps_to_move; i++) {
//    digitalWrite(stepPin, HIGH);
//    delayMicroseconds(5);
//    digitalWrite(stepPin, LOW);
//    delayMicroseconds(STEP_DELAY_US);
//  }
//}
//
//
//
//
//
//// CribbageStepperByPoints.ino
//// Listens for "<axis>,<totalPoints>\n", steps each motor by
//// (newPoints × MM_PER_POINT) worth of travel.
//
//#define X_STEP_PIN     2
//#define X_DIR_PIN      5
//
//#define Y_STEP_PIN     3
//#define Y_DIR_PIN      6
//
//#define ENABLE_PIN     8
//
//// How much chain (or board movement) per cribbage point?
//const float MM_PER_POINT  = 4.6;    // e.g. 4.6 mm per point
//const float MM_PER_REV    = 25.13;  // 1 full revolution = 25.13 mm
//const int   STEPS_PER_REV = 200;    // full steps
//const int   STEP_DELAY_US = 800;    // microseconds between pulses
//
//long lastScore1 = 0;
//long lastScore2 = 0;
//
//void setup() {
//  Serial.begin(9600);
//  pinMode(X_STEP_PIN, OUTPUT);  pinMode(X_DIR_PIN, OUTPUT);
//  pinMode(Y_STEP_PIN, OUTPUT);  pinMode(Y_DIR_PIN, OUTPUT);
//  pinMode(ENABLE_PIN, OUTPUT);
//
//  digitalWrite(ENABLE_PIN, LOW);    // enable drivers
//  digitalWrite(X_DIR_PIN, HIGH);    // default forward
//  digitalWrite(Y_DIR_PIN, HIGH);
//
//  Serial.println("Ready: send <axis>,<totalPoints>");
//}
//
//void loop() {
//  if (!Serial.available()) return;
//  String line = Serial.readStringUntil('\n');
//  line.trim();
//  if (line.length() < 3) return;
//
//  int comma = line.indexOf(',');
//  if (comma < 1) {
//    Serial.println("ERR: bad format");
//    return;
//  }
//
//  int axis       = line.substring(0, comma).toInt(); 
//  long totalPts  = line.substring(comma+1).toInt();
//
//  // figure out delta
//  long deltaPts;
//  if (axis == 1) {
//    deltaPts = totalPts - lastScore1;
//    lastScore1 = totalPts;
//  }
//  else if (axis == 2) {
//    deltaPts = totalPts - lastScore2;
//    lastScore2 = totalPts;
//  }
//  else {
//    Serial.println("ERR: bad axis");
//    return;
//  }
//
//  if (deltaPts <= 0) {
//    Serial.print("No new points on axis %d\n", axis);
//    return;
//  }
//
//  // compute mm to move
//  float moveMM = deltaPts * MM_PER_POINT;
//  // convert mm to steps
//  long steps = lround((moveMM / MM_PER_REV) * STEPS_PER_REV);
//
//  Serial.print("Axis=%d  Δpts=%ld  Δmm=%.2f  steps=%ld\n",
//                axis, deltaPts, moveMM, steps);
//
//  // step the appropriate motor
//  if (axis == 1) {
//    driveMotor(steps, X_STEP_PIN, X_DIR_PIN);
//  } else {
//    driveMotor(steps, Y_STEP_PIN, Y_DIR_PIN);
//  }
//}
//
//// driveMotor: positive=forward, negative=back
//void driveMotor(long steps, int stepPin, int dirPin) {
//  bool fwd = (steps >= 0);
//  digitalWrite(dirPin, fwd ? HIGH : LOW);
//  long n = labs(steps);
//  for (long i = 0; i < n; i++) {
//    digitalWrite(stepPin, HIGH);
//    delayMicroseconds(5);
//    digitalWrite(stepPin, LOW);
//    delayMicroseconds(STEP_DELAY_US);
//  }
//}
