"""
╔══════════════════════════════════════════════════════════╗
║     AUTOPICS v4.0 – Firebase Realtime Integration        ║
║     ESP32-CAM + Deteksi Slot + Firebase Realtime DB      ║
╠══════════════════════════════════════════════════════════╣
║  INSTALL:                                                ║
║  pip install opencv-python numpy torch torchvision       ║
║  pip install firebase-admin                              ║
║                                                          ║
║  CARA PAKAI:                                             ║
║  1. Isi konfigurasi ESP32 & Firebase di bawah           ║
║  2. python autopics_firebase.py                          ║
║  3. [G] gambar slot → [C] kalibrasi → deteksi otomatis  ║
╚══════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
import json, os, time, threading, socket
from collections import deque
from datetime import datetime

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
        if b"AUTOPICS_ESP32_HERE" in data:
            print(f"✅ ESP32 ditemukan via UDP → {addr[0]}")
            return addr[0]
    except Exception as e:
        print(f"   UDP timeout: {e}")

    # ── Tahap 2: mDNS (.local) ────────────────
    print(f"🔍 [2/3] Mencoba mDNS ({mdns_hostname})...")
    try:
        ip = socket.gethostbyname(mdns_hostname)
        print(f"✅ mDNS OK → {ip}")
        return ip
    except Exception:
        print(f"   mDNS gagal")

    # ── Tahap 3: Fallback IP manual ───────────
    print(f"⚠️  [3/3] Pakai IP manual fallback → {fallback_ip}")
    return fallback_ip

# ╔══════════════════════════════════════════════╗
# ║      KONFIGURASI  ← WAJIB DIISI SEMUA       ║
# ╚══════════════════════════════════════════════╝

# ── ESP32-CAM ─────────────────────────────────
# Ganti FALLBACK_IP jika auto-discovery gagal semua
FALLBACK_IP = "10.128.17.172"               # ← IP cadangan manual
ESP32_IP    = discover_esp_ip(fallback_ip=FALLBACK_IP)
STREAM_URL  = f"http://{ESP32_IP}/cam-hi.jpg"
SNAP_URL    = f"http://{ESP32_IP}/cam-lo.jpg"

# ── Firebase ───────────────────────────────────
FIREBASE_CRED_PATH   = "key.json"  # ← file JSON dari Firebase Console
FIREBASE_DB_URL      = "https://parking-600df-default-rtdb.asia-southeast1.firebasedatabase.app/"  # ← URL database kamu
FIREBASE_PATH_SLOTS  = "parkir/slots"            # path data tiap slot
FIREBASE_PATH_SUMMARY= "parkir/ringkasan"        # path ringkasan total

# Interval kirim ke Firebase (detik) — jangan terlalu cepat (boros kuota)
FIREBASE_INTERVAL    = 2.0   # kirim setiap 2 detik jika ada perubahan

# ── Detektor ──────────────────────────────────
SLOT_FILE        = "slots.json"
REF_FILE         = "referensi.npz"
WEIGHT_MSE       = 0.35
WEIGHT_HIST      = 0.40
WEIGHT_EDGE      = 0.25
THRESHOLD_SCORE  = 0.45
SMOOTH_FRAMES    = 18
KALIB_FRAMES     = 10
ROI_SIZE         = (72, 72)

# ── Warna UI ──────────────────────────────────
C_KOSONG  = (34, 197, 94)
C_TERISI  = (239, 68, 68)
C_UNKNOWN = (234, 179, 8)
C_GAMBAR  = (56, 189, 248)

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
            print("   Firebase dinonaktifkan. Deteksi tetap berjalan lokal.")
            return False

        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        db_ref      = db.reference("/")
        firebase_ok = True
        print(f"🔥 Firebase terhubung → {FIREBASE_DB_URL}")
        return True

    except ImportError:
        print("⚠️  firebase-admin belum diinstall → pip install firebase-admin")
        print("   Deteksi tetap berjalan, Firebase dinonaktifkan.")
        return False
    except Exception as e:
        print(f"⚠️  Firebase gagal: {e}")
        print("   Pastikan FIREBASE_DB_URL dan file JSON sudah benar.")
        return False

# ╔══════════════════════════════════════════════╗
# ║         FIREBASE SENDER (BACKGROUND)         ║
# ╚══════════════════════════════════════════════╝
class FirebaseSender:
    """
    Kirim data ke Firebase di thread terpisah agar tidak block UI.
    Hanya kirim jika ada perubahan status slot.
    """

    def __init__(self):
        self._queue      = {}         # {slot_id: data} antrian kirim
        self._lock       = threading.Lock()
        self._last_sent  = {}         # {slot_id: status_terakhir}
        self._last_time  = 0
        self.running     = True
        self.kirim_count = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def update(self, hasil: dict, total_slot: int):
        """Masukkan hasil deteksi ke antrian jika ada perubahan."""
        if not firebase_ok:
            return

        with self._lock:
            for sid, (terisi, skor) in hasil.items():
                # Hanya antri jika status berubah
                status_baru = "TERISI" if terisi else "KOSONG"
                if self._last_sent.get(sid) != status_baru:
                    self._queue[sid] = {
                        "status"    : status_baru,
                        "terisi"    : terisi,
                        "skor"      : round(skor, 3),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

    def _loop(self):
        """Thread pengiriman ke Firebase."""
        while self.running:
            time.sleep(0.2)
            now = time.time()

            # Kirim setiap FIREBASE_INTERVAL detik
            if now - self._last_time < FIREBASE_INTERVAL:
                continue

            with self._lock:
                if not self._queue:
                    continue
                batch    = dict(self._queue)
                self._queue.clear()

            self._kirim(batch)
            self._last_time = now

    def _kirim(self, batch: dict):
        """Kirim batch update ke Firebase Realtime Database."""
        try:
            from firebase_admin import db

            # Kirim tiap slot
            for sid, data in batch.items():
                db.reference(f"{FIREBASE_PATH_SLOTS}/{sid}").set(data)
                self._last_sent[sid] = data["status"]
                self.kirim_count += 1

            # Update ringkasan
            semua_slot   = list(self._last_sent.values())
            jml_terisi   = sum(1 for v in semua_slot if v == "TERISI")
            jml_kosong   = len(semua_slot) - jml_terisi

            db.reference(FIREBASE_PATH_SUMMARY).set({
                "total"      : len(semua_slot),
                "terisi"     : jml_terisi,
                "kosong"     : jml_kosong,
                "persen_terisi": round(jml_terisi / max(len(semua_slot), 1) * 100, 1),
                "updated_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

            perubahan = ", ".join([f"{k}={v['status']}" for k, v in batch.items()])
            print(f"🔥 Firebase ← {perubahan}  (total kirim: {self.kirim_count})")

        except Exception as e:
            print(f"⚠️  Firebase error: {e}")

    def reset_slot(self, slot_id: str):
        """Hapus slot dari Firebase saat slot dihapus dari UI."""
        if not firebase_ok:
            return
        try:
            from firebase_admin import db
            db.reference(f"{FIREBASE_PATH_SLOTS}/{slot_id}").delete()
            self._last_sent.pop(slot_id, None)
            print(f"🔥 Firebase: slot '{slot_id}' dihapus")
        except Exception as e:
            print(f"⚠️  Gagal hapus slot Firebase: {e}")

    def stop(self):
        self.running = False

# ╔══════════════════════════════════════════════╗
# ║              GPU / CPU SETUP                 ║
# ╚══════════════════════════════════════════════╝
try:
    import torch
    import torch.nn.functional as F
    if torch.cuda.is_available():
        DEVICE   = torch.device("cuda")
        USE_GPU  = True
        GPU_NAME = torch.cuda.get_device_name(0)
        torch.backends.cudnn.benchmark = True
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"🚀 GPU  : {GPU_NAME}  ({vram:.1f} GB)")
    else:
        DEVICE   = torch.device("cpu")
        USE_GPU  = False
        GPU_NAME = "CPU"
        print("⚠️  GPU tidak tersedia → CPU")
except ImportError:
    USE_GPU  = False
    DEVICE   = None
    GPU_NAME = "CPU"

# ╔══════════════════════════════════════════════╗
# ║              STATE APLIKASI                  ║
# ╚══════════════════════════════════════════════╝
slots         = []
ref_data      = {}
score_history = {}
menggambar    = False
titik_awal    = (0, 0)
kotak_tmp     = None
mode          = "normal"
terkalibrasi  = False
show_debug    = False
sedang_kalib  = False

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

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        while self.running:
            try:
                cap = cv2.VideoCapture(self.url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if cap.isOpened():
                    self.connected = True
                    print(f"🔗 Stream: {self.url}")
                while self.running and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    with self._lock:
                        self._frame = frame
                cap.release()
                self.connected = False
            except Exception:
                self.connected = False
            if self.running:
                print("🔄 Reconnecting...")
                time.sleep(1.5)

    def read(self):
        with self._lock:
            if self._frame is not None:
                return True, self._frame.copy()
        return False, None

    def stop(self):
        self.running = False

# ╔══════════════════════════════════════════════╗
# ║            SIMPAN / LOAD                     ║
# ╚══════════════════════════════════════════════╝
def simpan_slots():
    with open(SLOT_FILE, "w") as f:
        json.dump(slots, f, indent=2)
    print(f"💾 {len(slots)} slot → {SLOT_FILE}")

def load_slots():
    global slots
    if os.path.exists(SLOT_FILE):
        with open(SLOT_FILE) as f:
            slots = json.load(f)
        for s in slots:
            score_history.setdefault(s["id"], deque(maxlen=SMOOTH_FRAMES))
        print(f"📂 {len(slots)} slot dimuat")

def simpan_referensi():
    bundle = {}
    for sid, d in ref_data.items():
        bundle[f"{sid}__gray"] = d["gray"].cpu().numpy()
        bundle[f"{sid}__hist"] = d["hist"].cpu().numpy()
        bundle[f"{sid}__edge"] = np.array([d["edge_density"]])
    np.savez_compressed(REF_FILE, **bundle)
    print(f"💾 Referensi {len(ref_data)} slot → {REF_FILE}.npz")

def load_referensi():
    global ref_data, terkalibrasi
    path = REF_FILE if os.path.exists(REF_FILE) else REF_FILE + ".npz"
    if not os.path.exists(path):
        return False
    try:
        d    = np.load(path)
        sids = {k.rsplit("__", 1)[0] for k in d.files if "__" in k}
        for sid in sids:
            ref_data[sid] = {
                "gray":         _to_tensor(d[f"{sid}__gray"]),
                "hist":         _to_tensor(d[f"{sid}__hist"]),
                "edge_density": float(d[f"{sid}__edge"][0]),
            }
        terkalibrasi = len(ref_data) > 0
        if terkalibrasi:
            print(f"📂 Referensi {len(ref_data)} slot dimuat!")
        return terkalibrasi
    except Exception as e:
        print(f"⚠️  Gagal load ref: {e}")
        return False

def nama_baru():
    idx   = len(slots) + 1
    huruf = chr(ord('A') + (idx - 1) // 9)
    angka = ((idx - 1) % 9) + 1
    return f"{huruf}{angka}"

# ╔══════════════════════════════════════════════╗
# ║              HELPER GPU                      ║
# ╚══════════════════════════════════════════════╝
def _to_tensor(arr):
    t = torch.from_numpy(np.asarray(arr, dtype=np.float32))
    return t.to(DEVICE) if USE_GPU else t

def _crop_roi(frame_gray_np, slot):
    h, w = frame_gray_np.shape[:2]
    x1 = max(0, slot["x1"]); y1 = max(0, slot["y1"])
    x2 = min(w, slot["x2"]); y2 = min(h, slot["y2"])
    if x2 <= x1 or y2 <= y1:
        return None
    return cv2.resize(frame_gray_np[y1:y2, x1:x2], ROI_SIZE)

def preprocess(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if USE_GPU:
        g   = _to_tensor(gray)
        k1d = torch.tensor([1,4,6,4,1], dtype=torch.float32, device=DEVICE)
        k2d = (k1d.unsqueeze(0) * k1d.unsqueeze(1)) / 256.0
        return F.conv2d(g.unsqueeze(0).unsqueeze(0),
                        k2d.view(1,1,5,5), padding=2).squeeze()
    return torch.from_numpy(cv2.GaussianBlur(gray,(5,5),0).astype(np.float32))

def hist_dari_tensor(t):
    flat = t.flatten() / 255.0
    h    = torch.histc(flat, bins=64, min=0, max=1)
    return h / (h.sum() + 1e-8)

def edge_density_dari_tensor(t):
    img = t.unsqueeze(0).unsqueeze(0) / 255.0
    sx  = torch.tensor([[-1,0,1],[-2,0,2],[-1,0,1]], dtype=torch.float32, device=DEVICE).view(1,1,3,3)
    sy  = torch.tensor([[-1,-2,-1],[0,0,0],[1,2,1]],  dtype=torch.float32, device=DEVICE).view(1,1,3,3)
    mag = torch.sqrt(F.conv2d(img,sx,padding=1)**2 + F.conv2d(img,sy,padding=1)**2).squeeze()
    return (mag > 0.12).float().mean().item()

# ╔══════════════════════════════════════════════╗
# ║                KALIBRASI                     ║
# ╚══════════════════════════════════════════════╝
def kalibrasi(reader):
    global terkalibrasi, sedang_kalib
    if not slots:
        print("⚠️  Gambar slot dulu [G]!")
        return
    sedang_kalib = True
    print(f"\n🎯 Kalibrasi — mengambil {KALIB_FRAMES} frame...")

    frames_gray = []
    collected   = 0
    t_end       = time.time() + 12

    while collected < KALIB_FRAMES and time.time() < t_end:
        ret, frame = reader.read()
        if ret and frame is not None:
            frames_gray.append(preprocess(frame))
            collected += 1
            print(f"   Frame {collected}/{KALIB_FRAMES}...")
        time.sleep(0.08)

    if not frames_gray:
        print("❌ Gagal ambil frame!")
        sedang_kalib = False
        return

    gray_np_list = [f.cpu().numpy().astype(np.uint8) for f in frames_gray]
    ref_data.clear()

    for slot in slots:
        sid  = slot["id"]
        rois = [r for r in (_crop_roi(g, slot) for g in gray_np_list) if r is not None]
        if not rois:
            continue
        avg  = np.mean(np.stack(rois, 0), 0).astype(np.float32)
        roi_t = _to_tensor(avg)
        ref_data[sid] = {
            "gray":         roi_t,
            "hist":         hist_dari_tensor(roi_t),
            "edge_density": edge_density_dari_tensor(roi_t),
        }
        score_history[sid] = deque(maxlen=SMOOTH_FRAMES)

    terkalibrasi = True
    sedang_kalib = False
    simpan_referensi()
    print(f"✅ Kalibrasi selesai! {len(ref_data)} slot siap.\n")

# ╔══════════════════════════════════════════════╗
# ║          DETEKSI BATCH GPU                   ║
# ╚══════════════════════════════════════════════╝
def deteksi_semua(gray_tensor):
    if not terkalibrasi or not slots:
        return {}

    gray_np   = gray_tensor.cpu().numpy().astype(np.uint8)
    c_list, r_list, ids = [], [], []

    for slot in slots:
        sid = slot["id"]
        if sid not in ref_data:
            continue
        roi = _crop_roi(gray_np, slot)
        if roi is None:
            continue
        c_list.append(_to_tensor(roi.astype(np.float32)))
        r_list.append(ref_data[sid]["gray"])
        ids.append(sid)

    if not ids:
        return {}

    cs = torch.stack(c_list)
    rs = torch.stack(r_list)

    skor_mse  = torch.clamp(((cs-rs)**2).mean(dim=[1,2]) / 3000.0, 0, 1)

    skor_hist_l = []
    for i, t in enumerate(c_list):
        sim = torch.sqrt(hist_dari_tensor(t) * ref_data[ids[i]]["hist"] + 1e-8).sum().clamp(0,1)
        skor_hist_l.append(1.0 - sim)
    skor_hist = torch.stack(skor_hist_l)

    skor_edge_l = []
    for i, t in enumerate(c_list):
        ce = edge_density_dari_tensor(t)
        re = ref_data[ids[i]]["edge_density"]
        skor_edge_l.append(min(1.0, max(0.0, (ce-re) / max(re+0.01, 0.04) * 0.8)))
    skor_edge = torch.tensor(skor_edge_l, device=DEVICE)

    final_np = (WEIGHT_MSE*skor_mse + WEIGHT_HIST*skor_hist + WEIGHT_EDGE*skor_edge).cpu().numpy()

    hasil = {}
    for i, sid in enumerate(ids):
        s = float(final_np[i])
        score_history.setdefault(sid, deque(maxlen=SMOOTH_FRAMES)).append(s)
        sm = float(np.mean(score_history[sid]))
        hasil[sid] = (sm > THRESHOLD_SCORE, round(sm, 3))
    return hasil

# ╔══════════════════════════════════════════════╗
# ║              RENDER UI                       ║
# ╚══════════════════════════════════════════════╝
def render_slot(frame, hasil):
    overlay = frame.copy()
    for slot in slots:
        sid            = slot["id"]
        x1,y1,x2,y2   = slot["x1"],slot["y1"],slot["x2"],slot["y2"]
        cx,cy          = (x1+x2)//2, (y1+y2)//2

        if not terkalibrasi or sid not in hasil:
            warna = C_UNKNOWN; label = "?"; skor = 0.0
        else:
            terisi, skor = hasil[sid]
            warna = C_TERISI if terisi else C_KOSONG
            label = "TERISI" if terisi else "KOSONG"

        cv2.rectangle(overlay, (x1,y1), (x2,y2), warna, -1)
        cv2.rectangle(frame,   (x1,y1), (x2,y2), warna, 3)
        cv2.putText(frame, sid,   (cx-14, cy-8),  cv2.FONT_HERSHEY_DUPLEX,  0.75, (255,255,255), 2)
        cv2.putText(frame, label, (cx-28, cy+16), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255,255,255), 1)

        if terkalibrasi and sid in hasil:
            bw = (x2-x1)-8; bx = x1+4; by = y2-12
            cv2.rectangle(frame, (bx,by), (bx+bw, by+7), (40,40,40), -1)
            fill = int(bw * min(skor, 1.0))
            if fill > 0:
                cv2.rectangle(frame, (bx,by), (bx+fill, by+7), warna, -1)

        if show_debug and terkalibrasi and sid in hasil:
            cv2.putText(frame, f"{skor:.3f}", (x1+3, y1+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255,220,0), 1)

    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    return frame

def render_hud(frame, hasil, fps, stream_ok, fb_sender):
    h, w = frame.shape[:2]

    # Header
    cv2.rectangle(frame, (0,0), (w,52), (12,12,25), -1)
    cv2.putText(frame, "AUTOPICS", (12,38),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (56,189,248), 2)

    total  = len(slots)
    terisi = sum(1 for v in hasil.values() if v[0]) if hasil else 0
    kosong = total - terisi

    if sedang_kalib:
        info = "⏳ KALIBRASI — harap tunggu..."
        col  = (0, 220, 255)
    elif not terkalibrasi:
        info = "① [G] Gambar slot   ② Pastikan KOSONG   ③ [C] Kalibrasi"
        col  = (0, 200, 255)
    elif mode == "gambar":
        info = "MODE GAMBAR — drag untuk buat slot"
        col  = (56, 189, 248)
    elif mode == "hapus":
        info = "MODE HAPUS — klik slot untuk hapus"
        col  = (239, 68, 68)
    else:
        info = (f"Total:{total}   Kosong:{kosong}   Terisi:{terisi}   "
                f"Thr:{THRESHOLD_SCORE:.2f}   IP:{ESP32_IP}")
        col  = (34, 197, 94)

    cv2.putText(frame, info, (195,34), cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1)

    # Footer
    cv2.rectangle(frame, (0,h-36), (w,h), (12,12,25), -1)
    cv2.putText(frame,
        "[G]Gambar  [H]Hapus  [N]Normal  [C]Kalibrasi  [D]Debug  [+/-]Threshold  [S]Simpan  [Q]Keluar",
        (8, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (130,130,140), 1)

    # ── Badge kanan atas ─────────────────────────
    badge_x  = w - 215
    badge_h  = 26
    badge_gap = 4

    badges = [
        # (teks, warna_bg)
        ("✓ KALIBRASI OK" if terkalibrasi else "✗ BELUM KALIBRASI",
         (34,197,94) if terkalibrasi else (239,68,68)),

        (f"STREAM  FPS:{fps:.1f}" if stream_ok else "✗ STREAM PUTUS",
         (34,197,94) if stream_ok else (239,68,68)),

        (f"🔥 FIREBASE  ×{fb_sender.kirim_count}" if firebase_ok else "✗ FIREBASE OFF",
         (251,146,60) if firebase_ok else (107,114,128)),

        (f"GPU:{GPU_NAME.split()[-1]}" if USE_GPU else "CPU mode",
         (99,102,241) if USE_GPU else (107,114,128)),
    ]

    for i, (txt, col) in enumerate(badges):
        by1 = 6 + i * (badge_h + badge_gap)
        by2 = by1 + badge_h
        cv2.rectangle(frame, (badge_x, by1), (w-6, by2), col, -1)
        cv2.putText(frame, txt, (badge_x+5, by2-7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255,255,255), 1)

    return frame

def render_kotak_sementara(frame):
    if menggambar and kotak_tmp:
        x1,y1,x2,y2 = kotak_tmp
        cv2.rectangle(frame, (x1,y1), (x2,y2), C_GAMBAR, 2)
        cv2.putText(frame, f"{abs(x2-x1)}×{abs(y2-y1)}px",
                    (min(x1,x2)+4, min(y1,y2)-7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.43, C_GAMBAR, 1)

# ╔══════════════════════════════════════════════╗
# ║              MOUSE CALLBACK                  ║
# ╚══════════════════════════════════════════════╝
def mouse_cb(event, x, y, flags, param):
    global menggambar, titik_awal, kotak_tmp, slots
    fb_sender = param

    if mode == "gambar":
        if event == cv2.EVENT_LBUTTONDOWN:
            menggambar = True; titik_awal = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and menggambar:
            kotak_tmp = (*titik_awal, x, y)
        elif event == cv2.EVENT_LBUTTONUP and menggambar:
            menggambar = False
            x1,x2 = sorted([titik_awal[0],x]); y1,y2 = sorted([titik_awal[1],y])
            if (x2-x1)>25 and (y2-y1)>25:
                nama = nama_baru()
                slots.append({"id":nama,"x1":x1,"y1":y1,"x2":x2,"y2":y2})
                score_history[nama] = deque(maxlen=SMOOTH_FRAMES)
                print(f"➕ Slot '{nama}'  ({x1},{y1})→({x2},{y2})")
            kotak_tmp = None

    elif mode == "hapus":
        if event == cv2.EVENT_LBUTTONDOWN:
            for i, s in enumerate(slots):
                if s["x1"]<=x<=s["x2"] and s["y1"]<=y<=s["y2"]:
                    print(f"🗑  Slot '{s['id']}' dihapus")
                    ref_data.pop(s["id"], None)
                    score_history.pop(s["id"], None)
                    fb_sender.reset_slot(s["id"])   # hapus dari Firebase juga
                    slots.pop(i); break

# ╔══════════════════════════════════════════════╗
# ║                    MAIN                      ║
# ╚══════════════════════════════════════════════╝
def main():
    global mode, menggambar, kotak_tmp, show_debug, THRESHOLD_SCORE

    print("=" * 58)
    print("  AUTOPICS v4.0 – ESP32-CAM + Firebase Realtime")
    print(f"  ESP32-CAM : {ESP32_IP}")
    print(f"  Firebase  : {FIREBASE_DB_URL}")
    print(f"  GPU       : {'ON – ' + GPU_NAME if USE_GPU else 'OFF (CPU)'}")
    print("=" * 58)

    # Init Firebase
    init_firebase()

    load_slots()
    load_referensi()

    # Firebase sender
    fb_sender = FirebaseSender()

    # Stream reader
    print(f"\n🔄 Menghubungkan ke stream ESP32-CAM...")
    reader = StreamReader(STREAM_URL).start()

    # Tunggu frame pertama
    frame0 = None
    t0     = time.time()
    while time.time() - t0 < 8:
        ret, f = reader.read()
        if ret and f is not None:
            frame0 = f; break
        time.sleep(0.2)

    if frame0 is None:
        print(f"\n❌ Tidak bisa konek ke {STREAM_URL}")
        print(f"   Cek di browser: {STREAM_URL}")
        reader.stop(); fb_sender.stop()
        return

    print(f"✅ Stream OK! {frame0.shape[1]}×{frame0.shape[0]}")

    if firebase_ok:
        print(f"✅ Firebase OK! Data → {FIREBASE_DB_URL}/{FIREBASE_PATH_SLOTS}")

    # Window
    WIN = "AUTOPICS v4.0 – Firebase Realtime"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 960, 640)
    cv2.setMouseCallback(WIN, mouse_cb, fb_sender)

    # GPU warmup
    if USE_GPU and terkalibrasi:
        for _ in range(5):
            deteksi_semua(preprocess(frame0))
        print("✅ GPU warmup selesai\n")

    print("📋 KONTROL:")
    print("   [G] Gambar slot    [H] Hapus    [N] Normal")
    print("   [C] Kalibrasi      [S] Simpan   [Q] Keluar\n")

    fps_hist = deque(maxlen=25)
    t_prev   = time.time()
    frame    = frame0.copy()
    hasil    = {}
    gray_t   = None

    while True:
        ret, new_f = reader.read()
        stream_ok  = reader.connected

        if ret and new_f is not None:
            frame  = new_f
            t_now  = time.time()
            dt     = max(t_now - t_prev, 1e-6)
            t_prev = t_now
            fps_hist.append(1.0 / dt)
            fps    = float(np.mean(fps_hist))

            if not sedang_kalib:
                gray_t = preprocess(frame)
                hasil  = deteksi_semua(gray_t)

                # Kirim ke Firebase (hanya jika ada perubahan)
                if hasil:
                    fb_sender.update(hasil, len(slots))
        else:
            fps = 0.0

        # Render
        display = frame.copy()
        display = render_slot(display, hasil)
        render_kotak_sementara(display)
        display = render_hud(display, hasil, fps, stream_ok, fb_sender)

        if show_debug and gray_t is not None:
            g_np  = gray_t.cpu().numpy().astype(np.uint8)
            edges = cv2.Canny(g_np, 35, 110)
            hf,wf = display.shape[:2]
            pw,ph = wf//5, hf//5
            mini  = cv2.cvtColor(cv2.resize(edges,(pw,ph)), cv2.COLOR_GRAY2BGR)
            display[hf-ph-36:hf-36, wf-pw:wf] = mini

        cv2.imshow(WIN, display)
        key = cv2.waitKey(1) & 0xFF

        if   key == ord('q'): break
        elif key == ord('g'): mode="gambar"; print("✏  Mode GAMBAR")
        elif key == ord('h'): mode="hapus";  print("🗑  Mode HAPUS")
        elif key == ord('n'): mode="normal"; print("👁  Mode NORMAL")
        elif key == ord('d'):
            show_debug = not show_debug
            print(f"🔍 Debug: {'ON' if show_debug else 'OFF'}")
        elif key == ord('c'):
            if not sedang_kalib:
                threading.Thread(target=kalibrasi, args=(reader,), daemon=True).start()
        elif key == ord('s'):
            simpan_slots(); simpan_referensi()
        elif key == ord('l'):
            load_slots(); load_referensi()
        elif key in (ord('+'), ord('=')):
            THRESHOLD_SCORE = round(min(0.95, THRESHOLD_SCORE + 0.05), 2)
            print(f"⬆  Threshold: {THRESHOLD_SCORE}")
        elif key == ord('-'):
            THRESHOLD_SCORE = round(max(0.05, THRESHOLD_SCORE - 0.05), 2)
            print(f"⬇  Threshold: {THRESHOLD_SCORE}")

    reader.stop()
    fb_sender.stop()
    cv2.destroyAllWindows()

    if slots:
        if input("\n💾 Simpan? (y/n): ").strip().lower() == 'y':
            simpan_slots(); simpan_referensi()
            print("✅ Tersimpan!")

if __name__ == "__main__":
    main()