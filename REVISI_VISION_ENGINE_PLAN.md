# Rencana Migrasi Vision Engine AutoPics
**Dari ROI Thresholding statis → ke Object Tracking dinamis (YOLOv8 + ByteTrack)**

Dokumen ini disusun untuk tim Vision Engine sebagai panduan perombakan metode deteksi slot parkir agar lebih robust terhadap perubahan cahaya dan terintegrasi dengan data pengguna (RFID).

---

## 1. Analisis Masalah Metode Saat Ini

Metode yang digunakan di `y.py` saat ini adalah **ROI Pixel Comparison** (MSE, Histogram, Edge Density) yang dibandingkan dengan gambar referensi statis (`reference_esp32.npz`).

**Kelemahan fatal:**
1. Sangat sensitif terhadap perubahan pencahayaan (pagi/siang/malam).
2. Perlu kalibrasi manual (tekan `C`) setiap kali cahaya berubah.
3. Terjadi *false positive* jika ada bayangan benda lain jatuh di kotak ROI.
4. **Isolated System**: Vision Engine hanya tahu "Slot B3 terisi", tapi sistem tidak bisa menghubungkannya dengan "Siapa" yang parkir di situ (karena tidak ada tracking).

---

## 2. Solusi: YOLOv8 + ByteTrack + IoU Mapping

Kita akan mengganti pendekatan "pixel comparison" menjadi **"Object Detection & Tracking"**. 

Konsepnya:
1. Kamera dari atas melihat kendaraan yang berhenti di depan gerbang masuk (saat tap RFID).
2. Model AI mendeteksi kendaraan tersebut sebagai objek utuh (Mobil/Motor).
3. Algoritma tracking memberikan ID unik (`track_id=1`) dan melacak pergerakan kendaraan tersebut ke dalam area parkir.
4. Ketika kendaraan berhenti di suatu slot, sistem mengecek posisi objek terhadap koordinat slot (`slots_esp32.json`) menggunakan metode **IoU (Intersection over Union)**.
5. Sistem meng-assign kendaraan tersebut ke slot tertentu secara otomatis.

### Keuntungan Utama
- **Tahan banting terhadap cahaya**: YOLO belajar bentuk kendaraan, bukan warna piksel.
- **Tidak butuh kalibrasi manual**: Cukup config kotak ROI `slots_esp32.json` sekali.
- **Integrasi RFID (Premium Feature)**: Bisa melacak *track_id* kendaraan sejak dia tap RFID di depan gerbang, hingga dia parkir di slot mana. Ini memungkinkan dashboard menampilkan "Awang parkir di slot B3".

---

## 3. Arsitektur Baru

### Opsi Kamera 1: ESP32-CAM (Sistem Saat Ini)
Kelebihan: Wireless, tidak butuh kabel panjang.
Kekurangan: Resolusi terbatas, rentan lag jika sinyal WiFi tidak stabil.

```mermaid
graph TD
    A[Kamera ESP32-CAM] -->|HTTP Stream| B(YOLOv8 Object Detection)
    B -->|Bounding Box & Class| C(ByteTrack)
    
    C -->|Track_ID_1: [x1,y1,x2,y2]| D{IoU Mapping}
    D -->|Cek slots_esp32.json| E[Match? Slot B3]
    
    E --> F[Update Supabase]
    F -->|parking_history| G[SET slot_id = 'B3'<br/>WHERE status = 'PARKED']
```

### Opsi Kamera 2: USB Webcam (Alternatif Disarankan)
Kelebihan: Resolusi jauh lebih jernih (FHD/4K), FPS sangat tinggi, nol latensi, YOLOv8 akan sangat akurat.
Kekurangan: Butuh kabel panjang dari PC Server ke atas miniatur.

```mermaid
graph TD
    A[USB Webcam] -->|Direct VideoCapture| B(YOLOv8 Object Detection)
    B -->|Bounding Box & Class| C(ByteTrack)
    
    C -->|Track_ID_1: [x1,y1,x2,y2]| D{IoU Mapping}
    D -->|Cek slots_esp32.json| E[Match? Slot B3]
    
    E --> F[Update Supabase]
    F -->|parking_history| G[SET slot_id = 'B3'<br/>WHERE status = 'PARKED']
```

---

## 4. Mekanisme IoU (Intersection over Union)

Bagaimana sistem tahu mobil jatuh di slot mana?
Setiap deteksi YOLO menghasilkan Bounding Box `[x1, y1, x2, y2]`. Kita akan menghitung irisan (overlap) antara Bounding Box kendaraan dengan kotak ROI slot parkir.

### Pseudo-code Python untuk Integrasi:

