import cv2
import json
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "parking_slots.json")

# Ganti dengan path ke gambar/frame dari kamera parkir (bisa dikosongkan jika ingin pakai webcam)
IMAGE_PATH = os.path.join(SCRIPT_DIR, "gambar_test.jpg") 

points = []
slots = []
slot_id = 1

def mouse_callback(event, x, y, flags, param):
    global points, slots, slot_id, img_copy
    
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        cv2.circle(img_copy, (x, y), 3, (0, 0, 255), -1)
        
        if len(points) > 1:
            cv2.line(img_copy, tuple(points[-2]), tuple(points[-1]), (0, 255, 0), 2)
            
        # Jika sudah 4 titik, buat 1 slot
        if len(points) == 4:
            cv2.line(img_copy, tuple(points[3]), tuple(points[0]), (0, 255, 0), 2)
            slots.append({
                "id": slot_id,
                "points": list(points)
            })
            
            # Tulis ID slot di tengah kotak
            cx = int(sum([p[0] for p in points]) / 4)
            cy = int(sum([p[1] for p in points]) / 4)
            cv2.putText(img_copy, str(slot_id), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
            
            print(f"Slot {slot_id} berhasil dibuat.")
            slot_id += 1
            points = []
            
        cv2.imshow("Draw Parking Slots", img_copy)

if __name__ == "__main__":
    # Coba load dari gambar, jika tidak ada pakai webcam
    if not os.path.exists(IMAGE_PATH):
        print(f"⚠️ Gambar statis tidak ditemukan: {IMAGE_PATH}")
        print("Mencoba mengambil 1 frame dari webcam untuk digambar...")
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            img = frame
            print("✅ Berhasil mengambil frame dari webcam.")
        else:
            print("❌ Gagal mengambil frame dari webcam. Tolong sediakan gambar_test.jpg.")
            exit(1)
    else:
        img = cv2.imread(IMAGE_PATH)
        print(f"✅ Berhasil memuat {IMAGE_PATH}")
        
    img_copy = img.copy()
    
    print("\n" + "="*50)
    print("🛠️ CARA PENGGUNAAN:")
    print("1. Klik kiri 4 kali pada sudut-sudut kotak parkir untuk membuat 1 slot.")
    print("2. Ulangi untuk membuat slot lainnya.")
    print("3. Tekan 'r' untuk MERESET/menghapus semua slot jika salah.")
    print("4. Tekan 's' atau 'q' untuk MENYIMPAN ke JSON dan KELUAR.")
    print("="*50 + "\n")

    cv2.namedWindow("Draw Parking Slots")
    cv2.setMouseCallback("Draw Parking Slots", mouse_callback)
    
    while True:
        cv2.imshow("Draw Parking Slots", img_copy)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('r'):
            img_copy = img.copy()
            points = []
            slots = []
            slot_id = 1
            print("🔄 Canvas di-reset.")
        elif key == ord('s') or key == ord('q'):
            break

    cv2.destroyAllWindows()
    
    # Simpan ke JSON jika ada slot yang dibuat
    if len(slots) > 0:
        with open(OUTPUT_JSON, "w") as f:
            json.dump(slots, f, indent=2)
        print(f"\n✅ Berhasil menyimpan {len(slots)} slot ke {OUTPUT_JSON}")
    else:
        print("\n⚠️ Tidak ada slot yang disimpan.")
