"""
Model database untuk Website Manajemen Aset Perusahaan.
"""
from datetime import datetime
from flask_login import UserMixin
from extensions import db
import pytz
import json

WIB = pytz.timezone('Asia/Jakarta')

def get_wib_now():
    return datetime.now(WIB)


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Kategori(db.Model):
    __tablename__ = "kategori"
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    sub_kategori = db.relationship("SubKategori", backref="kategori", cascade="all, delete-orphan")


class SubKategori(db.Model):
    __tablename__ = "sub_kategori"
    id = db.Column(db.Integer, primary_key=True)
    id_kategori = db.Column(db.Integer, db.ForeignKey("kategori.id"), nullable=False)
    nama = db.Column(db.String(100), nullable=False)


class Aset(db.Model):
    __tablename__ = "aset"
    id = db.Column(db.Integer, primary_key=True)
    kode_aset = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    merek = db.Column(db.String(100), nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    foto_url = db.Column(db.String(500), nullable=True)
    gedung = db.Column(db.String(100), nullable=False)
    lantai = db.Column(db.String(50), nullable=True)
    ruangan = db.Column(db.String(100), nullable=False)
    status_aset = db.Column(db.String(20), default="Baik")
    jenis_aset = db.Column(db.String(20), nullable=False, default="Operasional")
    total_kerusakan = db.Column(db.Integer, default=0, nullable=False)
    spesifikasi = db.Column(db.Text, nullable=True)
    id_kategori = db.Column(db.Integer, db.ForeignKey("kategori.id"), nullable=True)
    id_sub_kategori = db.Column(db.Integer, db.ForeignKey("sub_kategori.id"), nullable=True)
    kategori = db.relationship("Kategori", foreign_keys=[id_kategori])
    sub_kategori = db.relationship("SubKategori", foreign_keys=[id_sub_kategori])


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
    created_at = db.Column(db.DateTime, default=get_wib_now)  # <-- PAKAI WIB
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