from ultralytics import YOLO
import cv2
import numpy as np
import json
import os
import threading
from collections import defaultdict
from datetime import datetime
import requests

# ============================================================
# 🎯 LOAD MODEL
# ============================================================
print("🚀 Loading model...")
model = YOLO('bos.pt')
print("✅ Model loaded!")

# ============================================================
# ⚙️  KONFIGURASI GLOBAL
# ============================================================
TRACKER_CONFIG   = "bytetrack.yaml"
CONFIDENCE       = 0.25
IOU              = 0.45
TRAIL_LENGTH     = 40
DEVICE           = 'cuda'
PARKING_SLOTS_FILE = "parking_slots.json"   # hasil dari parking_roi_config.py

# ============================================================
# 🅿️  LOAD ROI SLOT PARKIR
# ============================================================
def load_parking_slots(path=PARKING_SLOTS_FILE):
    """
    Load definisi slot parkir dari file JSON.
    Format: [{"id": 1, "points": [[x,y],[x,y],[x,y],[x,y]]}, ...]
    """
    if not os.path.exists(path):
        print(f"⚠️  File ROI '{path}' tidak ditemukan. Jalankan parking_roi_config.py dulu.")
        return []

    with open(path, "r") as f:
        data = json.load(f)

    slots = []
    for s in data:
        pts = np.array(s["points"], dtype=np.int32)
        slots.append({
            "id": s["id"],
            "points": pts,
            "occupied": False,
            "occupied_by": None   # track_id mobil yang menempati
        })
    print(f"✅ {len(slots)} slot parkir dimuat dari {path}")
    return slots

PARKING_SLOTS = load_parking_slots()

# ============================================================
# 🔥 SUPABASE CONFIG
# ============================================================
SUPABASE_URL = "https://hjxiczdakbcrnuntyrjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhqeGljemRha2Jjcm51bnR5cmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5NzUxNzMsImV4cCI6MjA5NjU1MTE3M30.Q5z5Eqeod6kd-sHhp-HOFW-vO8GMoJySo8Xopg_Vz_0"

def init_supabase():
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/parking_slots?limit=1", headers=headers, timeout=4)
        if resp.status_code == 200:
            print(f"🔥 Supabase terhubung (REST API Mode)")
            return True
        else:
            print(f"⚠️  Gagal terhubung ke Supabase: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Supabase REST connection failed: {e}")
        return False

# ╔══════════════════════════════════════════════╗
# ║         SUPABASE SENDER (BACKGROUND)         ║
# ╚══════════════════════════════════════════════╝
class SupabaseSender:
    def __init__(self):
        self._queue      = {}
        self._lock       = threading.Lock()
        self._event      = threading.Event()
        self._last_sent  = {}
        self.running     = True
        self.kirim_count = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def update(self, hasil: dict, total_slot: int):
        has_change = False
        with self._lock:
            for sid, terisi in hasil.items():
                last_state = self._last_sent.get(sid)
                last_terisi = last_state[0] if last_state else None

                if last_terisi != terisi:
                    self._queue[sid] = {
                        "slot_id": str(sid),
                        "status": "FULL" if terisi else "EMPTY",
                        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    }
                    has_change = True

        if has_change:
            self._event.set()

    def _loop(self):
        while self.running:
            self._event.wait(timeout=2.0)
            self._event.clear()

            with self._lock:
                if not self._queue: continue
                batch = list(self._queue.values())
                self._queue.clear()

            self._kirim(batch)

    def _kirim(self, batch: list):
        try:
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            url = f"{SUPABASE_URL}/rest/v1/parking_slots"
            resp = requests.post(url, json=batch, headers=headers, timeout=5)

            if resp.status_code in [200, 201]:
                for item in batch:
                    self._last_sent[item["slot_id"]] = (item["status"] == "FULL",)
                self.kirim_count += len(batch)
                print(f"🔥 Supabase update ({len(batch)} slot updated)")
            else:
                print(f"⚠️  Gagal update slot: HTTP {resp.status_code} - {resp.text}")

        except Exception as e:
            print(f"⚠️  Supabase REST error: {e}")

    def stop(self):
        self.running = False

