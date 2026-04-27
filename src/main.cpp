#include <Arduino.h>
#include <ESP32Servo.h>
#include <WiFiManager.h>
#include <FirebaseESP32.h>

// --- KONFIGURASI FIREBASE ---
#define API_KEY "AIzaSyB7lfoTolV2CUvIW47_JeaYnwobw1RCEHg"
// Gunakan host saja tanpa https:// dan / di akhir
#define DATABASE_URL "parking-600df-default-rtdb.asia-southeast1.firebasedatabase.app"

// --- KONFIGURASI SISTEM ---
const int DISTANCE_THRESHOLD = 8;
const unsigned long GATE_HOLD_TIME = 5000;
const unsigned long SCAN_INTERVAL = 100;

struct Gate {
  const char* name;
  int trig, echo, servoPin;
  Servo sv;
  bool isOpen;
  unsigned long lastOpen;
  int* availCount;
  bool isExit;
};

int availMot = 0;
int availMob = 0;

Gate gts[3] = {
  {"MOTOR_IN", 32, 33, 13, Servo(), false, 0, &availMot, false},
  {"MOBIL_IN", 27, 26, 12, Servo(), false, 0, &availMob, false},
  {"EXIT_ALL", 16, 17, 14, Servo(), false, 0, nullptr,   true}
};

WiFiManager wm;
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

int currentIdx = 0;
unsigned long lastScan = 0;

// Callback membaca status dari Firebase (Diupdate secara realtime oleh Python)
void streamCb(StreamData data) {
  String p = data.dataPath();
  String type = data.dataType();
  
  Serial.printf("🔥 Stream Triggered! Path: %s, Type: %s\n", p.c_str(), type.c_str());

  if (type == "int") {
    if (p == "/mobil/kosong") availMob = data.intData();
    else if (p == "/motor/kosong") availMot = data.intData();
  } 
  else if (type == "json") {
    FirebaseJson &json = data.jsonObject();
    FirebaseJsonData r;
    if (p == "/mobil") {
      if (json.get(r, "kosong")) availMob = r.intValue;
    } else if (p == "/motor") {
      if (json.get(r, "kosong")) availMot = r.intValue;
    } else if (p == "/") {
      if (json.get(r, "mobil/kosong")) availMob = r.intValue;
      if (json.get(r, "motor/kosong")) availMot = r.intValue;
    }
  }
  
  Serial.printf("📊 STATUS AKTIF -> Mobil Kosong: %d, Motor Kosong: %d\n", availMob, availMot);
}

long getD(int t, int e) {
  digitalWrite(t, LOW); delayMicroseconds(2);
  digitalWrite(t, HIGH); delayMicroseconds(10);
  digitalWrite(t, LOW);
  long dur = pulseIn(e, HIGH, 20000);
  return (dur == 0) ? 999 : dur * 0.034 / 2;
}

void setup() {
  Serial.begin(115200);
  
  wm.setConfigPortalBlocking(false);
  wm.autoConnect("AutoPics_Gate_AP");

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("NTP Sync...");
  time_t now = time(nullptr);
  while (now < 8 * 3600 * 2) { delay(500); Serial.print("."); now = time(nullptr); }
  Serial.println(" OK");

  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  
  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("Auth OK");
  }

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  
  delay(1000); 
  
  // Stream data dari ringkasan parkir (hasil hitungan Python)
  if (!Firebase.beginStream(fbdo, "/parkir/ringkasan")) {
    Serial.printf("Stream Error: %s\n", fbdo.errorReason().c_str());
  }
  Firebase.setStreamCallback(fbdo, streamCb, [](bool t){});

  for (int i = 0; i < 3; i++) {
    pinMode(gts[i].trig, OUTPUT);
    pinMode(gts[i].echo, INPUT);
    gts[i].sv.attach(gts[i].servoPin);
    gts[i].sv.write(0);
  }
  
  Serial.println(">>> GATE SYSTEM READY <<<");
}

void loop() {
  wm.process();
  unsigned long now = millis();

  if (now - lastScan >= SCAN_INTERVAL) {
    lastScan = now;
    Gate &g  = gts[currentIdx];
    long dist = getD(g.trig, g.echo);

    if (dist > 0 && dist < DISTANCE_THRESHOLD) {
      // Selalu boleh buka jika gerbang KELUAR
      // Jika gerbang MASUK, cek apakah ada slot kosong (availCount > 0)
      bool canOpen = g.isExit || (g.availCount != nullptr && *(g.availCount) > 0);

      if (canOpen) {
        if (!g.isOpen) {
          Serial.printf("🚀 %s: OPEN\n", g.name);
          g.sv.write(90);
          g.isOpen = true;
          // CATATAN: Tidak ada update Firebase di sini. 
          // Python akan mendeteksi mobil masuk/keluar via kamera.
        }
        g.lastOpen = now; 
      } else {
        static unsigned long lastMsg = 0;
        if (now - lastMsg > 2000) {
          Serial.printf("⚠️ %s: FULL! (Tunggu slot kosong)\n", g.name);
          lastMsg = now;
        }
      }
    }
    currentIdx = (currentIdx + 1) % 3;
  }

  for (int i = 0; i < 3; i++) {
    if (gts[i].isOpen && (now - gts[i].lastOpen >= GATE_HOLD_TIME)) {
      Serial.printf("🔒 %s: CLOSE\n", gts[i].name);
      gts[i].sv.write(0);
      gts[i].isOpen = false;
    }
  }

  // Cek perintah dari Serial Monitor
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "reswi") {
      Serial.println("♻️  Mereset WiFi & Restarting...");
      wm.resetSettings();
      delay(1000);
      ESP.restart();
    }
  }
}