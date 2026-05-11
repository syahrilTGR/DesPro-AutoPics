#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN   4
#define SS_MOT    21 
#define SS_MOB    22 
#define SS_EXIT   25

MFRC522 rfidMot(SS_MOT, RST_PIN);
MFRC522 rfidMob(SS_MOB, RST_PIN);
MFRC522 rfidExit(SS_EXIT, RST_PIN);

MFRC522* readers[3] = {&rfidMot, &rfidMob, &rfidExit};
const char* names[3] = {"RFID MOTOR_IN", "RFID MOBIL_IN", "RFID EXIT_ALL"};
bool cardWasPresent[3] = {false, false, false};

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n--- 🧪 UJI COBA TIGA SENSOR RFID SEKALIGUS (LENGKAP) 🧪 ---");

  // 1. CRITICAL: Set SEMUA pin SS sebagai OUTPUT dan set HIGH untuk mencegah kolisi bus SPI paralel
  pinMode(SS_MOT, OUTPUT);
  pinMode(SS_MOB, OUTPUT);
  pinMode(SS_EXIT, OUTPUT);
  digitalWrite(SS_MOT, HIGH);
  digitalWrite(SS_MOB, HIGH);
  digitalWrite(SS_EXIT, HIGH);

  SPI.begin();
  
  // 2. Inisialisasi dan Cek Firmware untuk ketiga modul secara bergilir
  for (int i = 0; i < 3; i++) {
    readers[i]->PCD_Init();
    delay(150); // Jeda stabilisasi elektrikal sedikit lebih panjang untuk 3 modul
    
    Serial.printf("\n🔍 %s Firmware Check: ", names[i]);
    readers[i]->PCD_DumpVersionToSerial();
  }
  
  Serial.println("\n✅ Inisialisasi Tiga Sensor Selesai.");
  Serial.println(">>> Silakan tempelkan kartu Anda ke modul mana saja secara bergantian... <<<\n");
}

void loop() {
  for (int i = 0; i < 3; i++) {
    // Cek scan reader ke-i
    if (readers[i]->PICC_IsNewCardPresent() && readers[i]->PICC_ReadCardSerial()) {
      if (!cardWasPresent[i]) {
        cardWasPresent[i] = true;
        Serial.printf("🎯 [%s] Terbaca! | 💳 UID: ", names[i]);
        
        String uidStr = "";
        for (byte j = 0; j < readers[i]->uid.size; j++) {
          uidStr += String(readers[i]->uid.uidByte[j] < 0x10 ? "0" : "");
          uidStr += String(readers[i]->uid.uidByte[j], HEX);
        }
        uidStr.toUpperCase();
        Serial.println(uidStr);
      }
      
      // Halt / Stop Crypto agar tidak membaca berulang di reader yang sama
      readers[i]->PICC_HaltA();
      readers[i]->PCD_StopCrypto1();
    } else {
      cardWasPresent[i] = false;
    }
  }
  delay(50); // Polling ringan antar reader
}
