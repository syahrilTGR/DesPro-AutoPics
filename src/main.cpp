#include <Arduino.h>
#include <time.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <WiFiClientSecure.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- KONFIGURASI SUPABASE ---
#define SUPABASE_URL "https://hjxiczdakbcrnuntyrjk.supabase.co"
#define SUPABASE_ANON_KEY "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

// --- KONFIGURASI RFID ---
#define RST_PIN   4
#define SS_MOT    21
#define SS_MOB    22
#define SS_EXIT   25

MFRC522 rfidMot(SS_MOT, RST_PIN);
MFRC522 rfidMob(SS_MOB, RST_PIN);
MFRC522 rfidExit(SS_EXIT, RST_PIN);

// --- KONFIGURASI SISTEM ---
const unsigned long GATE_HOLD_TIME = 5000;
const unsigned long SCAN_INTERVAL = 100;
const unsigned long POLL_INTERVAL = 5000;

struct Gate {
  const char* name;
  int trig, echo, servoPin;
  Servo sv;
  bool isOpen;
  unsigned long lastOpen;
  bool isExit;
  MFRC522* rfid;
  int defaultDist;
  unsigned long stableEmptyTime;
  bool hasEntered;
};

int availSlotsMotor = 0; // Slot kosong motor
int availSlotsMobil = 0;  // Slot kosong mobil

Gate gts[3] = {
  {"MOTOR_IN", 32, 33, 13, Servo(), false, 0, false, &rfidMot, 5,  0, false},
  {"MOBIL_IN", 27, 26, 12, Servo(), false, 0, false, &rfidMob, 10, 0, false},
  {"EXIT_ALL", 16, 17, 14, Servo(), false, 0, true,  &rfidExit, 10, 0, false}
};

WiFiManager wm;
SemaphoreHandle_t httpMutex;
int currentIdx = 0;
unsigned long lastScan = 0;
unsigned long lastPoll = 0;

// --- UTILITY FUNGSI WAKTU ---
String getISO8601Time() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) return "";
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S.000Z", &timeinfo);
  return String(buffer);
}

time_t parseISO8601(String isoStr) {
  struct tm tm = {0};
  // Format: 2026-06-11T09:12:00
  sscanf(isoStr.c_str(), "%d-%d-%dT%d:%d:%d", &tm.tm_year, &tm.tm_mon, &tm.tm_mday, &tm.tm_hour, &tm.tm_min, &tm.tm_sec);
  tm.tm_year -= 1900;
  tm.tm_mon -= 1;
  return mktime(&tm);
}

