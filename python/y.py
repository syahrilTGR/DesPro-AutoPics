"""
AUTOPICS - GPU-Accelerated Slot Detector + ESP32-CAM
=====================================================
Sumber kamera : ESP32-CAM via HTTP (hotspot)
Deteksi GPU   : PyTorch CUDA (fallback CPU)

Cara pakai:
  1. Ganti ESP32_IP sesuai IP kamu
  2. Jalankan: python autopics_esp32cam.py
  3. Tekan [G] + drag untuk gambar slot
  4. Pastikan semua slot kosong → tekan [C] kalibrasi
  5. Deteksi otomatis berjalan realtime!

Install:
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
  pip install opencv-python numpy firebase-admin
"""

import cv2
import numpy as np
import json, os, time, threading, socket
import urllib.request
from collections import deque
from datetime import datetime

# ── Manajemen IP Fallback ──────────────────
LAST_IP_FILE = "last_ip.txt"

def get_fallback_ip():
    if os.path.exists(LAST_IP_FILE):
        with open(LAST_IP_FILE, "r") as f:
            return f.read().strip()
    return "10.128.17.172" # Hard fallback

def save_last_ip(ip):
    with open(LAST_IP_FILE, "w") as f:
        f.write(ip)

# ╔══════════════════════════════════════════════╗
# ║        AUTO-DISCOVERY ESP32-CAM             ║
# ║  Cari IP otomatis via UDP Beacon & mDNS     ║
# ╚══════════════════════════════════════════════╝
def discover_esp_ip(fallback_ip="10.128.17.172",
                    mdns_hostname="autopics-cam.local",
                    udp_port=4210,
                    udp_timeout=3.5):
    """
    Cari IP ESP32-CAM secara otomatis:
      1. UDP Beacon  — ESP32 broadcast paket ke jaringan
      2. mDNS        — resolusi nama .local
      3. Fallback    — pakai IP manual jika keduanya gagal
    """
    # ── Tahap 1: UDP Beacon ───────────────────
    print("🔍 [1/3] Mencari ESP32-CAM via UDP Beacon...")
    try:
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp.settimeout(udp_timeout)
        udp.bind(('', udp_port))
        data, addr = udp.recvfrom(1024)
        udp.close()
        if b"AUTOPICS" in data:
            ip = addr[0]
            print(f"✅ ESP32 ditemukan via UDP → {ip}")
            save_last_ip(ip)
            return ip
    except Exception as e:
        print(f"   UDP timeout: {e}")

    # ── Tahap 2: mDNS (.local) ────────────────
    print(f"🔍 [2/3] Mencoba mDNS ({mdns_hostname})...")
    try:
        ip = socket.gethostbyname(mdns_hostname)
        print(f"✅ mDNS OK → {ip}")
        save_last_ip(ip)
        return ip
    except Exception:
        print(f"   mDNS gagal")

    # ── Tahap 3: Fallback IP Terakhir ─────────
    ip = get_fallback_ip()
    print(f"⚠️  [3/3] Pakai IP terakhir → {ip}")
    return ip

# ── ESP32-CAM ─────────────────────────────────
ESP32_IP    = discover_esp_ip()
STREAM_URL  = f"http://{ESP32_IP}/cam-lo.jpg"
SNAP_URL    = f"http://{ESP32_IP}/cam-lo.jpg"

# ── Firebase ───────────────────────────────────
FIREBASE_CRED_PATH   = "key.json"  # ← file JSON dari Firebase Console
FIREBASE_DB_URL      = "https://parking-600df-default-rtdb.asia-southeast1.firebasedatabase.app/"
FIREBASE_PATH_SLOTS  = "parkir/slots"
FIREBASE_PATH_SUMMARY= "parkir/ringkasan"
FIREBASE_INTERVAL    = 2.0

# ══════════════════════════════════════════════
#  GPU SETUP
# ══════════════════════════════════════════════
try:
    import torch
    import torch.nn.functional as F
    if torch.cuda.is_available():
        DEVICE   = torch.device("cuda")
        USE_GPU  = True
        GPU_NAME = torch.cuda.get_device_name(0)
        torch.backends.cudnn.benchmark = True
        print(f"🚀 GPU aktif  : {GPU_NAME}")
    else:
        DEVICE  = torch.device("cpu")
        USE_GPU = False
        GPU_NAME = "CPU"
        print("⚠️  GPU tidak tersedia → pakai CPU")
