#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- MASTER PINOUT ---
const int SENSOR_VIBE    = 2;
const int TOUCH_LEFT     = 3;
const int TOUCH_RIGHT    = 4;
const int TOUCH_TOP      = 7;
const int TOUCH_FRONT_L  = 8;
const int TOUCH_FRONT_R  = 12;
const int BUTTON_PIN     = 10; // AI Voice Button
const int LDR_PIN        = A1; // Light Sensor

// --- RGB PINOUT ---
const int RED_PIN        = 5;
const int GREEN_PIN      = 6;
const int BLUE_PIN       = 9;

// --- STATE TRACKING ---
bool leftState   = false;
bool rightState  = false;
bool topState    = false;
bool frontLState = false;
bool frontRState = false;

// --- SMART BUTTON STATE VARIABLES ---
bool lastButtonReading = HIGH; 
bool isButtonHeldState = false;
unsigned long buttonPressStartTime = 0;
bool speechModeActivated = false;
const unsigned long HOLD_THRESHOLD = 350; // Milliseconds to distinguish hold vs click

// --- LDR DARK MODE VARIABLES ---
const int DARK_THRESHOLD  = 200;  
const int LIGHT_THRESHOLD = 250;  // Hysteresis buffer
bool isDark = false;

// --- AUDIO ENGINE STATES ---
bool isSnoring = false;
unsigned long lastSnoreTime = 0;
bool isWakingUp = false;
unsigned long wakeupTriggerTime = 0;

void setup() {
  Serial.begin(250000);

  pinMode(SENSOR_VIBE, INPUT);
  pinMode(TOUCH_LEFT, INPUT);
  pinMode(TOUCH_RIGHT, INPUT);
  pinMode(TOUCH_TOP, INPUT);
  pinMode(TOUCH_FRONT_L, INPUT);
  pinMode(TOUCH_FRONT_R, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LDR_PIN, INPUT);

  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    for (;;);
  }

  Wire.setClock(400000); 

  display.clearDisplay();
  display.display();
  Serial.print('Y'); 
}

// =====================================================
// AUDIO ENGINE (NON-BLOCKING)
// =====================================================
void playSound(int freq, int duration) {
  tone(13, freq, duration);
}

void triggerWakeup() {
  tone(13, 800, 50);
  isWakingUp = true;
  wakeupTriggerTime = millis();
}

void audioEngine() {
  unsigned long now = millis();

  if (isWakingUp && (now - wakeupTriggerTime > 60)) {
    tone(13, 1600, 100); 
    isWakingUp = false;  
  }
  
  if (isSnoring && (now - lastSnoreTime > 3000)) {
    tone(13, 70, 250); 
    lastSnoreTime = now;
  }
}

// =====================================================
// VISUAL EFFECTS & DYNAMIC SPIRAL
// =====================================================
void pastelSpiral(int currentLightLevel) {
  static unsigned long lastUpdate = 0;
  static float t = 0.0;
  unsigned long now = millis();
  if (now - lastUpdate < 15) return;
  lastUpdate = now;

  t += 0.04; 
  if (t >= 6.28318) t -= 6.28318;

  int maxAmplitude = 18;
  int baselineBrightness = 28;

  if (isDark) {
    maxAmplitude = 1;         
    baselineBrightness = 1;    
  } else {
    baselineBrightness = map(currentLightLevel, 300, 1023, 15, 100);
    maxAmplitude       = map(currentLightLevel, 300, 1023, 10, 50);
    
    baselineBrightness = constrain(baselineBrightness, 15, 100);
    maxAmplitude       = constrain(maxAmplitude, 10, 50);
  }

  int r = (sin(t) * maxAmplitude) + baselineBrightness;
  int g = (sin(t + 2.094) * maxAmplitude) + baselineBrightness; 
  int b = (sin(t + 4.188) * maxAmplitude) + baselineBrightness;

  r = constrain(r, 0, 255);
  g = constrain(g, 0, 255);
  b = constrain(b, 0, 255);

  analogWrite(RED_PIN, r);
  analogWrite(GREEN_PIN, g);
  analogWrite(BLUE_PIN, b);
}

