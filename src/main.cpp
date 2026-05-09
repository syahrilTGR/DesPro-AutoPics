#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <WiFiManager.h>
#include <FirebaseESP32.h>
#include <time.h>

// --- KONFIGURASI FIREBASE ---
#define API_KEY "AIzaSyB7lfoTolV2CUvIW47_JeaYnwobw1RCEHg"
#define DATABASE_URL "parking-600df-default-rtdb.asia-southeast1.firebasedatabase.app"

// --- KONFIGURASI RFID ---
#define RST_PIN   4
#define SS_MOT    21
#define SS_MOB    22
#define SS_EXIT   25

MFRC522 rfidMot(SS_MOT, RST_PIN);
MFRC522 rfidMob(SS_MOB, RST_PIN);
MFRC522 rfidExit(SS_EXIT, RST_PIN);

// --- KONFIGURASI SISTEM ---
const int DISTANCE_THRESHOLD = 8;
const unsigned long GATE_HOLD_TIME = 5000;
const unsigned long SCAN_INTERVAL = 100;
const int TARIF_PER_JAM = 2000; // Contoh tarif Rp 2.000 per jam

struct Gate {
  const char* name;
  int trig, echo, servoPin;
  Servo sv;
  bool isOpen;
  unsigned long lastOpen;
  int* availCount;
  bool isExit;
  MFRC522* rfid;
};

int availMot = 0;
int availMob = 0;

Gate gts[3] = {
  {"MOTOR_IN", 32, 33, 13, Servo(), false, 0, &availMot, false, &rfidMot},
  {"MOBIL_IN", 27, 26, 12, Servo(), false, 0, &availMob, false, &rfidMob},
  {"EXIT_ALL", 16, 17, 14, Servo(), false, 0, nullptr,   true,  &rfidExit}
};

WiFiManager wm;
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

int currentIdx = 0;
unsigned long lastScan = 0;

void streamCb(StreamData data) {
  String p = data.dataPath();
  String type = data.dataType();
  
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
}

long getD(int t, int e) {
  digitalWrite(t, LOW); delayMicroseconds(2);
  digitalWrite(t, HIGH); delayMicroseconds(10);
  digitalWrite(t, LOW);
  long dur = pulseIn(e, HIGH, 20000);
  return (dur == 0) ? 999 : dur * 0.034 / 2;
}

String getUID(MFRC522* rfid) {
  String uidStr = "";
  for (byte i = 0; i < rfid->uid.size; i++) {
    uidStr += String(rfid->uid.uidByte[i] < 0x10 ? "0" : "");
    uidStr += String(rfid->uid.uidByte[i], HEX);
  }
  uidStr.toUpperCase();
  return uidStr;
}

void openGate(Gate &g, unsigned long now) {
  Serial.printf("🚀 %s: OPEN\n", g.name);
  g.sv.write(90);
  g.isOpen = true;
  g.lastOpen = now;
}

void processEntrance(Gate &g, String uid, unsigned long now) {
  if (g.availCount != nullptr && *(g.availCount) <= 0) {
    Serial.printf("⚠️ %s: FULL! (Tunggu slot kosong)\n", g.name);
    return;
  }

  String path = "/users/" + uid;
  if (Firebase.getInt(fbdo, path + "/balance")) {
    int balance = fbdo.intData();
    
    // Ambil status kartu untuk memastikan kartu berstatus aktif/ready
    String status = "inactive";
    if (Firebase.getString(fbdo, path + "/status")) {
      status = fbdo.stringData();
    }

    if (status == "active" || status == "left") {
      if (balance > 0) {
        openGate(g, now);
        Firebase.setString(fbdo, path + "/status", "parked");
        time_t tNow = time(nullptr);
        Firebase.setInt(fbdo, path + "/parked_at", tNow);
        Serial.printf("✅ Entrance Sukses. UID: %s, Saldo: %d\n", uid.c_str(), balance);
      } else {
        Serial.printf("❌ Saldo tidak cukup untuk UID: %s (Saldo: %d)\n", uid.c_str(), balance);
      }
    } else if (status == "parked") {
      Serial.printf("❌ Kartu UID %s sudah berada di dalam area parkir (Status: parked)!\n", uid.c_str());
    } else {
      Serial.printf("❌ Kartu UID %s tidak aktif atau belum diaktivasi (Status: %s)!\n", uid.c_str(), status.c_str());
    }
  } else {
    Serial.printf("❌ Kartu belum terdaftar! UID: %s\n", uid.c_str());
    String tapPath = "/unregistered_taps/" + String(g.name);
    Firebase.setString(fbdo, tapPath + "/uid", uid);
    time_t tNow = time(nullptr);
    Firebase.setInt(fbdo, tapPath + "/timestamp", tNow);
    Serial.printf("📡 Mengirim data tap terakhir ke Firebase: %s = %s\n", tapPath.c_str(), uid.c_str());
  }
}