except ImportError:
    USE_GPU  = False
    DEVICE   = None
    GPU_NAME = "CPU"
    print("⚠️  PyTorch tidak terinstall → pakai CPU OpenCV")

# ══════════════════════════════════════════════
#  KONFIGURASI DETEKTOR
# ══════════════════════════════════════════════
SLOT_FILE        = "slots_esp32.json"
REF_FILE         = "reference_esp32.npz"
WEIGHT_HIST      = 0.40
WEIGHT_EDGE      = 0.30
WEIGHT_MSE       = 0.30
THRESHOLD_SCORE  = 0.50
SMOOTH_FRAMES    = 15
ROI_SIZE         = (64, 64)

C_KOSONG  = (50, 210, 50)
C_TERISI  = (40, 40, 220)
C_UNKNOWN = (0, 180, 220)
C_GAMBAR  = (0, 210, 255)

# ══════════════════════════════════════════════
#  STATE GLOBAL
# ══════════════════════════════════════════════
slots         = []
ref_tensors   = {}
score_history = {}
menggambar    = False
titik_awal    = (0, 0)
kotak_tmp     = None
mode          = "normal"
terkalibrasi  = False
show_debug    = False

# State tambahan untuk pemilihan tipe kendaraan
sedang_pilih_tipe = False
last_rect         = None

# ╔══════════════════════════════════════════════╗
# ║              FIREBASE SETUP                  ║
# ╚══════════════════════════════════════════════╝
firebase_ok = False
db_ref      = None

def init_firebase():
    global firebase_ok, db_ref
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        if not os.path.exists(FIREBASE_CRED_PATH):
            print(f"⚠️  File kredensial tidak ditemukan: {FIREBASE_CRED_PATH}")
            return False
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        db_ref      = db.reference("/")
        firebase_ok = True
        print(f"🔥 Firebase terhubung → {FIREBASE_DB_URL}")
        return True
    except ImportError:
        print("⚠️  firebase-admin belum diinstall → pip install firebase-admin")
        return False
    except Exception as e:
        print(f"⚠️  Firebase gagal: {e}")
        return False

