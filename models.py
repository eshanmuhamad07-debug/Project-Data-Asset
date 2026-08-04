"""
Model database untuk Website Manajemen Aset Perusahaan.
"""
from datetime import datetime
from flask_login import UserMixin
from extensions import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select
import pytz

# ============================================================
# TIMEZONE WIB (UTC+7)
# ============================================================
WIB = pytz.timezone('Asia/Jakarta')

def get_wib_now():
    return datetime.now(WIB)


# ============================================================
# USER
# ============================================================
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # hanya 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    foto_profil = db.Column(db.String(255), nullable=True)  # nama file di static/uploads
    banned_until = db.Column(db.DateTime, nullable=True)  # ban sementara sampai waktu ini
    ban_reason = db.Column(db.String(255), nullable=True)


# ============================================================
# KATEGORI (tanpa SubKategori)
# ============================================================
class Kategori(db.Model):
    __tablename__ = "kategori"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False, unique=True)
    # Relasi ke Aset
    aset_list = db.relationship("Aset", backref="kategori_ref", lazy=True)


# ============================================================
# MASTER LOKASI (Area / Gedung / Lantai / Ruangan)
# ============================================================
# Tabel-tabel ini TIDAK punya halaman kelola tersendiri (tidak ditampilkan
# sebagai menu di UI) -- tujuannya hanya sebagai sumber data untuk dropdown
# Area/Gedung/Lantai/Ruangan di form Tambah & Edit Aset. Data di tabel ini
# terisi OTOMATIS setiap kali ada import Excel Data Aset (lihat app.py,
# fungsi upsert_lokasi_master() yang dipanggil dari route /aset/import).
# Kolom Aset.area / Aset.gedung / Aset.lantai / Aset.ruangan TETAP berupa
# teks bebas seperti sebelumnya -- tabel master ini hanya dipakai untuk
# menyusun pilihan dropdown, bukan sebagai foreign key wajib dari Aset.
class Area(db.Model):
    __tablename__ = "area"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False, unique=True)


class Gedung(db.Model):
    __tablename__ = "gedung"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    # Nullable: ada kemungkinan data Excel tidak punya kolom Area terisi.
    id_area = db.Column(db.Integer, db.ForeignKey("area.id"), nullable=True)
    area_ref = db.relationship("Area", backref="gedung_list")

    # Nama gedung boleh sama di area/TCU berbeda (mis. "Gedung D" ada di
    # TCU1 & TCU2), jadi yang harus unik adalah kombinasi nama + area.
    __table_args__ = (
        db.UniqueConstraint("nama", "id_area", name="uq_gedung_nama_area"),
    )


class Lantai(db.Model):
    __tablename__ = "lantai"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(50), nullable=False)
    id_gedung = db.Column(db.Integer, db.ForeignKey("gedung.id"), nullable=False)
    gedung_ref = db.relationship("Gedung", backref="lantai_list")

    __table_args__ = (
        db.UniqueConstraint("nama", "id_gedung", name="uq_lantai_nama_gedung"),
    )


class Ruangan(db.Model):
    __tablename__ = "ruangan"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    id_gedung = db.Column(db.Integer, db.ForeignKey("gedung.id"), nullable=False)
    # Nullable: ada ruangan yang di Excel tidak dilengkapi info lantai.
    id_lantai = db.Column(db.Integer, db.ForeignKey("lantai.id"), nullable=True)
    gedung_ref = db.relationship("Gedung", backref="ruangan_list")
    lantai_ref = db.relationship("Lantai", backref="ruangan_list")

    __table_args__ = (
        db.UniqueConstraint(
            "nama", "id_gedung", "id_lantai", name="uq_ruangan_nama_gedung_lantai"
        ),
    )