void processExit(Gate &g, String uid, unsigned long now) {
  String path = "/users/" + uid;
  
  if (Firebase.getString(fbdo, path + "/status")) {
    String status = fbdo.stringData();
    if (status != "parked") {
      Serial.printf("❌ Kendaraan tidak terdaftar sedang parkir: %s\n", uid.c_str());
      return;
    }
    
    int parked_at = 0;
    if (Firebase.getInt(fbdo, path + "/parked_at")) {
      parked_at = fbdo.intData();
    }
    
    int balance = 0;
    if (Firebase.getInt(fbdo, path + "/balance")) {
      balance = fbdo.intData();
    }
    
    time_t tNow = time(nullptr);
    double hours = difftime(tNow, parked_at) / 3600.0;
    if (hours < 1.0) hours = 1.0; // Anggap minimal parkir 1 jam
    
    int cost = (int)hours * TARIF_PER_JAM;
    if (balance >= cost) {
      balance -= cost;
      Firebase.setInt(fbdo, path + "/balance", balance);
      Firebase.setString(fbdo, path + "/status", "left");
      openGate(g, now);
      Serial.printf("✅ Exit Sukses. UID: %s, Biaya: %d, Sisa Saldo: %d\n", uid.c_str(), cost, balance);
    } else {
      Serial.printf("❌ Saldo tidak cukup untuk Exit! UID: %s, Biaya: %d, Saldo: %d\n", uid.c_str(), cost, balance);
    }
  } else {
    Serial.printf("❌ Data pengguna tidak ditemukan! UID: %s\n", uid.c_str());
    String tapPath = "/unregistered_taps/" + String(g.name);
    Firebase.setString(fbdo, tapPath + "/uid", uid);
    time_t tNow = time(nullptr);
    Firebase.setInt(fbdo, tapPath + "/timestamp", tNow);
    Serial.printf("📡 Mengirim data tap terakhir ke Firebase: %s = %s\n", tapPath.c_str(), uid.c_str());
  }
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
  
  if (!Firebase.beginStream(fbdo, "/parkir/ringkasan")) {
    Serial.printf("Stream Error: %s\n", fbdo.errorReason().c_str());
  }
  Firebase.setStreamCallback(fbdo, streamCb, [](bool t){});

  SPI.begin();
  rfidMot.PCD_Init();
  rfidMob.PCD_Init();
  rfidExit.PCD_Init();
  Serial.println("RFID Init OK");

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
      if (!g.isOpen) {
        if (g.rfid->PICC_IsNewCardPresent() && g.rfid->PICC_ReadCardSerial()) {
          String uid = getUID(g.rfid);
          g.rfid->PICC_HaltA(); // Halt reading
          
          if (g.isExit) {
            processExit(g, uid, now);
          } else {
            processEntrance(g, uid, now);
          }
        }
      } else {
        g.lastOpen = now;
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

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "reswi") {
      Serial.println("♻️ Mereset WiFi & Restarting...");
      wm.resetSettings();
      delay(1000);
      ESP.restart();
    }
  }
}