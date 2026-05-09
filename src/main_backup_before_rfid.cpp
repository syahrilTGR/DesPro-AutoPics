#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <WiFiManager.h>
#include <FirebaseESP32.h>

// --- KONFIGURASI RFID ---
#define RST_PIN 4
#define SS_MOT 21
#define SS_MOB 22
#define SS_EXIT 25

MFRC522 rfidMot(SS_MOT, RST_PIN);
MFRC522 rfidMob(SS_MOB, RST_PIN);
MFRC522 rfidExit(SS_EXIT, RST_PIN);

// --- KONFIGURASI FIREBASE ---
#define API_KEY "AIzaSyB7lfoTolV2CUvIW47_JeaYnwobw1RCEHg"
// Gunakan host saja tanpa https:// dan / di akhir
#define DATABASE_URL "parking-600df-default-rtdb.asia-southeast1.firebasedatabase.app"

// --- KONFIGURASI SISTEM ---
const int DISTANCE_THRESHOLD = 8;
const unsigned long GATE_HOLD_TIME = 5000;
const unsigned long SCAN_INTERVAL = 100;
const int DAILY_RATE = 5000; // Tarif parkir perhari

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

String getUIDString(byte *uid, byte uidSize) {
  String uidStr = "";
  for (byte i = 0; i < uidSize; i++) {
    if (uid[i] < 0x10) uidStr += "0";
    uidStr += String(uid[i], HEX);
  }
  uidStr.toUpperCase();
  return uidStr;
}

String getFormattedTime() {
  time_t now = time(nullptr);
  struct tm timeinfo;
  localtime_r(&now, &timeinfo);
  char buf[30];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(buf);
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

  SPI.begin();
  rfidMot.PCD_Init();
  rfidMob.PCD_Init();
  rfidExit.PCD_Init();
  Serial.println("RFID Readers Initialized");

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
        static unsigned long lastWaitMsg = 0;
        if (now - lastWaitMsg > 1500) {
          Serial.printf("⏳ %s: Kendaraan Terdeteksi. Tempelkan Kartu RFID...\n", g.name);
          lastWaitMsg = now;
        }

        // Cek kartu RFID
        if (g.rfid->PICC_IsNewCardPresent() && g.rfid->PICC_ReadCardSerial()) {
          String uid = getUIDString(g.rfid->uid.uidByte, g.rfid->uid.size);
          Serial.printf("💳 RFID Tap (%s): UID %s\n", g.name, uid.c_str());
          
          g.rfid->PICC_HaltA(); // Halt PICC agar tidak mendeteksi berkali-kali sangat cepat

          // Validasi Firebase
          String userPath = "/users/" + uid;
          FirebaseJsonData userData;
          
          if (Firebase.getJSON(fbdo, userPath)) {
            FirebaseJson &json = fbdo.jsonObject();
            String name = "";
            int balance = 0;
            String status = "";
            
            json.get(userData, "name");
            if (userData.success) name = userData.stringValue;
            
            json.get(userData, "balance");
            if (userData.success) balance = userData.intValue;
            
            json.get(userData, "status");
            if (userData.success) status = userData.stringValue;
            
            Serial.printf("👤 User: %s, Saldo: Rp%d, Status: %s\n", name.c_str(), balance, status.c_str());

            if (!g.isExit) {
              // --- LOGIKA PINTU MASUK ---
              if (g.availCount != nullptr && *(g.availCount) <= 0) {
                Serial.printf("⚠️ %s: FULL! Slot parkir penuh.\n", g.name);
              } else if (status == "parked") {
                Serial.printf("⚠️ %s: Ditolak. Kartu masih tercatat di dalam parkiran!\n", g.name);
              } else {
                // Berhasil masuk
                String timeNow = getFormattedTime();
                Firebase.setString(fbdo, userPath + "/status", "parked");
                Firebase.setString(fbdo, userPath + "/parked_at", timeNow);
                Serial.printf("✅ %s: Akses Masuk Diberikan!\n", g.name);
                g.sv.write(90);
                g.isOpen = true;
                g.lastOpen = now;
              }
            } else {
              // --- LOGIKA PINTU KELUAR ---
              if (status != "parked") {
                 Serial.printf("⚠️ %s: Ditolak. Kartu belum melakukan Tap In di Pintu Masuk!\n", g.name);
              } else {
                 if (balance >= DAILY_RATE) {
                   int newBalance = balance - DAILY_RATE;
                   Firebase.setInt(fbdo, userPath + "/balance", newBalance);
                   Firebase.setString(fbdo, userPath + "/status", "left");
                   Serial.printf("✅ %s: Akses Keluar Diberikan. Saldo terpotong Rp%d. Sisa: Rp%d\n", g.name, DAILY_RATE, newBalance);
                   g.sv.write(90);
                   g.isOpen = true;
                   g.lastOpen = now;
                 } else {
                   Serial.printf("⚠️ %s: Ditolak. Saldo tidak mencukupi! Minimal Rp%d\n", g.name, DAILY_RATE);
                 }
              }
            }
          } else {
            // Path tidak ditemukan / belum registrasi
            Serial.printf("❌ %s: Akses Ditolak. Kartu Belum Terdaftar! Silakan register.\n", g.name);
          }
        }
      } else {
        // Jika sedang terbuka, perbarui lastOpen agar tidak menutup sebelum mobil lewat
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