# ============================================================
# ASET (DENGAN FIELD BARU DARI EXCEL)
# ============================================================
class Aset(db.Model):
    __tablename__ = "aset"

    id = db.Column(db.Integer, primary_key=True)

    # --- Field lama ---
    kode_aset = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    merek = db.Column(db.String(100), nullable=True)
    foto = db.Column(db.String(255), nullable=True)          # upload file
    foto_url = db.Column(db.String(500), nullable=True)      # link gambar

    gedung = db.Column(db.String(100), nullable=False)
    lantai = db.Column(db.String(50), nullable=True)
    ruangan = db.Column(db.String(100), nullable=False)

    status_aset = db.Column(db.String(20), default="Baik")   # Baik / Rusak / Tidak Terpakai
    total_kerusakan = db.Column(db.Integer, default=0, nullable=False)

    # --- Field BARU dari Excel ---
    area = db.Column(db.String(100), nullable=True)           # Area
    fungsi = db.Column(db.String(255), nullable=True)         # Fungsi Barang
    serial_number = db.Column(db.String(100), nullable=True)  # Serial Number
    volume = db.Column(db.String(50), nullable=True)          # Volume
    satuan = db.Column(db.String(50), nullable=True)          # Satuan
    tipe_aset = db.Column(db.String(20), nullable=True)  # CAPEX / OPEX
    link_qr = db.Column(db.String(500), nullable=True)        # Link QR (HIDDEN)
    tanggal_datang = db.Column(db.Date, nullable=True)        # Tanggal Barang Datang
    keterangan = db.Column(db.Text, nullable=True)            # Keterangan

    # --- Relasi Kategori (HAPUS SubKategori) ---
    id_kategori = db.Column(db.Integer, db.ForeignKey("kategori.id"), nullable=True)
    # kategori_ref sudah didefinisikan di Kategori

    # --- Field lainnya (spesifikasi) ---
    spesifikasi = db.Column(db.Text, nullable=True)

    # --- Relasi ke histori ---
    histori = db.relationship("HistoriAset", backref="aset_ref", cascade="all, delete-orphan")
    pengecekan_harian = db.relationship(
        "PengecekanHarian", backref="aset_ref", cascade="all, delete-orphan"
    )


# ============================================================
# PENGECEKAN HARIAN ASET
# ============================================================
# 1 baris = 1 hasil pengecekan untuk 1 aset di 1 tanggal (kolom `tanggal`
# HANYA tanggal, tanpa jam -- lihat unique constraint di bawah). Dropdown
# "Pengecekan Harian" di modal Edit Aset TIDAK wajib diisi -- kalau
# dikosongkan (value ""), tidak ada baris baru/diubah sama sekali.
#
# Mark hijau "Dicek Hari Ini" di halaman Data Aset dihitung langsung dari
# tabel ini: cek apakah ADA baris dengan tanggal == hari ini (WIB) dan
# status == "Selesai" untuk aset tsb. Karena perbandingannya selalu
# terhadap tanggal HARI INI, mark ini otomatis "hilang" begitu tanggal
# berganti -- tidak perlu job/cron reset terpisah. Riwayat pengecekan hari
# sebelumnya tetap tersimpan permanen di tabel ini (dan juga dicatat ke
# HistoriAset supaya muncul di Riwayat/Detail Aset & History).
class PengecekanHarian(db.Model):
    __tablename__ = "pengecekan_harian"
    id = db.Column(db.Integer, primary_key=True)
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=False)
    tanggal = db.Column(db.Date, nullable=False)  # tanggal WIB saat dicek (tanpa jam)
    status = db.Column(db.String(20), nullable=False)  # "Selesai" / "Belum"
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=get_wib_now)
    updated_at = db.Column(db.DateTime, default=get_wib_now, onupdate=get_wib_now)
    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("id_aset", "tanggal", name="uq_pengecekan_aset_tanggal"),
    )


