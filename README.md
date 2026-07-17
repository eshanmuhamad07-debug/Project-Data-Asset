# Website Manajemen Aset Perusahaan

Aplikasi manajemen aset berbasis **Flask + MySQL (XAMPP) + Tailwind CSS (CDN)**.
Mendukung CRUD data aset, kategorisasi 2 level, dan alur tiket request
(Pemindahan/Perbaikan) dengan multi-assign pelaksana, komentar, notifikasi,
dan log riwayat status.

## 1. Struktur Proyek

```
asset_management/
├── app.py                # Entry point + seluruh route
├── models.py              # SQLAlchemy models (9 tabel)
├── extensions.py          # instance db & login_manager
├── seed.py                 # seeder data awal
├── requirements.txt
├── static/
│   ├── js/main.js         # sidebar toggle, modal, chained dropdown, search/filter
│   └── uploads/           # foto aset/tiket/komentar disimpan di sini
└── templates/
    ├── base.html           # layout sidebar + navbar
    ├── login.html
    ├── dashboard.html
    ├── notifikasi.html
    ├── 403.html
    ├── aset/list.html
    ├── tiket/list.html
    ├── tiket/detail.html
    ├── kategori/list.html
    └── users/list.html
```

## 2. Cara Menjalankan

1. **Aktifkan XAMPP**, nyalakan modul **MySQL**.
2. Buka phpMyAdmin (`http://localhost/phpmyadmin`) lalu buat database baru bernama:
   ```
   db_manajemen_aset
   ```
   (tidak perlu membuat tabel manual — akan dibuat otomatis oleh SQLAlchemy).
3. Jika user/password MySQL Anda **bukan** `root` tanpa password, ubah baris berikut
   di `app.py`:
   ```python
   app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/db_manajemen_aset"
   ```
   menjadi `mysql+pymysql://USER:PASSWORD@localhost/db_manajemen_aset`.
4. Install dependency (disarankan pakai virtual environment):
   ```
   pip install -r requirements.txt
   ```
5. Buat tabel & isi data contoh (jalankan seeder):
   ```
   python seed.py
   ```
6. Jalankan aplikasi:
   ```
   python app.py
   ```
7. Buka browser ke `http://localhost:5000`.

## 3. Akun Contoh (setelah seeder)

| Role     | Email              | Password     |
|----------|---------------------|--------------|
| Admin    | admin@aset.com       | password123 |
| Officer  | officer1@aset.com    | password123 |
| Officer  | officer2@aset.com    | password123 |
| Teknisi  | teknisi1@aset.com    | password123 |

## 4. Catatan Desain & Penyesuaian dari Brief

Beberapa penyesuaian kecil ditambahkan agar alur bisnis di brief bisa berjalan
secara konsisten di database:

- **Tabel `tiket_aset`** (junction Tiket ↔ Aset) ditambahkan karena 1 tiket
  bisa memuat banyak aset (form "Pilih Aset checkbox/select multiple"), namun
  tabel ini tidak disebut eksplisit di daftar 6 tabel inti.
- **Tabel `notifikasi`** ditambahkan agar ikon lonceng bisa melacak status
  "sudah dibaca / belum dibaca" per user secara akurat, bukan hanya dihitung ulang.
- Total jadi **9 tabel**: `user`, `aset`, `tiket`, `tiket_aset`, `tiket_user`,
  `komentar_tiket`, `log_status`, `kategori`, `sub_kategori`, `notifikasi`.
- Role `officer/teknisi` bisa melihat tiket di mana mereka berperan sebagai
  pembuat atau pelaksana; role `admin` melihat semua tiket.

## 5. Fitur yang Sudah Diimplementasikan

- ✅ Login/logout dengan `flask-login` + hash password `werkzeug.security`
- ✅ Proteksi route berdasarkan role (`role_required` decorator)
- ✅ Sidebar collapsible mobile-friendly (Tailwind, tanpa jQuery)
- ✅ Dashboard: 3 kartu statistik + grafik Chart.js aset per kategori
- ✅ CRUD Aset (modal popup, upload foto, search & filter vanilla JS)
- ✅ Kategori 2 level + chained dropdown (fetch API `/api/sub-kategori/<id>`)
- ✅ Alur tiket lengkap: buat → pending → setujui (multi-assign) → proses →
  selesai, dengan update otomatis status/lokasi aset
- ✅ Edit pelaksana kapan saja tanpa membatalkan tiket
- ✅ Thread komentar + upload foto per komentar
- ✅ Log status (timeline riwayat perubahan)
- ✅ Notifikasi bell dengan badge counter (polling ringan tiap 30 detik)
- ✅ Kelola user (admin only)
- ✅ Seeder data awal

## 6a. Update: Perbaikan Keamanan/Bug + Fitur Export-Import (terbaru)

Daftar solusi yang sudah diimplementasikan, sesuai kritik sebelumnya:

| # | Masalah | Solusi |
|---|---|---|
| 1 | Tiket bisa diakses/diproses user yang tidak terlibat | Ditambahkan `user_terlibat_tiket()`, dicek di `tiket_detail`, `tiket_mulai`, `tiket_selesai`, `tiket_komentar` |
| 2 | Tidak ada proteksi CSRF | `Flask-WTF` `CSRFProtect` diaktifkan, token ditambahkan ke 15 form |
| 3 | Secret key & kredensial DB hardcoded | Dipindah ke environment variable (lihat di bawah) |
| 4 | `debug=True` permanen | Dikontrol via `FLASK_DEBUG` env var, default mati |
| 5 | Upload foto hanya divalidasi dari ekstensi | Ditambahkan validasi isi file pakai Pillow (`is_valid_image`) |
| 6 | Tidak ada proteksi brute-force login | `Flask-Limiter`: maksimal 8 percobaan/menit per IP |
| 7 | Status aset tidak dikembalikan saat tiket ditolak | Kolom baru `tiket_aset.status_sebelum` menyimpan status awal, dikembalikan otomatis di `tiket_tolak` |
| 8 | Hapus user bisa gagal (foreign key) | Diganti jadi nonaktifkan/aktifkan (`is_active`), bukan hapus permanen |
| 9 | Error database tampil sebagai halaman 500 polos | Global error handler untuk `IntegrityError` |
| 10 | List aset/tiket tanpa pagination | Ditambahkan pagination server-side (20 baris/halaman) |
| 11 | Tidak ada validasi minimal password | Minimal 8 karakter saat buat user |
| 12 | Role berupa string bebas (rawan typo) | Dipindah ke konstanta di `roles.py` |

**Belum diimplementasikan** (di luar cakupan perbaikan kali ini, catatan untuk ke depan):
lupa password (reset via email), automated test.

### Environment variable baru

Sebelum menjalankan aplikasi, sebaiknya set variabel berikut (opsional untuk
development lokal, **wajib** untuk production):

```bash
export SECRET_KEY="ganti-dengan-string-acak-panjang"
export DB_USER=root
export DB_PASSWORD=
export DB_HOST=localhost
export DB_NAME=db_manajemen_aset
export FLASK_DEBUG=0
```

Kalau tidak di-set, aplikasi tetap jalan dengan default yang cocok untuk XAMPP lokal (sama seperti sebelumnya).

### Migrasi database (PENTING jika sudah pernah menjalankan seeder sebelumnya)

Ada beberapa kolom baru di database:
- `user.is_active`, `tiket_aset.status_sebelum`
- `aset.lantai` — kolom ini sudah dipakai `app.py` (filter/form/export/import) tapi
  sebelumnya belum ada di model, jadi tambah/edit aset akan **error** tanpa kolom ini
- `aset.jenis_aset` — kolom baru untuk fitur "Jenis Aset" (Operasional / Pusat)

`db.create_all()` di `seed.py` **tidak** menambahkan kolom ke tabel yang
sudah ada, jadi pilih salah satu:

- **Cara mudah (hapus data lama):** drop database `db_manajemen_aset` di
  phpMyAdmin, buat ulang, lalu jalankan `python seed.py` lagi.
- **Cara jaga data lama:** jalankan SQL berikut di phpMyAdmin:
  ```sql
  ALTER TABLE `user` ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1;
  ALTER TABLE `tiket_aset` ADD COLUMN `status_sebelum` VARCHAR(20) DEFAULT NULL;
  ALTER TABLE `aset` ADD COLUMN `lantai` VARCHAR(50) DEFAULT NULL;
  ALTER TABLE `aset` ADD COLUMN `jenis_aset` VARCHAR(20) NOT NULL DEFAULT 'Operasional';
  ```

### Fitur baru: Jenis Aset (Operasional / Pusat)

Setiap aset sekarang punya **Jenis Aset**, salah satu dari:
- **Operasional** — aset yang dipakai sehari-hari di lokasi/cabang
- **Pusat** — aset yang tercatat/berlokasi di kantor pusat

Bisa dipakai untuk:
- Filter di halaman Data Aset (dropdown "Semua Jenis" di sisi kiri, sebelah filter Kategori)
- Diisi saat Tambah/Edit aset (dropdown di modal)
- Ikut ter-export/import di file Excel (kolom `jenis_aset`)

File `dummy_import_aset.xlsx` (dikirim terpisah) berisi contoh data dengan
kombinasi Operasional/Pusat untuk uji coba fitur import.

### Fitur baru: Export & Import Data Aset (Excel)

- Tombol **⬇ Export Excel** di halaman Data Aset (khusus admin) mengunduh
  semua data aset sebagai file `.xlsx` (kolom: `kode_aset`, `nama`, `gedung`,
  `ruangan`, `status_aset`, `kategori`, `sub_kategori`).
- Edit file itu di Excel — misal ubah lokasi, status, atau tambah baris baru
  di bawahnya — lalu **⬆ Import** file yang sama.
- Pencocokan berdasarkan **`kode_aset`**:
  - Kalau kode sudah ada di database → data aset itu **diperbarui**.
  - Kalau kode belum ada → dibuat sebagai **aset baru**.
- Kategori/sub-kategori yang ditulis di kolom `kategori`/`sub_kategori` tapi
  belum ada di sistem akan **dibuat otomatis** agar proses tetap lancar.
- Baris dengan `kode_aset` atau `nama` kosong akan dilewati, dan jumlahnya
  dilaporkan lewat notifikasi setelah import selesai.

Dependency baru yang perlu di-install (sudah ada di `requirements.txt`):
`Flask-WTF`, `Flask-Limiter`, `openpyxl`, `Pillow`.

## 6. Yang Perlu Anda Sesuaikan Sendiri

Karena proyek ini butuh MySQL (XAMPP) yang berjalan di komputer lokal Anda,
kode ini **belum dijalankan/dites langsung** di lingkungan pembuatan —
silakan jalankan sesuai langkah di atas, lalu kabari jika ada error saat
instalasi (biasanya seputar koneksi database atau versi PyMySQL) supaya
saya bisa bantu perbaiki.
