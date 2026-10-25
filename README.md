# Panduan Kolaborasi & Deployment Proyek KonserKU

Panduan operasional ini dirancang untuk tim pengembang dan deployment server. Proyek ini merupakan platform pemesanan tiket konser berbasis web dengan fitur pencocokan sosial/teman konser (*swipe & match*) dan verifikasi data identitas (KTP OCR).

---

## Prasyarat Sistem

Sebelum menjalankan atau men-deploy proyek ini, pastikan sistem operasi memiliki:

* **Python 3.10+**
* **Git**
* **pip** (Python Package Installer)
* **Tesseract OCR Engine** (Wajib terpasang di level sistem operasi untuk ekstraksi NIK otomatis):
  * **Linux (Ubuntu/Debian Server):**
    ```bash
    sudo apt update
    sudo apt install tesseract-ocr -y
    ```
  * **Windows:**
    Unduh dan pasang installer Tesseract-OCR dari repositori resmi UB-Mannheim. Pastikan terpasang di lokasi standar:
    `C:\Program Files\Tesseract-OCR\tesseract.exe`

---

## 1. Setup Lokal (Development)

Ikuti langkah-langkah berikut untuk menjalankan proyek di perangkat lokal:

### 1. Kloning Repositori

```bash
git clone https://github.com/msarabd/pbo-tiketkonser-kel1.git
cd pbo_tiketkonser_kel1
```

### 2. Virtual Environment

Buat dan aktifkan virtual environment agar isolasi dependensi terjaga:

* **Windows:**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalasi Dependensi

Instal seluruh paket yang tercatat pada `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment (`.env`)

Salin template konfigurasi `.env.example` menjadi `.env`:

```bash
# Linux/macOS
cp .env.example .env

# Windows (Command Prompt)
copy .env.example .env
```

Sesuaikan isi `.env` untuk kebutuhan lokal:

```env
SECRET_KEY=kunci-rahasia-lokal-pengembangan
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 5. Sinkronisasi Database

Jalankan migrasi database SQLite:

```bash
python manage.py migrate
```

### 6. Jalankan Server Pengujian

```bash
python manage.py runserver
```

Akses melalui browser di: **http://127.0.0.1:8000/tickets/**

---

## 2. Panduan Deployment Server (Home Server / VPS Linux)

Bagian ini ditujukan bagi rekan tim atau administrator yang menangani server produksi:

### 1. Setup Awal & Instalasi Tesseract

```bash
sudo apt update && sudo apt install git python3-venv python3-pip tesseract-ocr -y
git clone https://github.com/msarabd/pbo-tiketkonser-kel1.git
cd pbo_tiketkonser_kel1
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup File `.env` Produksi

Buat file `.env` di direktori utama:

```bash
nano .env
```

Isi konfigurasi produksi:

```env
SECRET_KEY=buat-string-acak-yang-sangat-panjang-dan-unik-di-sini
DEBUG=False
ALLOWED_HOSTS=domainanda.com,ip_server_anda,127.0.0.1
```

### 3. Eksekusi File Statis & Migrasi

Kumpulkan seluruh file statis (CSS, JS, gambar visual auth) agar ditangani oleh WhiteNoise:

```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

### 4. Menjalankan Server dengan Gunicorn

Gunakan WSGI application server `gunicorn` untuk menangani trafik secara paralel:

```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

*(Direkomendasikan menggunakan reverse proxy seperti Nginx dan process manager seperti Systemd/Supervisor di depan Gunicorn).*

---

## Catatan Arsitektur & Perubahan Sistem Terkini

1. **Penghapusan Model Kursi (`Seat`)**:

   * Sistem tiket kini berorientasi kuota kategori secara atomic (`select_for_update`).
   * Alokasi kursi individu telah dihapus untuk memangkas overhead transaksi dan mengeliminasi resiko dead-lock saat perebutan tiket berlangsung.
2. **Hold Durasi Tiket Terpusat (15 Menit)**:

   * Batas masa berlaku penahanan tiket ditetapkan selama 15 menit (`HOLD_DURATION_MINUTES = 15`).
   * Pembatalan otomatis dan pengembalian stok tiket ke sistem dieksekusi secara atomic menggunakan database SQL expressions (`F('kuota') + 1`) guna mencegah race condition.
3. **Verifikasi KTP & Ekstraksi NIK (OCR)**:

   * Pengguna diwajibkan mengunggah foto KTP sebelum melakukan booking tiket.
   * Modul OCR memindai 16 digit NIK secara otomatis via asynchronous request (`api/ocr-ktp/`) dan mengisi form input profil pengguna, dengan fallback koreksi manual jika gambar buram.
4. **Integritas Database SQLite pada Git**:

   * File `db.sqlite3` telah dikecualikan (`.gitignore`) demi mencegah penimpaan data transaksi antar anggota tim. Pastikan melakukan migrasi berkala saat skema model diperbarui.