// --- UTILITY SUPABASE REST API ---
String execGET(String endpoint) {
  String payload = "";
  if (xSemaphoreTake(httpMutex, pdMS_TO_TICKS(15000)) == pdTRUE) {
    WiFiClientSecure client;
    client.setInsecure(); // Bypass SSL verification agar sangat cepat & hemat memori
    HTTPClient http;
    http.begin(client, String(SUPABASE_URL) + endpoint);
    http.addHeader("apikey", SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Connection", "close");
    int httpCode = http.GET();
    if (httpCode == 200) payload = http.getString();
    http.end();
    client.stop(); // Paksa tutup socket TCP
    xSemaphoreGive(httpMutex);
  }
  return payload;
}

String execPOST(String endpoint, String jsonPayload) {
  String response = "";
  if (xSemaphoreTake(httpMutex, pdMS_TO_TICKS(15000)) == pdTRUE) {
    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;
    http.begin(client, String(SUPABASE_URL) + endpoint);
    http.addHeader("apikey", SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Prefer", "return=representation");
    http.addHeader("Connection", "close");
    int httpCode = http.POST(jsonPayload);
    if (httpCode == 200 || httpCode == 201) response = http.getString();
    http.end();
    client.stop();
    xSemaphoreGive(httpMutex);
  }
  return response;
}

String execPATCH(String endpoint, String jsonPayload) {
  String response = "";
  Serial.println("  -> [PATCH] " + endpoint);
  
  if (xSemaphoreTake(httpMutex, pdMS_TO_TICKS(15000)) == pdTRUE) {
    Serial.println("  -> [PATCH] Mutex taken, connecting...");
    WiFiClientSecure client;
    client.setInsecure();
    
    HTTPClient http;
    http.begin(client, String(SUPABASE_URL) + endpoint);
    http.setTimeout(10000); 
    http.addHeader("apikey", SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Connection", "close");
    
    Serial.println("  -> [PATCH] Sending request...");
    int httpCode = http.sendRequest("PATCH", jsonPayload);
    Serial.printf("  -> [PATCH] httpCode: %d\n", httpCode);
    
    if (httpCode == 200 || httpCode == 201) {
      Serial.println("  -> [PATCH] Reading response...");
      response = http.getString();
    }
    
    Serial.println("  -> [PATCH] Closing...");
    http.end();
    client.stop();
    xSemaphoreGive(httpMutex);
    Serial.println("  <- [PATCH] Done.");
  } else {
    Serial.println("  <- [RESP] Mutex Timeout!");
  }
  return response;
}

// --- LOGIKA PARKIR ---
void pollParkingSlots() {
  String response = execGET("/rest/v1/parking_slots?status=eq.EMPTY&select=slot_id");
  int countMotor = 0;
  int countMobil = 0;
  
  if (response.length() > 0 && response != "[]") {
    JsonDocument doc;
    deserializeJson(doc, response);
    for (JsonObject slot : doc.as<JsonArray>()) {
      String slotId = slot["slot_id"].as<String>();
      int slotNum = slotId.toInt();
      if (slotNum >= 1 && slotNum <= 7) {
        countMobil++;
      } else {
        countMotor++;
      }
    }
  }
  
  availSlotsMotor = countMotor;
  availSlotsMobil = countMobil;
  Serial.printf("📊 Slot Kosong — Motor: %d | Mobil: %d\n", countMotor, countMobil);
}

long getD(int t, int e) {
  long d1, d2, d3;
  auto readPulse = [&]() -> long {
    digitalWrite(t, LOW); delayMicroseconds(2);
    digitalWrite(t, HIGH); delayMicroseconds(10);
    digitalWrite(t, LOW);
    long dur = pulseIn(e, HIGH, 20000);
    return (dur == 0) ? 999 : dur * 0.034 / 2;
  };
  d1 = readPulse(); delay(2);
  d2 = readPulse(); delay(2);
  d3 = readPulse();
  
  if ((d1 >= d2 && d1 <= d3) || (d1 >= d3 && d1 <= d2)) return d1;
  if ((d2 >= d1 && d2 <= d3) || (d2 >= d3 && d2 <= d1)) return d2;
  return d3;
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
  g.hasEntered = false;
  g.stableEmptyTime = 0;
}

void processEntrance(Gate &g, String uid, unsigned long now, bool isMotor) {
  int avail = isMotor ? availSlotsMotor : availSlotsMobil;
  if (avail <= 0) {
    Serial.printf("⚠️ %s: FULL! (Tunggu slot kosong)\n", g.name);
    return;
  }

  // Jenis kendaraan ditentukan dari gate mana kartu di-tap
  String vType = isMotor ? "Motor" : "Mobil";

  // 1. Cek apakah RFID terdaftar dan ambil data User
  String rfidRes = execGET("/rest/v1/rfid_cards?uid=eq." + uid + "&select=user_id,users(balance)");
  if (rfidRes == "[]" || rfidRes.length() == 0) {
    Serial.printf("❌ Kartu belum terdaftar! UID: %s\n", uid.c_str());
    return;
  }

  JsonDocument docRfid;
  deserializeJson(docRfid, rfidRes);
  int balance = docRfid[0]["users"]["balance"];

  // Cek saldo minimal (misal Rp 5000)
  if (balance < 5000) {
    Serial.printf("❌ Saldo tidak cukup untuk masuk! UID: %s (Saldo: Rp %d)\n", uid.c_str(), balance);
    return;
  }

  // 2. Cek apakah kendaraan ini sedang parkir (status = PARKED)
  String histRes = execGET("/rest/v1/parking_history?rfid_uid=eq." + uid + "&status=eq.PARKED");
  if (histRes != "[]" && histRes.length() > 0) {
    Serial.printf("❌ Kartu UID %s sudah berada di dalam area parkir!\n", uid.c_str());
    return;
  }

  // 3. Catat Entrance ke parking_history (termasuk vehicle_type dari gate)
  Serial.printf("🔄 Mencatat histori masuk (%s) ke Supabase...\n", vType.c_str());
  String timeIn = getISO8601Time();
  String payload = "{\"rfid_uid\":\"" + uid + "\",\"status\":\"PARKED\",\"vehicle_type\":\"" + vType + "\",\"time_in\":\"" + timeIn + "\"}";
  String postRes = execPOST("/rest/v1/parking_history", payload);
  
  if (postRes.length() > 0) {
    Serial.printf("✅ Entrance Sukses. UID: %s (%s), Saldo: Rp %d\n", uid.c_str(), vType.c_str(), balance);
    openGate(g, now);
  } else {
    Serial.println("⚠️ Gagal mencatat histori entrance.");
  }
}

void processExit(Gate &g, String uid, unsigned long now) {
  // 1. Ambil session parkir aktif & data saldo user
  // vehicle_type dibaca dari parking_history (dicatat saat masuk berdasarkan gate)
  String histRes = execGET("/rest/v1/parking_history?rfid_uid=eq." + uid + "&status=eq.PARKED&select=id,time_in,vehicle_type,rfid_cards(user_id,users(balance))");
  if (histRes == "[]" || histRes.length() == 0) {
    Serial.printf("❌ Kendaraan tidak terdaftar sedang parkir atau kartu salah: %s\n", uid.c_str());
    return;
  }

  JsonDocument docHist;
  deserializeJson(docHist, histRes);
  String histId = docHist[0]["id"].as<String>();
  String timeInStr = docHist[0]["time_in"].as<String>();
  String vType = docHist[0]["vehicle_type"].as<String>();  // Dari histori, bukan rfid_cards
  String userId = docHist[0]["rfid_cards"]["user_id"].as<String>();
  int balance = docHist[0]["rfid_cards"]["users"]["balance"];

  // 2. Kalkulasi Durasi & Tarif
  time_t tIn = parseISO8601(timeInStr);
  time_t tOut = time(nullptr);
  double duration_secs = difftime(tOut, tIn);
  if (duration_secs < 0) duration_secs = 0;
  
  int duration_minutes = ceil(duration_secs / 60.0);
  if (duration_minutes < 1) duration_minutes = 1;

  int cost = 0;
  if (vType == "Motor") {
    cost = 2000; // Base 1 menit
    if (duration_minutes > 1) cost += (duration_minutes - 1) * 30;
  } else {
    cost = 5000; // Base 1 menit
    if (duration_minutes > 1) cost += (duration_minutes - 1) * 80;
  }

  if (balance >= cost) {
    int newBalance = balance - cost;
    Serial.println("🔄 Memproses pembayaran & histori keluar di Supabase...");
    
    // Update Saldo User
    String userPayload = "{\"balance\":" + String(newBalance) + "}";
    execPATCH("/rest/v1/users?id=eq." + userId, userPayload);

    // Update History Parkir
    String timeOutStr = getISO8601Time();
    String histPayload = "{\"time_out\":\"" + timeOutStr + "\",\"duration_minutes\":" + String(duration_minutes) + ",\"total_fee\":" + String(cost) + ",\"status\":\"COMPLETED\"}";
    execPATCH("/rest/v1/parking_history?id=eq." + histId, histPayload);

    Serial.printf("✅ Exit Sukses. UID: %s, Durasi: %d mnt, Biaya: Rp %d, Sisa Saldo: Rp %d\n", uid.c_str(), duration_minutes, cost, newBalance);
    openGate(g, now);
  } else {
    Serial.printf("❌ Saldo tidak cukup untuk Exit! UID: %s, Biaya: Rp %d, Saldo: Rp %d\n", uid.c_str(), cost, balance);
  }
}

void setup() {
  Serial.begin(115200);
  httpMutex = xSemaphoreCreateMutex();
  
  wm.setConfigPortalBlocking(true);
  wm.autoConnect("AutoPics_Gate_AP");

  // Sinkronisasi Waktu
  configTime(0, 0, "id.pool.ntp.org", "pool.ntp.org", "time.nist.gov");
  Serial.print("NTP Sync...");
  time_t now = time(nullptr);
  while (now < 8 * 3600 * 2) { 
    delay(500); 
    Serial.print("."); 
    now = time(nullptr); 
  }
  Serial.println(" OK");
  
  pinMode(SS_MOT, OUTPUT);
  pinMode(SS_MOB, OUTPUT);
  pinMode(SS_EXIT, OUTPUT);
  digitalWrite(SS_MOT, HIGH);
  digitalWrite(SS_MOB, HIGH);
  digitalWrite(SS_EXIT, HIGH);

  SPI.begin();
  rfidMot.PCD_Init();
  delay(50);
  rfidMob.PCD_Init();
  delay(50);
  rfidExit.PCD_Init();
  delay(50);
  Serial.println("RFID Init OK");

  for (int i = 0; i < 3; i++) {
    pinMode(gts[i].trig, OUTPUT);
    pinMode(gts[i].echo, INPUT);
    gts[i].sv.attach(gts[i].servoPin);
    gts[i].sv.write(0);
  }
  
  // Initial Polling
  pollParkingSlots();
  
  // Buat Task FreeRTOS agar HTTP GET ke Supabase berjalan di background (Core 0)
  xTaskCreatePinnedToCore(
    [](void* param) {
      for(;;) {
        vTaskDelay(5000 / portTICK_PERIOD_MS); // Tunggu 5 detik
        pollParkingSlots();
      }
    },
    "PollTask", 8192, NULL, 1, NULL, 0
  );

  Serial.println(">>> SUPABASE GATE SYSTEM READY <<<");
}

void loop() {
  wm.process();
  unsigned long now = millis();
  static unsigned long lastDbPrint = 0;

  if (now - lastDbPrint >= 1000) {
    lastDbPrint = now;
    long dMot = getD(gts[0].trig, gts[0].echo);
    long dMob = getD(gts[1].trig, gts[1].echo);
    long dExt = getD(gts[2].trig, gts[2].echo);
    Serial.printf("🔍 Heap: %d B | Kosong(Mtr:%d Mob:%d) | Jarak: %ld,%ld,%ld cm\n", 
                  ESP.getFreeHeap(), availSlotsMotor, availSlotsMobil, dMot, dMob, dExt);
  }

  if (now - lastScan >= SCAN_INTERVAL) {
    lastScan = now;
    Gate &g  = gts[currentIdx];
    long dist = getD(g.trig, g.echo);

    bool rfidPresent = false;
    String detectedUid = "";
    if (g.rfid != nullptr && g.rfid->PICC_IsNewCardPresent() && g.rfid->PICC_ReadCardSerial()) {
      detectedUid = getUID(g.rfid);
      g.rfid->PICC_HaltA();
      rfidPresent = true;
      Serial.printf("📡 Kartu di %s! UID: %s\n", g.name, detectedUid.c_str());
    }

    if (!g.isOpen) {
      if (rfidPresent) {
        if (g.isExit) {
          processExit(g, detectedUid, now);
        } else {
          bool isMotorGate = (strcmp(g.name, "MOTOR_IN") == 0);
          processEntrance(g, detectedUid, now, isMotorGate);
        }
      }
    } else {
      if (abs(dist - g.defaultDist) > 1 && dist != 999) {
        g.hasEntered = true;
        g.stableEmptyTime = 0;
      } else {
        if (g.stableEmptyTime == 0) g.stableEmptyTime = now;
        
        if (g.hasEntered && (now - g.stableEmptyTime >= 1500)) {
          Serial.printf("🔒 %s: CLOSE (Lewat)\n", g.name);
          g.sv.write(0);
          g.isOpen = false;
        }
        else if (!g.hasEntered && (now - g.lastOpen >= GATE_HOLD_TIME)) {
          Serial.printf("🔒 %s: CLOSE (Timeout)\n", g.name);
          g.sv.write(0);
          g.isOpen = false;
        }
      }
    }
    
    currentIdx = (currentIdx + 1) % 3;
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "reswi") {
      wm.resetSettings();
      delay(1000);
      ESP.restart();
    }
  }

  // --- FITUR RESET WIFI VIA TOMBOL BOOT FISIK ---
  // Tombol BOOT bawaan ESP32 terhubung ke GPIO 0
  static unsigned long btnPressTime = 0;
  if (digitalRead(0) == LOW) {
    if (btnPressTime == 0) btnPressTime = millis();
    else if (millis() - btnPressTime > 3000) {
      Serial.println("\n[!] Tombol BOOT ditekan 3 detik. Mereset WiFi...");
      wm.resetSettings();
      delay(1000);
      ESP.restart();
    }
  } else {
    btnPressTime = 0;
  }
}