# ============================================================
# TIKET (History)
# ============================================================
class Tiket(db.Model):
    __tablename__ = "tiket"
    id = db.Column(db.Integer, primary_key=True)
    jenis_tiket = db.Column(db.String(20), nullable=False)  # Pemindahan / Kerusakan
    nama_pemohon = db.Column(db.String(120), nullable=False)
    gedung_asal = db.Column(db.String(100), nullable=True)
    lantai_asal = db.Column(db.String(50), nullable=True)
    ruangan_asal = db.Column(db.String(100), nullable=True)
    gedung_tujuan = db.Column(db.String(100), nullable=True)
    lantai_tujuan = db.Column(db.String(50), nullable=True)
    ruangan_tujuan = db.Column(db.String(100), nullable=True)
    catatan = db.Column(db.Text, nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_wib_now)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user_creator = db.relationship("User", foreign_keys=[created_by])
    aset_terkait = db.relationship("TiketAset", backref="tiket", cascade="all, delete-orphan")
    log_status = db.relationship("LogStatus", backref="tiket", cascade="all, delete-orphan", order_by="LogStatus.created_at")

    @hybrid_property
    def status_tiket(self):
        """Status terkini tiket (Pending/Selesai), diambil dari histori
        LogStatus terakhir -- BUKAN kolom tersendiri (tabel tiket memang
        tidak dan tidak perlu punya kolom status_tiket sendiri, supaya
        1 sumber kebenaran cukup lewat LogStatus)."""
        if self.log_status:
            return self.log_status[-1].status_baru
        return "Pending"

    @status_tiket.expression
    def status_tiket(cls):
        """Versi SQL dari properti di atas, supaya tetap bisa dipakai untuk
        query.filter(Tiket.status_tiket == ...) di halaman Pemindahan/
        Kerusakan (dropdown filter status)."""
        return (
            select(LogStatus.status_baru)
            .where(LogStatus.id_tiket == cls.id)
            .order_by(LogStatus.id.desc())
            .limit(1)
            .correlate(cls)
            .scalar_subquery()
        )


class TiketAset(db.Model):
    __tablename__ = "tiket_aset"
    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    # Nullable: kalau aset yang bersangkutan sudah dihapus dari sistem,
    # id_aset akan dilepas (di-set None) supaya tidak melanggar constraint
    # FK, tapi tiket & histori-nya (mis. di menu Kerusakan) tetap tampil
    # berkat kode_aset_snapshot / nama_aset_snapshot di bawah ini.
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=True)
    aset = db.relationship("Aset")

    # Snapshot kode & nama aset saat tiket dibuat -- dipakai sebagai fallback
    # tampilan (di halaman Pemindahan/Kerusakan) kalau aset aslinya sudah
    # dihapus (aset relationship jadi None).
    kode_aset_snapshot = db.Column(db.String(50), nullable=True)
    nama_aset_snapshot = db.Column(db.String(150), nullable=True)


class LogStatus(db.Model):
    __tablename__ = "log_status"
    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    status_lama = db.Column(db.String(20), nullable=True)
    status_baru = db.Column(db.String(20), nullable=False)
    id_user_pengubah = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=get_wib_now)
    user_pengubah = db.relationship("User")


class HistoriAset(db.Model):
    __tablename__ = "histori_aset"
    id = db.Column(db.Integer, primary_key=True)
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=True)
    jenis_event = db.Column(db.String(20), nullable=False)
    gedung = db.Column(db.String(100), nullable=True)
    lantai = db.Column(db.String(50), nullable=True)
    ruangan = db.Column(db.String(100), nullable=True)
    gedung_asal = db.Column(db.String(100), nullable=True)
    lantai_asal = db.Column(db.String(50), nullable=True)
    ruangan_asal = db.Column(db.String(100), nullable=True)
    tanggal = db.Column(db.DateTime, default=get_wib_now, nullable=False)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=True)
    # Catatan bebas untuk detail event, mis. "Kondisi diubah dari Rusak
    # menjadi Baik (maintenance: Ganti sparepart AC)"
    keterangan = db.Column(db.Text, nullable=True)
    aset = db.relationship("Aset")
    tiket = db.relationship("Tiket")


class AktivitasLog(db.Model):
    __tablename__ = "aktivitas_log"
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    aksi = db.Column(db.String(50), nullable=False)
    target_model = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    deskripsi = db.Column(db.String(255), nullable=True)
    data_lama = db.Column(db.JSON, nullable=True)
    data_baru = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=get_wib_now)
    user = db.relationship("User")