# ╔══════════════════════════════════════════════╗
# ║         FIREBASE SENDER (BACKGROUND)         ║
# ╚══════════════════════════════════════════════╝
class FirebaseSender:
    def __init__(self):
        self._queue      = {}
        self._lock       = threading.Lock()
        self._last_sent  = {}
        self._last_time  = 0
        self.running     = True
        self.kirim_count = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def update(self, hasil: dict, total_slot: int):
        if not firebase_ok: return
        with self._lock:
            for sid, (terisi, skor) in hasil.items():
                if self._last_sent.get(sid) != terisi:
                    # Cari data tipe kendaraan dari daftar slot global
                    slot = next((s for s in slots if s["id"] == sid), None)
                    if not slot: continue
                    
                    self._queue[sid] = {
                        "terisi"    : terisi,
                        "tipe"      : slot.get("tipe", "mobil"), # default mobil
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

    def _loop(self):
        while self.running:
            time.sleep(0.2)
            now = time.time()
            if now - self._last_time < FIREBASE_INTERVAL: continue
            with self._lock:
                if not self._queue: continue
                batch = dict(self._queue)
                self._queue.clear()
            self._kirim(batch)
            self._last_time = now

    def _kirim(self, batch: dict):
        try:
            from firebase_admin import db
            for sid, data in batch.items():
                tipe = data.pop("tipe")
                # Kirim ke folder sub-jenis: parkir/slots/mobil/A1
                db.reference(f"{FIREBASE_PATH_SLOTS}/{tipe}/{sid}").set(data)
                self._last_sent[sid] = (data["terisi"], tipe)
                self.kirim_count += 1
            
            # Hitung ringkasan terpisah (mobil vs motor)
            summary_data = {
                "mobil": {"total": 0, "terisi": 0, "kosong": 0, "persen": 0},
                "motor": {"total": 0, "terisi": 0, "kosong": 0, "persen": 0}
            }

            for s in slots:
                sid, tipe = s["id"], s.get("tipe", "mobil")
                if sid in self._last_sent:
                    terisi, _ = self._last_sent[sid]
                    summary_data[tipe]["total"] += 1
                    if terisi: summary_data[tipe]["terisi"] += 1
                    else: summary_data[tipe]["kosong"] += 1

            for tipe in ["mobil", "motor"]:
                d = summary_data[tipe]
                if d["total"] > 0:
                    d["persen"] = round(d["terisi"] / d["total"] * 100, 1)
                    db.reference(f"{FIREBASE_PATH_SUMMARY}/{tipe}").set({
                        "total"      : d["total"],
                        "terisi"     : d["terisi"],
                        "kosong"     : d["kosong"],
                        "persen_terisi": d["persen"],
                        "updated_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })

            print(f"🔥 Firebase update ({len(batch)} slot updated)")

        except Exception as e:
            print(f"⚠️  Firebase error: {e}")

    def reset_slot(self, slot_id: str):
        if not firebase_ok: return
        try:
            from firebase_admin import db
            # Cari tipe dulu sebelum hapus
            slot = next((s for s in slots if s["id"] == slot_id), None)
            if slot:
                tipe = slot.get("tipe", "mobil")
                db.reference(f"{FIREBASE_PATH_SLOTS}/{tipe}/{slot_id}").delete()
            self._last_sent.pop(slot_id, None)
        except Exception: pass

    def stop(self):
        self.running = False

# ╔══════════════════════════════════════════════╗
# ║          STREAM READER (THREAD)              ║
# ╚══════════════════════════════════════════════╝
class StreamReader:
    def __init__(self, url):
        self.url       = url
        self._frame    = None
        self._lock     = threading.Lock()
        self.running   = False
        self.connected = False
        import requests
        self.session   = requests.Session() # Persistent Connection (Keep-Alive)
        self.fps       = 0.0
        self._fps_hist = deque(maxlen=10)

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        while self.running:
            t_start = time.time() # Titik awal sinkronisasi 5 FPS
            try:
                # Ambil gambar dengan timeout lebih lega (5 detik)
                resp = self.session.get(self.url, timeout=5)
                if resp.status_code == 200:
                    img_np = np.frombuffer(resp.content, dtype=np.uint8)
                    frame  = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Update FPS history
                        self._fps_hist.append(1.0 / max(time.time() - t_start, 0.001))
                        self.fps = float(np.mean(self._fps_hist))

                        if not self.connected: 
                            print(f"🔗 Terhubung (Keep-Alive): {self.url}")
                        self.connected = True
                        with self._lock: self._frame = frame
                    else:
                        # Jika decode gagal (gambar rusak), jangan langsung DC
                        pass
                else:
                    self.connected = False
            except Exception as e:
                if self.connected:
                    print(f"❌ Koneksi terputus: {e}")
                self.connected = False
                time.sleep(0.5)

            # SINKRONISASI 5 FPS (200ms per frame)
            # Tidur sisa waktu dari total 0.2 detik
            t_elapsed = time.time() - t_start
            t_sleep   = max(0, 0.2 - t_elapsed)
            if t_sleep > 0:
                time.sleep(t_sleep)

    def update_url(self, new_url):
        with self._lock:
            if self.url != new_url:
                print(f"🔄 Berpindah ke: {new_url}")
                self.url = new_url
                self.connected = False

    def read(self):
        with self._lock:
            if self._frame is not None: return True, self._frame.copy()
        return False, None

    def stop(self):
        self.running = False

# ══════════════════════════════════════════════
#  SIMPAN / LOAD
# ══════════════════════════════════════════════
def simpan_slots():
    with open(SLOT_FILE, "w") as f:
        json.dump(slots, f, indent=2)
    print(f"💾 {len(slots)} slot disimpan")

def load_slots():
    global slots
    if os.path.exists(SLOT_FILE):
        with open(SLOT_FILE) as f:
            slots = json.load(f)
        for s in slots:
            if s["id"] not in score_history:
                score_history[s["id"]] = deque(maxlen=SMOOTH_FRAMES)

def simpan_referensi():
    save = {}
    for sid, d in ref_tensors.items():
        save[f"{sid}_gray"]         = d["gray"].cpu().numpy()
        save[f"{sid}_hist"]         = d["hist"].cpu().numpy()
        save[f"{sid}_edge_density"] = np.array([d["edge_density"]])
    np.savez_compressed(REF_FILE, **save)

def load_referensi():
    global ref_tensors, terkalibrasi
    if not os.path.exists(REF_FILE) and not os.path.exists(REF_FILE + ".npz"): return False
    target = REF_FILE if os.path.exists(REF_FILE) else REF_FILE + ".npz"
    d = np.load(target)
    sids = {k.rsplit("_", 1)[0] for k in d.files}
    for sid in sids:
        try:
            ref_tensors[sid] = {
                "gray":         _to_tensor(d[f"{sid}_gray"]),
                "hist":         _to_tensor(d[f"{sid}_hist"]),
                "edge_density": float(d[f"{sid}_edge_density"][0]),
            }
        except Exception: pass
    terkalibrasi = len(ref_tensors) > 0
    return terkalibrasi

def nama_baru():
    idx   = len(slots) + 1
    huruf = chr(ord('A') + (idx - 1) // 9)
    angka = ((idx - 1) % 9) + 1
    return f"{huruf}{angka}"

# ══════════════════════════════════════════════
#  HELPER GPU
# ══════════════════════════════════════════════
def _to_tensor(arr):
    t = torch.from_numpy(arr.astype(np.float32))
    return t.to(DEVICE) if USE_GPU else t

def _roi(frame, slot):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = max(0, slot["x1"]), max(0, slot["y1"]), min(w, slot["x2"]), min(h, slot["y2"])
    if x2 <= x1 or y2 <= y1: return None
    return cv2.resize(frame[y1:y2, x1:x2], ROI_SIZE)

def hist_gpu(gray_tensor):
    flat = gray_tensor.flatten() / 255.0
    hist = torch.histc(flat, bins=64, min=0, max=1)
    return hist / (hist.sum() + 1e-8)

def edge_density_gpu(gray_tensor):
    img = gray_tensor.unsqueeze(0).unsqueeze(0) / 255.0
    sx = torch.tensor([[-1,0,1],[-2,0,2],[-1,0,1]], dtype=torch.float32, device=DEVICE).view(1,1,3,3)
    sy = torch.tensor([[-1,-2,-1],[0,0,0],[1,2,1]], dtype=torch.float32, device=DEVICE).view(1,1,3,3)
    mag = torch.sqrt(F.conv2d(img, sx, padding=1)**2 + F.conv2d(img, sy, padding=1)**2).squeeze()
    return (mag > 0.15).float().mean().item()

def preprocess_frame_gpu(frame):
    gray_np = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if USE_GPU:
        gray_gpu  = torch.from_numpy(gray_np.astype(np.float32)).to(DEVICE)
        k1d = torch.tensor([1,4,6,4,1], dtype=torch.float32, device=DEVICE)
        k2d = (k1d.unsqueeze(0) * k1d.unsqueeze(1)) / 256.0
        return F.conv2d(gray_gpu.unsqueeze(0).unsqueeze(0), k2d.view(1,1,5,5), padding=2).squeeze()
    return torch.from_numpy(cv2.GaussianBlur(gray_np, (5, 5), 0).astype(np.float32))

# ══════════════════════════════════════════════
#  KALIBRASI
# ══════════════════════════════════════════════
def kalibrasi(frame):
    global terkalibrasi
    if not slots: return
    gray_tensor = preprocess_frame_gpu(frame)
    gray_np = gray_tensor.cpu().numpy().astype(np.uint8)
    ref_tensors.clear()
    for slot in slots:
        roi = _roi(gray_np, slot)
        if roi is None: continue
        roi_t = _to_tensor(roi.astype(np.float32))
        ref_tensors[slot["id"]] = {
            "gray": roi_t,
            "hist": hist_gpu(roi_t),
            "edge_density": edge_density_gpu(roi_t),
        }
    terkalibrasi = True
    simpan_referensi()
    print(f"✅ Kalibrasi selesai ({len(ref_tensors)} slot)")

# ══════════════════════════════════════════════
#  DETEKSI
# ══════════════════════════════════════════════
def deteksi_semua_slot(gray_tensor):
    if not terkalibrasi or not slots: return {}
    hasil = {}
    gray_cpu = gray_tensor.cpu().numpy().astype(np.uint8)
    batch_curr, batch_ref, ids = [], [], []
    for slot in slots:
        sid = slot["id"]
        if sid not in ref_tensors: continue
        roi = _roi(gray_cpu, slot)
        if roi is None: continue
        batch_curr.append(_to_tensor(roi.astype(np.float32)))
        batch_ref.append(ref_tensors[sid]["gray"])
        ids.append(sid)
    if not ids: return {}
    cs, rs = torch.stack(batch_curr), torch.stack(batch_ref)
    skor_mse = torch.clamp(((cs - rs) ** 2).mean(dim=[1, 2]) / 2500.0, 0, 1)
    # Hist & Edge simplified loops
    skor_hist = torch.tensor([1.0 - torch.sqrt(hist_gpu(c) * ref_tensors[ids[i]]["hist"] + 1e-8).sum().clamp(0,1) for i,c in enumerate(batch_curr)], device=DEVICE)
    skor_edge = torch.tensor([min(1.0, max(0.0, (edge_density_gpu(c) - ref_tensors[ids[i]]["edge_density"]) / max(ref_tensors[ids[i]]["edge_density"] + 0.01, 0.05) * 0.7)) for i,c in enumerate(batch_curr)], device=DEVICE)
    skor_final = (WEIGHT_MSE*skor_mse + WEIGHT_HIST*skor_hist + WEIGHT_EDGE*skor_edge).cpu().numpy()
    for i, sid in enumerate(ids):
        score_history.setdefault(sid, deque(maxlen=SMOOTH_FRAMES)).append(float(skor_final[i]))
        sm = float(np.mean(score_history[sid]))
        hasil[sid] = (sm > THRESHOLD_SCORE, sm)
    return hasil

# ══════════════════════════════════════════════
#  RENDER
# ══════════════════════════════════════════════
def gambar_overlay(frame, hasil):
    overlay = frame.copy()
    for slot in slots:
        sid = slot["id"]
        tipe = slot.get("tipe", "mobil")
        x1, y1, x2, y2 = slot["x1"], slot["y1"], slot["x2"], slot["y2"]

        if not terkalibrasi or sid not in hasil:
            warna, label, skor = C_UNKNOWN, "?", 0.0
        else:
            terisi, skor = hasil[sid]
            warna, label = (C_TERISI if terisi else C_KOSONG), ("TERISI" if terisi else "KOSONG")

        cv2.rectangle(overlay, (x1, y1), (x2, y2), warna, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 3)

        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        # ID & Status
        cv2.putText(frame, sid, (cx - 14, cy - 8), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255,255,255), 2)
        cv2.putText(frame, label, (cx - 22, cy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)
        
        # Label Tipe Kendaraan
        label_t = "MOBIL" if tipe == "mobil" else "MOTOR"
        cv2.putText(frame, label_t, (x1 + 6, y1 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,0), 1)

        if terkalibrasi and sid in hasil:
            bw = x2 - x1 - 8
            cv2.rectangle(frame, (x1+4, y2-10), (x1+4+bw, y2-4), (60,60,60), -1)
            cv2.rectangle(frame, (x1+4, y2-10), (x1+4+int(bw*min(skor,1)), y2-4), warna, -1)
    cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
    return frame

def gambar_hud(frame, hasil, fps, fps_gpu):
    h, w = frame.shape[:2]
    total, terisi = len(slots), sum(1 for v in hasil.values() if v[0]) if hasil else 0
    kosong = total - terisi
    cv2.rectangle(frame, (0, h - 38), (w, h), (15, 15, 30), -1)
    info = f"Slot:{total}  Kosong:{kosong}  Terisi:{terisi}  FPS:{fps:.1f}  Threshold:{THRESHOLD_SCORE:.2f}"
    cv2.putText(frame, info, (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
    return frame

def gambar_sementara(frame):
    if menggambar and kotak_tmp:
        x1, y1, x2, y2 = kotak_tmp
        cv2.rectangle(frame, (x1, y1), (x2, y2), C_GAMBAR, 2)

# ══════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════
def mouse_cb(event, x, y, flags, param):
    global menggambar, titik_awal, kotak_tmp, slots
    global sedang_pilih_tipe, last_rect
    fb_sender = param
    if mode == "gambar":
        if event == cv2.EVENT_LBUTTONDOWN: menggambar, titik_awal = True, (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and menggambar: kotak_tmp = (*titik_awal, x, y)
        elif event == cv2.EVENT_LBUTTONUP and menggambar:
            menggambar = False
            x1, x2 = sorted([titik_awal[0], x]); y1, y2 = sorted([titik_awal[1], y])
            if (x2-x1)>20 and (y2-y1)>20:
                last_rect = (x1, y1, x2, y2)
                sedang_pilih_tipe = True
            kotak_tmp = None
    elif mode == "hapus" and event == cv2.EVENT_LBUTTONDOWN:
        for i, s in enumerate(slots):
            if s["x1"] <= x <= s["x2"] and s["y1"] <= y <= s["y2"]:
                if fb_sender: fb_sender.reset_slot(s["id"])
                ref_tensors.pop(s["id"], None); score_history.pop(s["id"], None); slots.pop(i); break

def main():
    global mode, menggambar, kotak_tmp, show_debug, THRESHOLD_SCORE, terkalibrasi
    global sedang_pilih_tipe, last_rect
    init_firebase()
    load_slots(); load_referensi()
    fb_sender = FirebaseSender()
    reader = StreamReader(STREAM_URL).start()
    WIN = "AUTOPICS – ESP32-CAM"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL); cv2.resizeWindow(WIN, 900, 600); cv2.setMouseCallback(WIN, mouse_cb, fb_sender)
    t_prev = time.time(); fps_hist = deque(maxlen=20); hasil = {}; frame = None
    
    print("⏳ Menunggu frame dari kamera...")
    for _ in range(100):
        ret, f = reader.read()
        if ret:
            frame = f
            break
        time.sleep(0.1)
    
    if frame is None:
        print("❌ Gagal terhubung ke kamera.")
        reader.stop(); fb_sender.stop(); return

    while True:
        ret, new_f = reader.read()
        if ret:
            frame = new_f
            dt = max(time.time() - t_prev, 1e-6); t_prev = time.time()
            fps_hist.append(1.0/dt); fps = float(np.mean(fps_hist))
            gray_t = preprocess_frame_gpu(frame)
            hasil = deteksi_semua_slot(gray_t)
            if hasil: fb_sender.update(hasil, len(slots))
        
        # Render
        display = frame.copy()
        display = gambar_overlay(display, hasil)
        gambar_sementara(display)

        # UI Pemilihan Tipe Kendaraan
        if sedang_pilih_tipe:
            h_win, w_win = display.shape[:2]
            cv2.rectangle(display, (0, h_win//2 - 40), (w_win, h_win//2 + 40), (20, 20, 20), -1)
            cv2.putText(display, "PILIH TIPE: [1] MOBIL   [2] MOTOR   [Esc] BATAL", 
                        (w_win//2 - 320, h_win//2 + 10), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (56, 189, 248), 2)

        display = gambar_hud(display, hasil, reader.fps, 0)
        cv2.imshow(WIN, display)

        key = cv2.waitKey(1) & 0xFF

        # Logika Pemilihan Tipe
        if sedang_pilih_tipe:
            if key == ord('1') or key == ord('2'):
                tipe_k = "mobil" if key == ord('1') else "motor"
                x1, y1, x2, y2 = last_rect
                nama = nama_baru()
                slots.append({"id": nama, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "tipe": tipe_k})
                score_history[nama] = deque(maxlen=SMOOTH_FRAMES)
                print(f"➕ Slot {nama} ({tipe_k}) ditambahkan")
                sedang_pilih_tipe = False; last_rect = None
            elif key == 27: # Esc
                sedang_pilih_tipe = False; last_rect = None
            continue

        if key == ord('q'): break
        elif key == ord('g'): mode = "gambar"
        elif key == ord('h'): mode = "hapus"
        elif key == ord('n'): mode = "normal"
        elif key == ord('c'):
            r,f = reader.read()
            if r: kalibrasi(f)
        elif key == ord('s'): simpan_slots(); simpan_referensi()
        
        # Hotkeys Ganti Resolusi (3, 4, 5)
        elif key == ord('3'): reader.update_url(f"http://{ESP32_IP}/cam-lo.jpg")
        elif key == ord('4'): reader.update_url(f"http://{ESP32_IP}/cam-mid.jpg")
        elif key == ord('5'): reader.update_url(f"http://{ESP32_IP}/cam-hi.jpg")

        # Batasi loop agar tidak memakan CPU (FPS Cap ~20 FPS)
        time.sleep(0.05)

    reader.stop(); fb_sender.stop(); cv2.destroyAllWindows()

if __name__ == "__main__": main()