void playNightmare() {
  display.clearDisplay();
  display.setTextSize(2); 
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 16);
  display.println("HOPE U HAVE");
  display.setCursor(0, 36);
  display.println("A NIGHTMARE");
  display.display();
  display.startscrollleft(0x00, 0x0F);

  analogWrite(RED_PIN, 150);
  analogWrite(GREEN_PIN, 0);
  analogWrite(BLUE_PIN, 0);

  const char* morse = ".... --- .--. . / ..- / .... .- ...- . / .- / -. .. --. .... - -- .- .-. .";
  int dotTime = 75; 
  int pitch = 600;  

  for (int i = 0; morse[i] != '\0'; i++) {
    if (morse[i] == '.') {
      tone(13, pitch, dotTime);
      delay(dotTime * 2); 
    } else if (morse[i] == '-') {
      tone(13, pitch, dotTime * 3);
      delay(dotTime * 4); 
    } else if (morse[i] == ' ') {
      delay(dotTime * 2); 
    } else if (morse[i] == '/') {
      delay(dotTime * 6); 
    }
  }

  display.stopscroll();
  display.clearDisplay();
  display.display();
  Serial.print('Y'); 
}

// =====================================================
// MAIN CORE LOOP
// =====================================================
void loop() {
  audioEngine(); 
  
  // --- 1. LDR LIGHT SENSOR MONITORING ---
  int lightLevel = analogRead(LDR_PIN);
  
  if (!isDark && lightLevel < DARK_THRESHOLD) {
    isDark = true;
    Serial.write('D'); 
  } 
  else if (isDark && lightLevel > LIGHT_THRESHOLD) {
    isDark = false;
    Serial.write('d'); 
  }

  // Pass light readings directly into the dynamic brightness engine
  pastelSpiral(lightLevel);

  // --- 2. FIXED ADVANCED AI BUTTON TIMING ENGINE ---
  bool currentButtonReading = digitalRead(BUTTON_PIN);
  unsigned long currentMillis = millis();

  // Button newly pressed down
  if (currentButtonReading == LOW && lastButtonReading == HIGH) {
    buttonPressStartTime = currentMillis;
    isButtonHeldState = true;
    speechModeActivated = false;
  }

  // Button is actively being held down
  if (isButtonHeldState && currentButtonReading == LOW) {
    if (!speechModeActivated && (currentMillis - buttonPressStartTime >= HOLD_THRESHOLD)) {
      // User held the button long enough -> Activate Voice Mode
      playSound(2000, 30);
      Serial.print('V'); // Signal Python: Start recording voice
      speechModeActivated = true;
    }
  }

  // Button released
  if (currentButtonReading == HIGH && lastButtonReading == LOW) {
    isButtonHeldState = false;
    
    if (speechModeActivated) {
      // Was in Voice Mode -> End recording
      playSound(1800, 30);
      Serial.print('v'); // Signal Python: Stop voice recording
    } else {
      // Short click detected! -> Activate Keyboard Overlay Mode
      playSound(2200, 20);
      Serial.print('K'); // Signal Python: Unique command to pop up entry window immediately
    }
    speechModeActivated = false;
  }
  lastButtonReading = currentButtonReading;

  // --- 3. PHYSICAL TOUCH CAPACITIVE SENSORS ---
  if (digitalRead(TOUCH_TOP) == HIGH) {
    if (!topState) {
      playSound(1200, 40);
      Serial.print('P');
      topState = true;
    }
  } else if (digitalRead(TOUCH_TOP) == LOW && topState) {
    Serial.print('p');
    topState = false;
  }

  if (digitalRead(TOUCH_RIGHT) == HIGH && !rightState) {
    playSound(1500, 40);
    Serial.print('N');
    rightState = true;
  } else if (digitalRead(TOUCH_RIGHT) == LOW) {
    rightState = false;
  }

  if (digitalRead(TOUCH_LEFT) == HIGH && !leftState) {
    playSound(1000, 40);
    Serial.print('B');
    leftState = true;
  } else if (digitalRead(TOUCH_LEFT) == LOW) {
    leftState = false;
  }

  if (digitalRead(TOUCH_FRONT_L) == HIGH && !frontLState) {
    playSound(800, 40);
    Serial.print('L');
    frontLState = true;
  } else if (digitalRead(TOUCH_FRONT_L) == LOW && frontLState) {
    Serial.print('l');
    frontLState = false;
  }

  if (digitalRead(TOUCH_FRONT_R) == HIGH && !frontRState) {
    playSound(900, 40);
    Serial.print('R');
    frontRState = true;
  } else if (digitalRead(TOUCH_FRONT_R) == LOW && frontRState) {
    Serial.print('r');
    frontRState = false;
  }

  // --- 4. ZERO-COPY SERIAL FRAME DISPLAY ---
  if (Serial.available() > 0) {
    byte cmd = Serial.read();

    if (cmd == 0x01) {
      if (Serial.readBytes(display.getBuffer(), 1024) == 1024) {
        display.display();
        Serial.print('Y'); 
      }
    } 
    else if (cmd == 'E') { playNightmare(); }
    else if (cmd == 'S') { isSnoring = true; } 
    else if (cmd == 'W') { 
      isSnoring = false; 
      triggerWakeup(); 
    } 
  }
}