class Peminjaman(db.Model):
    __tablename__ = "peminjaman"
    id = db.Column(db.Integer, primary_key=True)

    nama_peminjam = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(100), nullable=True)
    lokasi_kerja = db.Column(db.String(100), nullable=True)

    # --- Field dari import Excel (sheet BA Transfer) ---
    jenis_barang = db.Column(db.String(150), nullable=True)   # LEGACY: teks bebas asli hasil import (dipertahankan untuk histori/audit)
    id_kategori = db.Column(db.Integer, db.ForeignKey("kategori.id"), nullable=True)  # BARU: Jenis Barang sekarang mengacu ke tabel Kategori (sama seperti Aset)
    jenis_transaksi = db.Column(db.String(30), nullable=True)  # Peminjaman/Pengembalian/Pelimpahan IN/Pelimpahan OUT/dll (dari Excel)
    evidence_link = db.Column(db.String(500), nullable=True)   # link Google Drive PDF hasil import (bukan file upload)
    sumber_import = db.Column(db.Boolean, default=False, nullable=False)  # True = berasal dari import Excel

    kategori_ref = db.relationship("Kategori")  # kategori/jenis barang (untuk peminjaman non-aset-terdaftar)

    tanggal_pinjam = db.Column(db.Date, nullable=False)
    tanggal_rencana_kembali = db.Column(db.Date, nullable=True)
    tanggal_dikembalikan = db.Column(db.Date, nullable=True)

    status = db.Column(db.String(20), default="Dipinjam", nullable=False)  # Dipinjam / Dikembalikan
    status_perpanjangan = db.Column(db.String(30), nullable=True)  # None / 'Diperpanjang' / 'Tidak Diperpanjang'
    keterangan = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.String(255), nullable=True)  # file BA Serah Terima (gambar/pdf) -- upload manual

    created_at = db.Column(db.DateTime, default=get_wib_now)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user_creator = db.relationship("User", foreign_keys=[created_by])

    aset_terkait = db.relationship("PeminjamanAset", backref="peminjaman", cascade="all, delete-orphan")
    evidence_list = db.relationship(
        "PeminjamanEvidence",
        backref="peminjaman",
        cascade="all, delete-orphan",
        order_by="PeminjamanEvidence.tanggal_upload.desc()",
    )


class PeminjamanEvidence(db.Model):
    """Histori evidence laporan (BA/PDF) untuk 1 peminjaman.

    Dibuat supaya evidence baru bisa ditambahkan tanpa menghapus/menimpa
    evidence lama (kolom `Peminjaman.evidence` hanya menyimpan evidence
    awal saat data peminjaman pertama kali dibuat).
    """
    __tablename__ = "peminjaman_evidence"
    id = db.Column(db.Integer, primary_key=True)
    id_peminjaman = db.Column(db.Integer, db.ForeignKey("peminjaman.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    keterangan = db.Column(db.String(255), nullable=True)
    tanggal_upload = db.Column(db.DateTime, default=get_wib_now, nullable=False)
    id_user_uploader = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user_uploader = db.relationship("User")


class PeminjamanAset(db.Model):
    __tablename__ = "peminjaman_aset"
    id = db.Column(db.Integer, primary_key=True)
    id_peminjaman = db.Column(db.Integer, db.ForeignKey("peminjaman.id"), nullable=False)
    # Nullable: kalau aset yang bersangkutan sudah dihapus dari sistem,
    # id_aset akan dilepas (di-set None) supaya tidak melanggar constraint
    # FK, tapi riwayat peminjamannya tetap tampil berkat
    # kode_aset_snapshot / nama_aset_snapshot di bawah ini.
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=True)
    aset = db.relationship("Aset")

    kode_aset_snapshot = db.Column(db.String(50), nullable=True)
    nama_aset_snapshot = db.Column(db.String(150), nullable=True)


class CatatanAset(db.Model):
    """Catatan (notes) bebas terkait aset. Berbeda dari Histori/Maintenance/
    Kerusakan yang otomatis tercipta dari alur tiket -- CatatanAset murni
    dibuat manual oleh user untuk mencatat hal apapun, boleh terkait BANYAK
    aset sekaligus (lihat CatatanAsetItem) dan boleh punya BANYAK foto
    pendukung (lihat CatatanFoto)."""
    __tablename__ = "catatan_aset"

    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    keterangan = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=get_wib_now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    user = db.relationship("User")
    aset_list = db.relationship(
        "CatatanAsetItem", backref="catatan", cascade="all, delete-orphan"
    )
    foto_list = db.relationship(
        "CatatanFoto",
        backref="catatan",
        cascade="all, delete-orphan",
        order_by="CatatanFoto.uploaded_at",
    )


class CatatanAsetItem(db.Model):
    """Satu baris = satu aset yang dipilih untuk sebuah catatan (relasi
    banyak-ke-banyak Catatan <-> Aset, karena 1 catatan boleh terkait
    lebih dari 1 aset sekaligus)."""
    __tablename__ = "catatan_aset_item"
    id = db.Column(db.Integer, primary_key=True)
    id_catatan = db.Column(db.Integer, db.ForeignKey("catatan_aset.id"), nullable=False)
    # Nullable: kalau aset yang bersangkutan sudah dihapus dari sistem,
    # id_aset akan dilepas (di-set None) supaya tidak melanggar constraint
    # FK, tapi catatannya tetap tampil berkat kode_aset_snapshot /
    # nama_aset_snapshot di bawah ini (pola yang sama dengan Maintenance).
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=True)
    aset = db.relationship("Aset")

    kode_aset_snapshot = db.Column(db.String(50), nullable=True)
    nama_aset_snapshot = db.Column(db.String(150), nullable=True)


