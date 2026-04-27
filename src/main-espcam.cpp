#include <type_traits>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp32cam.h>
#include <WiFiManager.h>
#include "esp_camera.h"


WebServer server(80);

static auto loRes = esp32cam::Resolution::find(320, 240);
static auto midRes = esp32cam::Resolution::find(480, 360); // Gunakan 360p (480x360)
static auto hiRes = esp32cam::Resolution::find(800, 600);

bool stopBeacon = false;

unsigned long lastRequestTime = 0; // Catat waktu terakhir Python minta gambar

void serveJpg() {
  lastRequestTime = millis(); // Update waktu aktivitas
  stopBeacon = true; 
  auto frame = esp32cam::capture();
  if (frame == nullptr) {
    Serial.println("CAPTURE FAIL");
    server.send(503, "", "");
    return;
  }

  server.setContentLength(frame->size());
  server.send(200, "image/jpeg");
  WiFiClient client = server.client();
  frame->writeTo(client);
}

void handleJpgLo() {
  esp32cam::Camera.changeResolution(loRes);
  serveJpg();
}

void handleJpgHi() {
  esp32cam::Camera.changeResolution(hiRes);
  serveJpg();
}

void handleJpgMid() {
  esp32cam::Camera.changeResolution(midRes);
  serveJpg();
}

WiFiManager wm; 
WiFiUDP udp;
const int udpPort = 4210;

void setup() {
  setCpuFrequencyMhz(240); // CPU kencang agar encoding cepat
  btStop();                // Matikan Bluetooth (Hemat RAM & Daya)

  Serial.begin(115200);
  Serial.println("\n--- AUTOPICS ESP32-CAM (LIGHT & STABLE) ---");

  {
    using namespace esp32cam;
    Config cfg;
    cfg.setPins(pins::AiThinker);
    cfg.setResolution(loRes); // Kembali ke Lo-Res (320x240) - Paling Stabil
    cfg.setBufferCount(2); 
    cfg.setJpeg(80);         

    bool ok = Camera.begin(cfg);
    if (ok) {
      sensor_t * s = esp_camera_sensor_get();
      if (s) {
        s->set_brightness(s, 1);
        s->set_contrast(s, 1);
      }
      Serial.println("CAMERA OK");
    }
  }

  Serial.println("Starting WiFiManager...");
  wm.setConfigPortalBlocking(false); 
  if (!wm.autoConnect("AutoPics_Cam_AP")) {
    Serial.println("WiFiManager: Portal Aktif...");
  }
  
  WiFi.setSleep(false); // WiFi tetap siaga (No Lag)
  WiFi.setTxPower(WIFI_POWER_19_5dBm); // Sinyal Maksimal

  Serial.println("WiFi Connected!");
  Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());

  // Handler Root untuk test koneksi
  server.on("/", []() {
    server.send(200, "text/plain", "AUTOPICS ESP32-CAM (STABLE) READY!");
  });

  server.on("/cam-lo.jpg", handleJpgLo);
  server.on("/cam-hi.jpg", handleJpgHi);
  server.on("/cam-mid.jpg", handleJpgMid);

  server.begin();
  Serial.println("HTTP Server started");
}

unsigned long lastBeacon = 0;

void loop() {
  wm.process();
  
  if (WiFi.status() == WL_CONNECTED) {
    server.handleClient();

    // Auto-resume Beacon jika sudah 10 detik tidak ada request
    if (stopBeacon && (millis() - lastRequestTime > 10000)) {
      stopBeacon = false;
      Serial.println("📡 No activity. Resuming UDP Beacon...");
    }

    // Kirim UDP Beacon tiap 2 detik
    if (!stopBeacon && (millis() - lastBeacon > 2000)) {
      lastBeacon = millis();
      IPAddress broadcastIP = WiFi.localIP();
      broadcastIP[3] = 255; 
      udp.beginPacket(broadcastIP, udpPort);
      udp.print("AUTOPICS_ESP32_HERE");
      udp.endPacket();
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