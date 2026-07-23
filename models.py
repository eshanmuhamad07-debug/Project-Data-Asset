"""
Model database untuk Website Manajemen Aset Perusahaan.
"""
from datetime import datetime
from flask_login import UserMixin
from extensions import db
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
    
    status_aset = db.Column(db.String(20), default="Baik")   # Baik / Rusak
    total_kerusakan = db.Column(db.Integer, default=0, nullable=False)
    
    # --- Field BARU dari Excel ---
    area = db.Column(db.String(100), nullable=True)           # Area
    fungsi = db.Column(db.String(255), nullable=True)         # Fungsi Barang
    serial_number = db.Column(db.String(100), nullable=True)  # Serial Number
    volume = db.Column(db.String(50), nullable=True)          # Volume
    satuan = db.Column(db.String(50), nullable=True)          # Satuan
    tipe_aset = db.Column(db.String(20), nullable=False, default="OPEX")  # CAPEX / OPEX
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


class TiketAset(db.Model):
    __tablename__ = "tiket_aset"
    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=False)
    aset = db.relationship("Aset")


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
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=False)
    jenis_event = db.Column(db.String(20), nullable=False)
    gedung = db.Column(db.String(100), nullable=True)
    lantai = db.Column(db.String(50), nullable=True)
    ruangan = db.Column(db.String(100), nullable=True)
    gedung_asal = db.Column(db.String(100), nullable=True)
    lantai_asal = db.Column(db.String(50), nullable=True)
    ruangan_asal = db.Column(db.String(100), nullable=True)
    tanggal = db.Column(db.DateTime, default=get_wib_now, nullable=False)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=True)
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

class Maintenance(db.Model):
    __tablename__ = "maintenance"

    id = db.Column(db.Integer, primary_key=True)
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=False)
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

    aset = db.relationship("Aset")
    user = db.relationship("User")