class CatatanFoto(db.Model):
    """Satu baris = satu foto pendukung sebuah catatan. 1 catatan boleh
    punya banyak foto (pola yang sama dengan PeminjamanEvidence)."""
    __tablename__ = "catatan_foto"
    id = db.Column(db.Integer, primary_key=True)
    id_catatan = db.Column(db.Integer, db.ForeignKey("catatan_aset.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=get_wib_now, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User")


class PengecekanAset(db.Model):
    """Pengecekan aset -- tombol ke-3 di Edit Data Aset (sejajar dengan
    'Pemindahan Aset' & 'Kerusakan Aset'). Setiap submit membuat 1 baris
    riwayat baru (radio Sudah Dicek/Belum Dicek + keterangan + foto
    opsional), otomatis muncul di History terpadu dan menjadi acuan
    tanda hijau "Sudah Dicek" di daftar Aset (menggantikan mekanisme
    dropdown 'Pengecekan Harian' + tabel PengecekanHarian yang lama)."""
    __tablename__ = "pengecekan_aset"

    id = db.Column(db.Integer, primary_key=True)

    # Nullable: kalau aset yang bersangkutan sudah dihapus dari sistem,
    # id_aset akan dilepas (di-set None) supaya tidak melanggar constraint
    # FK, tapi riwayat pengecekannya tetap tampil berkat kode_aset_snapshot
    # / nama_aset_snapshot di bawah ini (pola yang sama dengan Maintenance).
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=True)
    kode_aset_snapshot = db.Column(db.String(50), nullable=True)
    nama_aset_snapshot = db.Column(db.String(150), nullable=True)

    status = db.Column(db.String(20), nullable=False)  # "Sudah Dicek" / "Belum Dicek"
    keterangan = db.Column(db.Text, nullable=True)
    foto = db.Column(db.String(255), nullable=True)  # nama file di static/uploads, opsional

    created_at = db.Column(db.DateTime, default=get_wib_now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    aset = db.relationship("Aset")
    user = db.relationship("User")


class Maintenance(db.Model):
    __tablename__ = "maintenance"


    id = db.Column(db.Integer, primary_key=True)
    # Nullable: kalau aset yang bersangkutan sudah dihapus dari sistem,
    # id_aset akan dilepas (di-set None) supaya tidak melanggar constraint
    # FK, tapi riwayat maintenance-nya tetap tampil berkat
    # kode_aset_snapshot / nama_aset_snapshot di bawah ini.
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=True)
    kode_aset_snapshot = db.Column(db.String(50), nullable=True)
    nama_aset_snapshot = db.Column(db.String(150), nullable=True)
    kategori = db.Column(db.String(50), nullable=False)  # Elektronik / Furniture
    judul = db.Column(db.String(200), nullable=False)
    deskripsi = db.Column(db.Text, nullable=True)
    vendor = db.Column(db.String(100), nullable=True)
    tipe = db.Column(db.String(50), nullable=False)  # Preventif / Korektif / Inspeksi
    tanggal_mulai = db.Column(db.Date, nullable=False)
    tanggal_akhir = db.Column(db.Date, nullable=True)
    biaya = db.Column(db.Numeric(15, 2), default=0.00)  # <-- PAKAI NUMERIC
    status = db.Column(db.String(20), default="Scheduled")
    created_at = db.Column(db.DateTime, default=get_wib_now)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # --- Foto dokumentasi maintenance (hanya tampil di halaman Detail) ---
    foto_before = db.Column(db.String(255), nullable=True)
    foto_progress = db.Column(db.String(255), nullable=True)
    foto_after = db.Column(db.String(255), nullable=True)

    aset = db.relationship("Aset")
    user = db.relationship("User")
