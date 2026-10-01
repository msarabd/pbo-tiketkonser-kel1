
# Panduan Kolaborasi Proyek KonserKU (TiketWee)

Panduan operasional ini khusus dirancang untuk kelompok kerja Anda di mana file database SQLite (`db.sqlite3`) disertakan di dalam repositori Git agar seluruh anggota tim dapat langsung menggunakan data konser, venue, dan akun yang sama tanpa harus mengisi ulang dari awal.

## Prasyarat Sistem

Sebelum menjalankan proyek ini di perangkat lokal Anda, pastikan telah terpasang:

* Python 3.10 atau versi terbaru
* Git
* pip (Python Package Installer)

---

## Langkah-Langkah Awal untuk Perangkat Lain (Git Clone)

Ikuti urutan eksekusi di bawah ini dengan presisi agar sistem berjalan lancar di komputer lokal Anda:

1. **Kloning Repositori**
   Buka terminal atau *Command Prompt* di komputer Anda, lalu jalankan perintah:
   `git clone `
   `cd pbo_tiketkonser_kel1`
2. **Buat dan Aktifkan Virtual Environment**
   Sangat dilarang menginstal dependensi langsung ke sistem utama Python komputer Anda.
   *Pengguna Windows:*
   `python -m venv venv`
   `.\venv\Scripts\activate`

   *Pengguna Mac/Linux:*
   `python3 -m venv venv`
   `source venv/bin/activate`
3. **Instalasi Modul Dependensi**
   Instal kerangka kerja Django dan pustaka pengolah gambar (*Pillow*) yang dibutuhkan sistem:
   `pip install django pillow`
4. **Lewati Proses Migrasi Database**
   Karena file database (`db.sqlite3`) sudah disertakan di dalam repositori ini, Anda **tidak perlu** menjalankan perintah `makemigrations` maupun `migrate`. Seluruh struktur tabel dan data bersama sudah langsung tersedia di dalam folder proyek.
5. **Jalankan Server Lokal**
   Nyalakan server pengembangan Django dengan perintah:
   `python manage.py runserver`
6. **Akses Aplikasi**
   Buka *browser* Anda dan kunjungi tautan berikut:
   **http://127.0.0.1:8000/tickets/**

   Seluruh data konser, kategori tiket, venue, dan akun yang telah dibuat oleh tim akan langsung muncul dan siap digunakan secara seragam di perangkat lokal Anda.

---

## Catatan Penting untuk Kerja Kelompok

* Karena file database SQLite dibagi bersama melalui Git, **hindari melakukan perubahan data secara bersamaan** (seperti menambah event atau mengubah data lewat panel admin) tanpa koordinasi.
* Jika rekan tim Anda melakukan *push* perubahan data database, lakukan `git pull` terlebih dahulu sebelum Anda mulai bekerja di perangkat Anda untuk menghindari konflik data.
