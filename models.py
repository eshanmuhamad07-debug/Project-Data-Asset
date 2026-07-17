"""
Model database untuk Website Manajemen Aset Perusahaan.

Catatan tambahan di luar 6 tabel inti yang diminta:
- Kategori & SubKategori  -> diminta di bagian "Fitur Kategorisasi Aset (2 Level)"
- TiketAset (tabel junction) -> WAJIB ada karena 1 tiket bisa berisi banyak aset
  (form pembuatan tiket meminta "Pilih Aset checkbox/select multiple"), tapi tabel
  ini tidak disebutkan eksplisit di daftar 6 tabel. Ditambahkan agar relasi valid.
- Notifikasi -> diperlukan untuk fitur "Ikon Lonceng (Bell)" agar status baca
  notifikasi bisa dilacak per user, bukan sekadar dihitung ulang setiap saat.
"""
from datetime import datetime
from flask_login import UserMixin
from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / officer / teknisi
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    # is_active dipakai untuk nonaktifkan akun (soft-delete) alih-alih hapus
    # permanen -- menghapus user yang punya riwayat tiket/komentar akan gagal
    # karena foreign key, jadi solusinya dinonaktifkan saja (Solusi #8).

    def is_admin(self):
        return self.role == "admin"

    def is_officer(self):
        return self.role == "officer"

    def is_teknisi(self):
        return self.role == "teknisi"


class Kategori(db.Model):
    __tablename__ = "kategori"

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)

    sub_kategori = db.relationship(
        "SubKategori", backref="kategori", cascade="all, delete-orphan"
    )


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
    foto = db.Column(db.String(255), nullable=True)
    gedung = db.Column(db.String(100), nullable=False)
    lantai = db.Column(db.String(50), nullable=True)
    # lantai: kolom ini sudah dipakai di app.py (filter, form, export/import)
    # tapi belum pernah didefinisikan di model -- ditambahkan di sini supaya
    # tambah/edit/export/import aset tidak error.
    ruangan = db.Column(db.String(100), nullable=False)
    status_aset = db.Column(db.String(20), default="Baik")  # Baik / Rusak / Dipindahkan
    jenis_aset = db.Column(db.String(20), nullable=False, default="Operasional")
    # jenis_aset: "Operasional" (dipakai sehari-hari di lapangan/cabang) atau
    # "Pusat" (aset milik/tercatat di kantor pusat).

    id_kategori = db.Column(db.Integer, db.ForeignKey("kategori.id"), nullable=True)
    id_sub_kategori = db.Column(db.Integer, db.ForeignKey("sub_kategori.id"), nullable=True)

    kategori = db.relationship("Kategori", foreign_keys=[id_kategori])
    sub_kategori = db.relationship("SubKategori", foreign_keys=[id_sub_kategori])


class Tiket(db.Model):
    __tablename__ = "tiket"

    id = db.Column(db.Integer, primary_key=True)
    jenis_tiket = db.Column(db.String(20), nullable=False)  # Pemindahan / Perbaikan
    nama_pemohon = db.Column(db.String(120), nullable=False)
    gedung_tujuan = db.Column(db.String(100), nullable=True)
    ruangan_tujuan = db.Column(db.String(100), nullable=True)
    catatan = db.Column(db.Text, nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    status_tiket = db.Column(db.String(20), default="Pending")
    # Pending / Disetujui / Ditolak / Proses / Selesai
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    aset_terkait = db.relationship("TiketAset", backref="tiket", cascade="all, delete-orphan")
    pelaksana = db.relationship("TiketUser", backref="tiket", cascade="all, delete-orphan")
    komentar = db.relationship(
        "KomentarTiket", backref="tiket", cascade="all, delete-orphan",
        order_by="KomentarTiket.created_at"
    )
    log_status = db.relationship(
        "LogStatus", backref="tiket", cascade="all, delete-orphan",
        order_by="LogStatus.created_at"
    )


class TiketAset(db.Model):
    """Tabel junction many-to-many antara Tiket dan Aset."""
    __tablename__ = "tiket_aset"

    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    id_aset = db.Column(db.Integer, db.ForeignKey("aset.id"), nullable=False)
    status_sebelum = db.Column(db.String(20), nullable=True)
    # status_sebelum menyimpan status_aset SEBELUM tiket dibuat, dipakai untuk
    # mengembalikan status aset jika tiket ini ditolak (Solusi #7).

    aset = db.relationship("Aset")


class TiketUser(db.Model):
    """Tabel junction many-to-many antara Tiket dan User (pembuat/pelaksana)."""
    __tablename__ = "tiket_user"

    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    peran_di_tiket = db.Column(db.String(20), nullable=False)  # pembuat / pelaksana

    user = db.relationship("User")


class KomentarTiket(db.Model):
    __tablename__ = "komentar_tiket"

    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pesan = db.Column(db.Text, nullable=True)
    foto_komentar = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")


class LogStatus(db.Model):
    __tablename__ = "log_status"

    id = db.Column(db.Integer, primary_key=True)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=False)
    status_lama = db.Column(db.String(20), nullable=True)
    status_baru = db.Column(db.String(20), nullable=False)
    id_user_pengubah = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_pengubah = db.relationship("User")


class Notifikasi(db.Model):
    __tablename__ = "notifikasi"

    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    id_tiket = db.Column(db.Integer, db.ForeignKey("tiket.id"), nullable=True)
    pesan = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
