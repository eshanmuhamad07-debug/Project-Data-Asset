# Website Manajemen Aset Perusahaan

Aplikasi manajemen aset berbasis **Flask + MySQL (XAMPP) + Tailwind CSS (CDN)**.

> ⚠️ **Catatan:** dokumen ini ditulis ulang berdasarkan pembacaan langsung ke
> `app.py`, `models.py`, `roles.py`, dan `seed.py` di dalam paket ini, karena
> alur bisnis aplikasi sudah banyak berubah dari versi awal (lihat bagian
> [8. Riwayat Perubahan Besar](#8-riwayat-perubahan-besar-dari-versi-awal)).
> **Alur tiket dengan approval multi-role, komentar, dan notifikasi bell yang
> dijelaskan di versi README sebelumnya SUDAH TIDAK BERLAKU.**

Modul yang tersedia saat ini:
- **Data Aset** — CRUD aset + kategori, filter berlapis (area/gedung/lantai/
  ruangan/kategori/tipe/status), export & import Excel.
- **Pemindahan & Kerusakan** — pencatatan aset dipindah lokasi atau ditandai
  rusak. Langsung tercatat selesai (tanpa alur approval).
- **Peminjaman Aset** — pencatatan aset/barang yang dipinjam, tanggal
  rencana kembali, evidence (BA serah terima), reminder & kalender
  perpanjangan, plus import dari Excel (sheet "BA Transfer").
- **Maintenance** — jadwal perawatan aset dengan dokumentasi foto
  Sebelum/Sedang Berlangsung/Sesudah.
- **History** — linimasa terpadu (Pemindahan, Kerusakan, Peminjaman,
  Maintenance, Aktivitas admin) dengan filter per jenis.
- **Kelola User** — hanya untuk admin: tambah user, aktif/nonaktifkan, ban
  sementara.
- **Profil** — semua user login bisa update nama/email, ganti password, dan
  foto profil sendiri.

## 1. Struktur Proyek

```
asset_management/
├── app.py                    # Entry point + seluruh route (± 2950 baris)
├── models.py                 # SQLAlchemy models
├── extensions.py             # instance db, login_manager, csrf, limiter
├── roles.py                  # konstanta role (saat ini HANYA "admin")
├── seed.py                   # seeder: membuat 1 akun admin awal
├── requirements.txt
├── static/
│   ├── js/main.js             # sidebar toggle, modal, chained dropdown, search/filter
│   └── uploads/                # foto aset/tiket/maintenance/profil & dokumen evidence
└── templates/
    ├── base.html               # layout sidebar + navbar
    ├── login.html / register.html
    ├── dashboard.html          # statistik, grafik, kalender peminjaman
    ├── profile.html
    ├── 403.html
    ├── _macros.html
    ├── aset/
    │   ├── list.html            # halaman utama Data Aset (CRUD modal)
    │   └── import_guide.html
    ├── kategori/list.html      # kelola kategori (admin only)
    ├── peminjaman/
    │   ├── list.html
    │   ├── detail.html
    │   └── import_guide.html
    ├── maintenance/
    │   ├── list.html
    │   └── detail.html          # + upload foto before/progress/after
    ├── history/
    │   ├── list.html            # linimasa terpadu
    │   ├── detail.html          # detail 1 event Pemindahan/Kerusakan
    │   └── aktivitas_detail.html
    └── users/list.html         # kelola user (admin only)
```

### Template yang sudah tidak dipakai (orphan)

File-file berikut masih ada di folder `templates/` tapi **tidak lagi
dirender oleh route mana pun** di `app.py` — sisa dari versi lama sebelum
alur tiket-approval diganti dengan alur "History" langsung-selesai. Aman
dihapus, atau dibiarkan sebagai referensi:

- `templates/tiket/list.html`, `templates/tiket/detail.html` — dulu halaman
  daftar & detail tiket dengan approval/komentar, sudah digantikan
  `templates/history/list.html` & `templates/history/detail.html`.
- `templates/notifikasi.html` — dulu halaman notifikasi bell, fitur ini
  **sudah dihapus** (tidak ada model `Notifikasi` maupun route `/notifikasi`
  di `app.py` saat ini).
- `templates/list.html` (di root `templates/`) — tidak direferensikan route apa pun.

## 2. Cara Menjalankan

1. **Aktifkan XAMPP**, nyalakan modul **MySQL**.
2. Buka phpMyAdmin (`http://localhost/phpmyadmin`) lalu buat database baru bernama:
   ```
   db_manajemen_aset
   ```
   (tidak perlu membuat tabel manual — akan dibuat otomatis oleh SQLAlchemy).
3. Jika user/password MySQL Anda **bukan** `root` tanpa password, set
   environment variable (lihat bagian 2a) atau ubah langsung default di
   `app.py`:
   ```python
   DB_USER = os.environ.get("DB_USER", "root")
   DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
   ```
4. Install dependency (disarankan pakai virtual environment):
   ```
   pip install -r requirements.txt
   ```
   > ⚠️ `models.py` mengimpor `pytz` untuk menghitung waktu WIB, tapi `pytz`
   > **tidak** ada di `requirements.txt`. Tambahkan manual jika instalasi
   > gagal dengan error `ModuleNotFoundError: pytz`:
   > ```
   > pip install pytz
   > ```
5. Buat tabel & akun admin awal (jalankan seeder):
   ```
   python seed.py
   ```
6. Jalankan aplikasi:
   ```
   python app.py
   ```
7. Buka browser ke `http://localhost:5001` — **bukan port 5000**. Port dan
   mode debug sekarang di-hardcode di baris terakhir `app.py`:
   ```python
   app.run(debug=True, host="0.0.0.0", port=5001)
   ```
   `debug=True` aktif permanen di kode saat ini (env var `FLASK_DEBUG` yang
   disebut di dokumentasi versi lama **tidak lagi dibaca** oleh baris ini).
   Untuk production, ubah baris ini secara manual sebelum deploy.

### 2a. Environment variable yang didukung

```bash
export SECRET_KEY="ganti-dengan-string-acak-panjang"
export DB_USER=root
export DB_PASSWORD=
export DB_HOST=localhost
export DB_NAME=db_manajemen_aset
```

Kalau tidak di-set, aplikasi tetap jalan dengan default yang cocok untuk
XAMPP lokal.

## 3. Akun

Seeder (`python seed.py`) hanya membuat **satu akun admin**:

| Role  | Email          | Password    |
|-------|----------------|-------------|
| Admin | admin@aset.com | password123 |

Akun tambahan dibuat melalui salah satu dari dua cara:

- **Halaman Register** (`/register`) — siapa saja bisa mendaftar sendiri,
  tapi **wajib** pakai email `@gmail.com`, dan otomatis mendapat role
  `"user"` (akses terbatas, lihat bagian 4).
- **Halaman Kelola User** (`/users`, khusus admin) — admin bisa membuat user
  baru dengan role `admin` atau `user`, serta menonaktifkan/mengaktifkan
  atau mem-ban sementara (dengan tanggal berakhir & alasan) akun tertentu.

> Catatan: `roles.py` saat ini hanya mendefinisikan `ROLE_ADMIN = "admin"`
> (sisa role lama seperti `officer`/`teknisi` sudah dihapus). Role `"user"`
> tetap dipakai di beberapa tempat (register, kelola user) sebagai string
> biasa, bukan konstanta di `roles.py`.

## 4. Role & Hak Akses

Sistem role sekarang jauh lebih sederhana dibanding versi awal (tidak ada
lagi alur approval/multi-assign per role):

| Role    | Bisa melihat semua halaman (dashboard, data aset, peminjaman, maintenance, history, profil)? | Bisa tambah/edit/hapus data (aset, kategori, pemindahan, kerusakan, peminjaman, maintenance, user)? |
|---------|---|---|
| `admin` | ✅ | ✅ |
| `user`  | ✅ (read-only) | ❌ — akan mendapat halaman `403.html` jika mencoba akses route yang di-protect `role_required(ROLE_ADMIN)` |

Semua route mutasi data (`*_create`, `*_edit`, `*_delete`, `*_import`,
pemindahan/kerusakan, peminjaman, maintenance, kategori, kelola user)
dilindungi decorator `@role_required(ROLE_ADMIN)`. Route baca-saja
(`dashboard`, `aset_list`, `peminjaman_list`, `history_list`, `profile`,
dll.) hanya butuh `@login_required` sehingga bisa diakses role apa pun yang
sudah login.

## 5. Alur Bisnis per Modul (Kondisi Saat Ini)

### 5.1 Data Aset (`/aset`)
- CRUD aset lewat modal popup (create/edit/delete/hapus massal).
- Field aset mencakup: kode aset, nama, merek, foto (upload atau link URL),
  area/gedung/lantai/ruangan, status (Baik/Rusak), tipe aset (CAPEX/OPEX),
  kategori, fungsi barang, serial number, volume, satuan, link QR (hidden),
  tanggal barang datang, keterangan, spesifikasi.
- Filter berlapis: pencarian nama/kode, status, kategori, area+gedung
  (chained dropdown ke lantai → ruangan lewat `/api/lantai` dan
  `/api/ruangan`), tipe aset.
- **Export** ke Excel (`/aset/export`, admin only) dan **Import** dari Excel
  (`/aset/import`) dengan pencocokan berdasarkan `kode_aset` — kode yang
  sudah ada di-update, kode baru dibuat sebagai aset baru; kategori yang
  belum ada dibuat otomatis.
- Setiap perubahan (tambah/edit/hapus/pindah) otomatis dicatat ke
  `AktivitasLog` dan muncul di halaman History.

### 5.2 Pemindahan & Kerusakan (dibuat dari halaman History, disimpan sebagai `Tiket`)
- **Tidak ada lagi alur approval/proses/selesai bertingkat.** Begitu form
  disubmit (`POST /tiket/create/pemindahan` atau `/tiket/create/kerusakan`),
  data langsung tercatat **selesai**:
  - **Pemindahan**: lokasi (gedung/lantai/ruangan) semua aset yang dipilih
    langsung diupdate ke lokasi tujuan, status aset diset "Baik", dan
    dicatat ke `HistoriAset` (jenis event `pindah`).
  - **Kerusakan**: status aset yang dipilih langsung diubah jadi "Rusak",
    counter `total_kerusakan` bertambah, dan dicatat ke `HistoriAset`
    (jenis event `rusak`).
- Bisa multi-aset dalam satu tiket (checkbox pilih aset).
- Detail read-only tiket bisa dilihat di `/history/<id>` (route
  `history_detail`, render `history/detail.html`).
- Model `Komentar`/thread diskusi dan multi-assign pelaksana pada tiket
  **sudah tidak ada** di kode saat ini.

### 5.3 Peminjaman Aset (`/peminjaman`)
- Mencatat siapa meminjam (nama, unit, lokasi kerja), barang/aset yang
  dipinjam (bisa multi-aset), jenis transaksi (Peminjaman/Pengembalian/
  Pelimpahan IN/OUT/dll — meniru sheet "BA Transfer" dari Excel lama),
  tanggal pinjam, rencana kembali, dan file **evidence** (gambar atau
  dokumen, BA serah terima).
- Status: `Dipinjam` → `Dikembalikan` (via `/peminjaman/<id>/kembalikan`).
  "Terlambat" bukan kolom database, melainkan status turunan
  (`Dipinjam` + `tanggal_rencana_kembali` sudah lewat).
- **Konfirmasi perpanjangan**: dashboard menampilkan peminjaman yang jatuh
  tempo ≤10 hari lagi atau sudah lewat (`peminjaman_reminder`), admin bisa
  konfirmasi lewat modal di dashboard (`/peminjaman/<id>/konfirmasi-perpanjangan`).
- **Kalender**: dashboard menampilkan kalender bulanan yang menandai
  tanggal rencana kembali tiap peminjaman aktif, termasuk hari libur
  nasional 2026 (hardcoded di `app.py`).
- **Import** dari file Excel sheet "BA Transfer" (`/peminjaman/import`) —
  mendukung evidence berupa link Google Drive.
- Field `evidence` di tabel `peminjaman` sekarang hanya diisi **sekali**
  saat data dibuat; belum ada tabel histori evidence terpisah di kode saat
  ini (lihat catatan versi lama di bagian 8 — fitur `PeminjamanEvidence`
  yang pernah didokumentasikan **tidak ditemukan** di `models.py`/`app.py`
  paket ini).

### 5.4 Maintenance (`/maintenance`)
- Jadwal perawatan per aset: kategori (Elektronik/Furniture), judul,
  deskripsi, vendor, tipe (Preventif/Korektif/Inspeksi), tanggal
  mulai/akhir, biaya, status.
- Halaman **Detail** (`/maintenance/<id>/detail`) berisi 3 slot foto
  dokumentasi: **Sebelum**, **Sedang Berlangsung**, **Sesudah** — upload,
  lihat, dan hapus foto hanya bisa dilakukan dari halaman ini
  (`/maintenance/<id>/foto/<slot>` dan `/maintenance/<id>/foto/<slot>/delete`).
- Upload foto divalidasi isi filenya (bukan cuma ekstensi) memakai Pillow.

### 5.5 History (`/history`)
- Linimasa terpadu yang menggabungkan 4 sumber data (diurutkan berdasarkan
  waktu terbaru, dengan pagination 10 per halaman):
  1. **Tiket** — Pemindahan & Kerusakan
  2. **Peminjaman** — termasuk status "Dikembalikan"
  3. **Aktivitas admin** (hanya tampil untuk role admin) — tambah/edit/hapus
     aset, peminjaman, maintenance
  4. **Maintenance** — jadwal yang dibuat
- Filter berdasarkan jenis (`?filter=Pemindahan|Kerusakan|Peminjaman|Maintenance|Aktivitas`).
- Klik satu baris membuka detail sesuai jenisnya (`history_detail`,
  `aktivitas_detail`, atau `peminjaman_detail`).

### 5.6 Kelola User (`/users`, admin only)
- Tambah user baru dengan role `admin`/`user`.
- **Toggle aktif/nonaktif** (`is_active`) — tidak menghapus data user secara
  permanen supaya relasi foreign key tetap aman.
- **Ban sementara** — set `banned_until` (tanggal & jam) plus alasan; bisa
  dicabut lewat unban. (Perlu dicek di route `login()` apakah user yang
  `banned_until` masih berlaku ditolak login — lihat langsung ke fungsi
  `login()` di `app.py` untuk detail pastinya.)
- Admin tidak bisa menonaktifkan/mem-ban akun sendiri.

### 5.7 Profil (`/profile`, semua role)
- Update nama & email sendiri, ganti password (validasi password lama +
  minimal 8 karakter), upload/hapus foto profil sendiri.

## 6. Skema Database Saat Ini

Tabel yang benar-benar ada di `models.py` (bukan 9 tabel seperti
dokumentasi versi lama):

| Tabel | Fungsi |
|---|---|
| `user` | Akun login, role, status aktif/ban, foto profil |
| `kategori` | Kategori aset (1 level, **tidak ada** `sub_kategori`) |
| `aset` | Data aset lengkap dengan field hasil import Excel |
| `tiket` | Catatan Pemindahan/Kerusakan (langsung selesai) |
| `tiket_aset` | Junction tiket ↔ aset (multi-aset per tiket) |
| `log_status` | Riwayat status tiket (dipakai untuk timeline) |
| `histori_aset` | Riwayat event per aset: pindah/rusak/pinjam |
| `aktivitas_log` | Log aktivitas CRUD aset/peminjaman/maintenance oleh admin |
| `peminjaman` | Data peminjaman aset/barang |
| `peminjaman_aset` | Junction peminjaman ↔ aset |
| `maintenance` | Jadwal maintenance + 3 kolom foto (before/progress/after) |

**Tidak ada** di kode saat ini (meski pernah didokumentasikan di versi
README sebelumnya): `sub_kategori`, `komentar_tiket`, `notifikasi`,
`peminjaman_evidence`, `tiket_user`.

## 7. Fitur yang Sudah Diimplementasikan (ringkasan)

- ✅ Login/logout (`flask-login`) + hash password (`werkzeug.security`) +
  rate-limit brute-force login (`Flask-Limiter`, 8x/menit/IP)
- ✅ Register mandiri (khusus email `@gmail.com`), default role `user`
- ✅ Proteksi CSRF di seluruh form (`Flask-WTF`)
- ✅ Proteksi route berdasarkan role (`role_required` decorator)
- ✅ Sidebar collapsible mobile-friendly (Tailwind, vanilla JS)
- ✅ Dashboard: statistik aset/kategori/maintenance/pemindahan, grafik
  Chart.js aset per kategori, kalender peminjaman + reminder perpanjangan
- ✅ CRUD Aset (modal, upload/URL foto, filter berlapis, export & import Excel)
- ✅ Kategori 1 level (admin only)
- ✅ Pemindahan & Kerusakan aset (langsung tercatat selesai, multi-aset)
- ✅ Peminjaman aset (multi-aset, evidence, status, import Excel, kalender)
- ✅ Maintenance dengan 3 slot foto dokumentasi (before/progress/after)
- ✅ History terpadu (tiket + peminjaman + aktivitas admin + maintenance)
  dengan filter jenis & pagination
- ✅ Kelola user: tambah, aktif/nonaktif, ban sementara (admin only)
- ✅ Profil: update data diri, ganti password, foto profil
- ✅ Validasi upload gambar berdasar isi file, bukan cuma ekstensi (Pillow)
- ✅ Seeder membuat 1 akun admin awal

**Fitur yang pernah didokumentasikan di versi README sebelumnya tapi
TIDAK ditemukan di kode saat ini** (kemungkinan sudah dihapus/diganti
pendekatan lain):
- ❌ Alur tiket approve → proses → selesai dengan multi-assign pelaksana
- ❌ Thread komentar per tiket
- ❌ Notifikasi bell dengan badge counter
- ❌ Histori evidence peminjaman multi-upload (tabel `peminjaman_evidence`)
- ❌ Kategori 2 level (`sub_kategori`) + chained dropdown kategori→sub-kategori
- ❌ Role `officer`/`teknisi`

## 8. Riwayat Perubahan Besar dari Versi Awal

Ringkasan arah perubahan arsitektur dibanding dokumentasi versi paling
awal proyek ini (untuk konteks, bukan langkah yang perlu dijalankan ulang):

1. Role disederhanakan dari `admin/officer/teknisi` menjadi hanya
   `admin` (di `roles.py`), ditambah role generik `user` (read-only) dari
   fitur self-register.
2. Alur tiket dengan approval bertingkat + multi-assign + komentar +
   notifikasi diganti total menjadi alur **Pemindahan/Kerusakan langsung
   selesai**, dicatat di modul **History** terpadu.
3. Modul **Peminjaman Aset** dan **Maintenance** (dengan dokumentasi foto)
   ditambahkan sebagai modul baru yang berdiri sendiri.
4. Kategori disederhanakan dari 2 level (kategori + sub-kategori) menjadi
   1 level saja.
5. Ditambahkan fitur **Kelola User** dengan aktif/nonaktif dan ban
   sementara, menggantikan pendekatan hapus user permanen.
6. Ditambahkan export/import Excel untuk Data Aset dan Peminjaman.

## 9. Yang Perlu Anda Sesuaikan Sendiri

Karena proyek ini butuh MySQL (XAMPP) yang berjalan di komputer lokal Anda,
dan dokumentasi ini disusun ulang murni dari membaca kode (bukan dari
menjalankan aplikasinya secara langsung), disarankan untuk:

- Menjalankan `python seed.py` lalu `python app.py`, mengecek semua modul
  di atas satu per satu, dan mengabari jika ada perilaku yang tidak sesuai
  dengan penjelasan di README ini supaya bisa segera diperbaiki.
- Menambahkan `pytz` ke `requirements.txt` (lihat catatan di bagian 2)
  sebelum deploy ke lingkungan baru.
- Meninjau ulang `app.run(debug=True, ...)` di baris terakhir `app.py`
  sebelum dipakai di production.
