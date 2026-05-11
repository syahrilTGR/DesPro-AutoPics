#include <Arduino.h>

struct Ultrasonic {
  const char* name;
  int trig;
  int echo;
};

Ultrasonic sensors[3] = {
  {"MOTOR_IN (Ultrasonik 1)", 32, 33},
  {"MOBIL_IN (Ultrasonik 2)", 27, 26},
  {"EXIT_ALL (Ultrasonik 3)", 16, 17}
};

const int THRESHOLD = 2; // Ambang batas deteksi: 2 cm

long getDistance(int t, int e) {
  digitalWrite(t, LOW); delayMicroseconds(2);
  digitalWrite(t, HIGH); delayMicroseconds(10);
  digitalWrite(t, LOW);
  long dur = pulseIn(e, HIGH, 20000); // Timeout 20ms
  return (dur == 0) ? 999 : dur * 0.034 / 2;
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n--- KODE UJI COBA SENSOR ULTRASONIK (AUTOPICS) ---");
  for (int i = 0; i < 3; i++) {
    pinMode(sensors[i].trig, OUTPUT);
    pinMode(sensors[i].echo, INPUT);
    Serial.printf("✅ %s: Pin Set Sukses\n", sensors[i].name);
  }
  Serial.println(">>> Memulai pembacaan jarak realtime... <<<\n");
}

void loop() {
  Serial.println("=========================================");
  for (int i = 0; i < 3; i++) {
    long dist = getDistance(sensors[i].trig, sensors[i].echo);
    
    Serial.printf("📡 %s: %ld cm", sensors[i].name, dist);
    
    // Berikan penanda jika mendeteksi objek di bawah threshold 2 cm
    if (dist <= THRESHOLD) {
      Serial.println("  [ 🚨 OBJEK TERDETEKSI! <= 2 CM ]");
    } else {
      Serial.println("");
    }
  }
  delay(500); // Jeda pembacaan setiap setengah detik agar nyaman dibaca di layar
}