# ============================================================
# 🅿️  HELPER: cek apakah titik berada dalam polygon slot
# ============================================================
def point_in_slot(point, slot_points):
    """cv2.pointPolygonTest: >0 berarti di dalam polygon."""
    result = cv2.pointPolygonTest(slot_points, point, False)
    return result >= 0

def update_parking_status(boxes, ids, classes):
    """
    Cek setiap bounding box mobil terhadap semua slot parkir.
    Update status occupied & occupied_by pada PARKING_SLOTS.
    Mengembalikan dict {slot_id: track_id atau None}
    """
    # Reset status setiap frame (supaya update real-time)
    for slot in PARKING_SLOTS:
        slot["occupied"] = False
        slot["occupied_by"] = None

    status_map = {}

    for box, track_id, cls in zip(boxes, ids, classes):
        x1, y1, x2, y2 = box
        # Gunakan centroid (titik tengah) bounding box sebagai acuan posisi mobil
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)

        for slot in PARKING_SLOTS:
            if point_in_slot((cx, cy), slot["points"]):
                slot["occupied"]    = True
                slot["occupied_by"] = int(track_id)
                status_map[slot["id"]] = int(track_id)
                break  # 1 mobil cukup cocok 1 slot

    return status_map

def draw_parking_slots(frame):
    """Gambar semua ROI slot parkir dengan warna sesuai status."""
    overlay = frame.copy()

    for slot in PARKING_SLOTS:
        pts = slot["points"]
        # Hijau transparan = kosong, Merah transparan = terisi
        color = (0, 0, 255) if slot["occupied"] else (0, 200, 0)

        cv2.fillPoly(overlay, [pts], color)
        frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))

        if slot["occupied"]:
            text = f"Slot {slot['id']}: ID-{slot['occupied_by']}"
        else:
            text = f"Slot {slot['id']}: Kosong"

        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(frame, (cx - tw//2 - 4, cy - th - 4), (cx + tw//2 + 4, cy + 6), color, -1)
        cv2.putText(frame, text, (cx - tw//2, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    return frame

# ============================================================
# 🎨 WARNA UNIK PER TRACK ID
# ============================================================
_color_cache = {}

def get_color(track_id: int):
    if track_id not in _color_cache:
        np.random.seed(track_id * 7 % 2147483647)
        _color_cache[track_id] = tuple(int(c) for c in np.random.randint(80, 255, 3))
    return _color_cache[track_id]

# ============================================================
# 🖊️  HELPER: gambar label dengan background
# ============================================================
def draw_label(frame, text, x1, y1, color):
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness  = 2
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, text, (x1 + 2, y1 - 4), font, font_scale, (255, 255, 255), thickness)

# ============================================================
# 🔄 HELPER: proses satu frame hasil tracking + cek ROI parkir
# ============================================================
def process_tracked_frame(frame, results, track_history, all_ids=None):
    annotated = frame.copy()
    active    = 0

    boxes_data = results[0].boxes

    # ── Gambar ROI parkir dulu (di belakang bounding box mobil) ──
    if boxes_data is None or boxes_data.id is None:
        # Tidak ada deteksi -> semua slot kosong
        update_parking_status([], [], [])
        annotated = draw_parking_slots(annotated)
        cv2.putText(annotated, "No vehicles detected",
                    (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return annotated, 0, {}

    boxes   = boxes_data.xyxy.cpu().numpy()
    ids     = boxes_data.id.cpu().numpy().astype(int)
    confs   = boxes_data.conf.cpu().numpy()
    classes = boxes_data.cls.cpu().numpy().astype(int)
    active  = len(ids)

    # ── Cek slot parkir berdasarkan posisi tiap mobil ──
    status_map = update_parking_status(boxes, ids, classes)

    # ── Gambar ROI parkir (dengan status terbaru) ──
    annotated = draw_parking_slots(annotated)

    for box, track_id, conf, cls in zip(boxes, ids, confs, classes):
        x1, y1, x2, y2 = map(int, box)
        label  = model.names[cls]
        color  = get_color(track_id)

        if all_ids is not None:
            all_ids.add(track_id)

        # ── Bounding box mobil ──
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        draw_label(annotated, f"ID:{track_id} {label} {conf:.2f}", x1, y1, color)

        # ── Titik tengah (centroid) — penanda acuan ROI ──
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.circle(annotated, (cx, cy), 4, (0, 255, 255), -1)

        # ── Trail ──
        history = track_history[track_id]
        history.append((cx, cy))
        if len(history) > TRAIL_LENGTH:
            history.pop(0)
        if len(history) > 1:
            pts = np.array(history, dtype=np.int32)
            cv2.polylines(annotated, [pts], isClosed=False, color=color, thickness=2)

    return annotated, active, status_map

# ============================================================
# 📷 MODE 1: GAMBAR STATIS
# ============================================================
def test_image(image_path):
    print(f"\n📸 Testing: {image_path}")
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"❌ Gambar tidak ditemukan: {image_path}")
        return

    results = model.predict(frame, conf=CONFIDENCE, iou=IOU, device=DEVICE)
    annotated = frame.copy()

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf  = box.conf[0].item()
        label = model.names[int(box.cls[0].item())]
        print(f"  🚗 {label} {conf:.2f} | [{x1},{y1},{x2},{y2}]")
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        draw_label(annotated, f"{label} {conf:.2f}", x1, y1, (0, 200, 0))

    cv2.imshow("Detection", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    cv2.imwrite("hasil_deteksi.jpg", annotated)
    print("✅ Hasil disimpan: hasil_deteksi.jpg")

# ============================================================
# 🎥 MODE 2: WEBCAM REAL-TIME + BYTETRACK + PARKING ROI
# ============================================================
def test_webcam_bytetrack(source=0):
    print(f"\n📷 Starting: {source}")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"❌ Source tidak terdeteksi: {source}")
        return

    track_history = defaultdict(list)
    all_ids       = set()
    frame_count   = 0
    prev_status   = {}   # untuk deteksi perubahan status (event log)

    init_supabase()
    sb_sender = SupabaseSender()

    import time
    fps_timer  = time.time()
    fps_display = 0.0

    print("✅ Aktif! Tekan 'Q' untuk keluar, 'R' untuk reset trail.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        results = model.track(
            frame,
            conf=CONFIDENCE,
            iou=IOU,
            tracker=TRACKER_CONFIG,
            persist=True,
            verbose=False,
            device=DEVICE
        )

        annotated, active, status_map = process_tracked_frame(frame, results, track_history, all_ids)

        # ── Log perubahan status slot (mobil masuk/keluar slot) ──
        for slot in PARKING_SLOTS:
            sid = slot["id"]
            now_id  = status_map.get(sid)
            prev_id = prev_status.get(sid)
            if now_id != prev_id:
                if now_id is not None:
                    print(f"  🅿️  Slot {sid}: Mobil ID-{now_id} PARKIR.")
                else:
                    print(f"  🅿️  Slot {sid}: Mobil ID-{prev_id} KELUAR.")
        prev_status = status_map.copy()

        # ── Update Supabase (hanya jika status berubah) ──
        supabase_status = {str(sid): (sid in status_map) for sid in [s["id"] for s in PARKING_SLOTS]}
        sb_sender.update(supabase_status, len(PARKING_SLOTS))

        # ── HUD ──
        elapsed = time.time() - fps_timer
        if elapsed >= 0.5:
            fps_display = frame_count / (time.time() - fps_timer + 1e-9)
            fps_timer   = time.time()
            frame_count = 0

        occupied_count = sum(1 for s in PARKING_SLOTS if s["occupied"])
        total_slots    = len(PARKING_SLOTS)

        cv2.putText(annotated, f"Active: {active}  |  Total IDs: {len(all_ids)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        cv2.putText(annotated, f"Parkir: {occupied_count}/{total_slots}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        cv2.putText(annotated, f"FPS: {fps_display:.1f}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

        cv2.imshow("YOLOv8 + ByteTrack + Parking ROI", annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            track_history.clear()
            print("🔄 Trail direset.")

    cap.release()
    sb_sender.stop()
    cv2.destroyAllWindows()
    print(f"\n✅ Selesai. Total kendaraan unik terdeteksi: {len(all_ids)}")

# ============================================================
# 💾 MODE 3: VIDEO FILE + BYTETRACK + PARKING ROI + SIMPAN OUTPUT
# ============================================================
def test_video_bytetrack(video_path, output_path="hasil_tracking.mp4"):
    print(f"\n🎬 Processing: {video_path}")
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"❌ Video tidak ditemukan: {video_path}")
        return

    w            = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h            = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps          = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    out = cv2.VideoWriter(output_path,
                          cv2.VideoWriter_fourcc(*'mp4v'),
                          fps, (w, h))

    track_history = defaultdict(list)
    all_ids       = set()
    frame_count   = 0

    print(f"📐 {w}x{h} | {fps:.1f} FPS | {total_frames} frame")
    print("⏳ Processing... (Ctrl+C untuk berhenti)\n")

    init_supabase()
    sb_sender = SupabaseSender()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        results = model.track(
            frame,
            conf=CONFIDENCE,
            iou=IOU,
            tracker=TRACKER_CONFIG,
            persist=True,
            verbose=False,
            device=DEVICE
        )

        annotated, active, status_map = process_tracked_frame(frame, results, track_history, all_ids)

        # ── Update Supabase ──
        supabase_status = {str(sid): (sid in status_map) for sid in [s["id"] for s in PARKING_SLOTS]}
        sb_sender.update(supabase_status, len(PARKING_SLOTS))

        occupied_count = sum(1 for s in PARKING_SLOTS if s["occupied"])
        total_slots    = len(PARKING_SLOTS)
        pct = frame_count / total_frames * 100 if total_frames > 0 else 0

        cv2.putText(annotated, f"Active: {active}  |  Parkir: {occupied_count}/{total_slots}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        cv2.putText(annotated, f"Frame: {frame_count}/{total_frames} ({pct:.1f}%)",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        out.write(annotated)

        if frame_count % 50 == 0:
            print(f"  ⏳ {frame_count}/{total_frames} ({pct:.1f}%) | Parkir: {occupied_count}/{total_slots}")

    cap.release()
    out.release()
    sb_sender.stop()
    print(f"\n✅ Video disimpan: {output_path}")
    print(f"📊 Total frame: {frame_count} | Kendaraan unik: {len(all_ids)}")

# ============================================================
# 🏁 JALANKAN
# ============================================================
if __name__ == "__main__":

    if not PARKING_SLOTS:
        print("\n⚠️  PERINGATAN: Belum ada slot parkir terdefinisi.")
        print("   Jalankan dulu: python parking_roi_config.py\n")

    # 1️⃣  Webcam real-time + ByteTrack + Parking ROI
    test_webcam_bytetrack(source=0)

    # 2️⃣  IP Camera / RTSP
    # test_webcam_bytetrack(source="rtsp://username:password@192.168.1.100/stream")

    # 3️⃣  File video → simpan hasil tracking
    # test_video_bytetrack("video_parkir.mp4", "hasil_tracking.mp4")

    # 4️⃣  Gambar statis
    # test_image("gambar_test.jpg")