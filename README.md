# Real-Time People Counting System

Proyek monitoring jumlah orang secara real-time di ruangan menggunakan **Raspberry Pi 4 + Webcam USB + YOLO11n + ByteTrack**.

Sistem ini mendeteksi orang melewati pintu masuk (virtual line), menghitung arah gerak (IN/OUT), menyimpan event ke database SQLite lokal, dan menyediakannya via API + Dashboard Web modern.

---

## 📂 Struktur Project

*   `app/` — Modul utama program (Camera, Detector, Tracker, Counter, Database, Config).
*   `api/` — Backend API dengan FastAPI.
*   `dashboard/` — Frontend web minimalis berbasis glassmorphism.
*   `scripts/` — Tool utility (test camera, export model ke NCNN, benchmark FPS).
*   `deploy/` — File setup installer dan systemd daemon service.
*   `models/` — Direktori penyimpanan model YOLO (`.pt` dan `.bin`/`.param` NCNN).
*   `data/` — Direktori database SQLite `counting.db`.

---

## 💻 Pengujian di Laptop (Development)

Sebelum deploy ke Raspberry Pi, kamu bisa menguji seluruh alur program langsung di laptop menggunakan webcam bawaan laptop atau file video rekaman.

### 1. Instalasi Dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Jalankan Utility Test Camera (Tahap 1, 2, 3)
Gunakan `scripts/test_camera.py` untuk menguji kamera, deteksi, tracking, dan visualisasi line crossing:

*   **Deteksi Dasar (YOLO):**
    ```bash
    python scripts/test_camera.py --mode detect --source 0
    ```
*   **Tracking ID (ByteTrack):**
    ```bash
    python scripts/test_camera.py --mode track --source 0
    ```
*   **Simulasi Counting (Virtual Line + Bounding Box):**
    ```bash
    python scripts/test_camera.py --mode count --source 0
    ```
    *(Ganti `--source 0` dengan path video `.mp4` jika ingin melakukan pengujian dari file video).*

### 3. Jalankan Program Utama + API Server (Tahap 4 & 5)
Jalankan program utama dengan display window dan API server aktif:
```bash
python app/main.py --source 0 --with-api
```
Lalu buka browser di alamat:
*   Dashboard: [http://localhost:8000/](http://localhost:8000/)
*   Dokumentasi API: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🍓 Deployment ke Raspberry Pi 4

Setelah dipastikan berjalan normal di laptop, ikuti alur ini untuk deploy ke Raspberry Pi 4.

### 1. Transfer File Code
Kirim seluruh folder project dari laptop ke Raspberry Pi via SCP:
```bash
scp -r ../accident_camera pi@<ip_raspberry_pi>:/home/pi/people-counting
```
*(Ganti `<ip_raspberry_pi>` dengan IP asli Raspberry Pi milikmu).*

### 2. Jalankan Setup Script di Raspberry Pi
Masuk ke terminal Raspberry Pi via SSH, lalu jalankan script setup:
```bash
cd /home/pi/people-counting
chmod +x deploy/install.sh
./deploy/install.sh
```
Script ini akan menginstall compiler C++, dependensi OpenCV, python venv, mendownload model, dan **mengekspor model YOLO ke format NCNN** agar inferensinya optimal di Raspberry Pi.

### 3. Jalankan Benchmarking FPS
Uji kecepatan FPS model native PyTorch `.pt` dibandingkan NCNN:
```bash
python scripts/benchmark.py
```
*(Model NCNN dengan input size 320 ditargetkan menghasilkan 5 - 10 FPS).*

### 4. Setup Auto-Start Service (Systemd)
Agar program berjalan otomatis di background ketika RPi menyala:

1.  Edit `/home/pi/people-counting/deploy/people-counter.service` jika username RPi milikmu bukan `pi`.
2.  Copy file service ke systemd directory:
    ```bash
    sudo cp deploy/people-counter.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable people-counter
    sudo systemctl start people-counter
    ```
3.  Periksa apakah service berjalan normal:
    ```bash
    sudo systemctl status people-counter
    ```
4.  Kini dashboard dapat diakses oleh laptop yang berada dalam satu jaringan Wifi via browser di URL:
    `http://<ip_raspberry_pi>:8000/`