```python
def iou(box1, box2):
    """Menghitung skor irisan (0.0 - 1.0)"""
    x1 = max(box1[0], box2[0]); y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2]); y2 = min(box1[3], box2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    if inter_area == 0: return 0.0
    
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return inter_area / float(box1_area + box2_area - inter_area)

def get_assigned_slot(vehicle_bbox, slots_config, iou_threshold=0.3):
    best_slot = None
    best_iou = 0.0
    
    for slot in slots_config:
        slot_box = [slot['x1'], slot['y1'], slot['x2'], slot['y2']]
        score = iou(vehicle_bbox, slot_box)
        
        if score > best_iou and score >= iou_threshold:
            best_iou = score
            best_slot = slot['id']
            
    return best_slot
```
*Jika `best_iou` di atas threshold (misal > 30% area overlap), maka kendaraan tersebut resmi menempati slot tersebut.*

---

## 5. Rencana Migrasi (Step-by-Step)

Untuk tim Vision Engine, berikut task list yang perlu dikerjakan:

### Tahap 1: Pengumpulan Dataset & Training
- [ ] Buat script sederhana untuk *capture frame* dari kamera setiap 5 detik.
- [ ] Taruh miniatur kendaraan di berbagai slot, ubah kondisi cahaya ruangan. Kumpulkan ~200 foto.
- [ ] Label data menggunakan alat seperti CVAT / Roboflow.
- [ ] Train custom model **YOLOv8 Nano (yolov8n.pt)** menggunakan dataset tersebut.

### Tahap 2: Implementasi Tracking (ByteTrack)
- [ ] Di file `y.py` baru, ganti proses crop GPU lama dengan inference YOLOv8.
- [ ] Integrasikan `ByteTrack` (`model.track(source, tracker="bytetrack.yaml")`).
- [ ] Ekstrak `track_id` dan `bounding_box` dari hasil tracking.

### Tahap 3: IoU Slot Mapping
- [ ] Load `slots_esp32.json`.
- [ ] Tiap frame, jalankan fungsi `get_assigned_slot()` untuk tiap `track_id`.

### Tahap 4: Integrasi Database
- [ ] Tambahkan kolom `slot_id` di tabel `parking_history` Supabase.
- [ ] Perbarui `SupabaseSender` untuk melakukan `UPDATE` record parkir berdasarkan ID yang di-track.

## 6. Kamera: ESP32-CAM vs USB Webcam

### Perbandingan Kamera

| Aspek | ESP32-CAM | USB Webcam |
|-------|-----------|------------|
| **Harga** | ~Rp 150.000 | Rp 200.000 - 1 juta (untuk FHD) |
| **Resolusi** | 640×480 (max) | FHD (1920×1080) atau 4K |
| **FPS** | 5-15 FPS (tergantung resolusi) | 30-60 FPS (normal) |
| **Latensi** | 200-500 ms (WiFi) | <50 ms (USB langsung) |
| **Kualitas Gambar** | Sedang (terpengaruh cahaya, noise) | Tinggi (sensor besar, lebih detail) |
| **Pemasangan** | Mudah ( Wireless ) | Perlu kabel panjang |
| **Kompatibilitas Python** | Via `requests.get()` URL HTTP | Via `cv2.VideoCapture(0)` |

### Pilihan Disarankan untuk Development

**Untuk prototipe cepat & production-ready: USB Webcam**
- Resolusi tinggi → YOLOv8 detect lebih akurat
- Tidak ada lag WiFi → tracking lebih stabil
- Lebih mudah untuk dataset capture (screenshot langsung)

**Untuk demo/final project tanpa kabel: ESP32-CAM**
- Lebih "maker-friendly" sesuai tema IoT
- Tantangan teknis yang lebih menarik (sistem wireless)

### Kode Input Source Python (Both Options)

**Option A: ESP32-CAM (HTTP Stream)**
```python
import cv2
import numpy as np
import requests

ESP32_IP = "10.128.17.172"
STREAM_URL = f"http://{ESP32_IP}/cam-mid.jpg"

def get_frame():
    try:
        resp = requests.get(STREAM_URL, timeout=5)
        img_np = np.frombuffer(resp.content, dtype=np.uint8)
        frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print(f"Error: {e}")
        return None
```

**Option B: USB Webcam (Direct Capture)**
```python
import cv2

def get_frame():
    cap = cv2.VideoCapture(0)  # 0 = default webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None
```

### Pilihan Konfigurasi YOLOv8

**Yolov8 Nano (Cepat, akurasi sedang)**
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # 5 MB, 100+ FPS di CPU
results = model.track(source=source, tracker="bytetrack.yaml", show=False)
```

**Yolov8 Medium (Akurasi tinggi, agak lambat)**
```python
model = YOLO('yolov8m.pt')  # 19 MB, 50+ FPS di CPU
results = model.track(source=source, tracker="bytetrack.yaml", show=False)
```

---

*Note: Rencana ini bersifat modular. Hardware (ESP32 Gate) tidak perlu diubah firmware-nya karena perubahan murni di sisi Server Vision dan integrasi backend.*
