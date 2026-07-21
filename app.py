import os
import io
from functools import wraps
from datetime import datetime, timedelta, timezone
import pytz

from flask import (
    Flask, render_template, redirect, url_for, request, flash, jsonify,
    abort, send_file
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from PIL import Image
import openpyxl
from openpyxl.utils import get_column_letter
import re

from extensions import db, login_manager, csrf, limiter
from models import (
    User, Kategori, Aset, Tiket, TiketAset,
    LogStatus, HistoriAset, AktivitasLog 
)
from roles import ROLE_ADMIN

# ---------------------------------------------------------------------------
# Konfigurasi Aplikasi
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "jpe", "jfif", "bmp", "tiff", "tif"}

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-only-jangan-dipakai-di-production"
)

DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "db_manajemen_aset")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
limiter.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Set timezone ke WIB (UTC+7)
WIB = pytz.timezone('Asia/Jakarta')


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def is_valid_image(file_storage):
    try:
        pos = file_storage.stream.tell()
        Image.open(file_storage.stream).verify()
        file_storage.stream.seek(pos)
        return True
    except Exception:
        return False


def save_upload(file_storage, prefix=""):
    if not file_storage or file_storage.filename == "":
        return None, None
    if not allowed_file(file_storage.filename):
        return None, f"Ekstensi file tidak diizinkan. Gunakan: {', '.join(ALLOWED_EXT)}"
    if not is_valid_image(file_storage):
        return None, "File yang diupload bukan gambar yang valid."
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None, "Nama file tidak valid."
    unique_name = f"{prefix}{datetime.now(WIB).strftime('%Y%m%d%H%M%S%f')}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    try:
        file_storage.save(filepath)
        return unique_name, None
    except Exception as e:
        return None, f"Gagal menyimpan file: {str(e)}"


def convert_gdrive_to_thumbnail(url):
    if not url:
        return url
    if 'drive.google.com' not in url:
        return url
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    return url

def catat_aktivitas(aksi, target_model, target_id, deskripsi=None, data_lama=None, data_baru=None):
    """Catat aktivitas admin ke tabel aktivitas_log."""
    log = AktivitasLog(
        id_user=current_user.id,
        aksi=aksi,
        target_model=target_model,
        target_id=target_id,
        deskripsi=deskripsi,
        data_lama=data_lama,
        data_baru=data_baru
    )
    db.session.add(log)

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def catat_log(tiket, status_lama, status_baru):
    db.session.add(LogStatus(
        id_tiket=tiket.id,
        status_lama=status_lama,
        status_baru=status_baru,
        id_user_pengubah=current_user.id
    ))


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(IntegrityError)
def handle_integrity_error(e):
    db.session.rollback()
    flash(
        "Data tidak bisa disimpan: kemungkinan data duplikat atau masih "
        "terkait dengan data lain.",
        "danger",
    )
    return redirect(request.referrer or url_for("dashboard"))


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("8 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash("Akun ini sudah dinonaktifkan. Hubungi admin.", "danger")
                return render_template("login.html")
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Email atau password salah.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    total_aset = Aset.query.count()
    total_history = Tiket.query.count()  # semua tiket = history
    total_rusak = Aset.query.filter_by(status_aset="Rusak").count()

    kategori_chart = (
        db.session.query(Kategori.nama, db.func.count(Aset.id))
        .outerjoin(Aset, Aset.id_kategori == Kategori.id)
        .group_by(Kategori.id)
        .all()
    )
    chart_labels = [k[0] for k in kategori_chart]
    chart_values = [k[1] for k in kategori_chart]

    history_terbaru = Tiket.query.order_by(Tiket.created_at.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        total_aset=total_aset,
        total_history=total_history,
        total_rusak=total_rusak,
        chart_labels=chart_labels,
        chart_values=chart_values,
        history_terbaru=history_terbaru,
    )


# ---------------------------------------------------------------------------
# ASET (CRUD)
# ---------------------------------------------------------------------------
JENIS_ASET_OPTIONS = ["Operasional", "Pusat"]


@app.route("/aset")
@login_required
def aset_list():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    kategori_id = request.args.get("kategori", "")
    gedung = request.args.get("gedung", "")
    lantai = request.args.get("lantai", "")
    ruangan = request.args.get("ruangan", "")

    query = Aset.query
    if q:
        query = query.filter(
            db.or_(Aset.nama.ilike(f"%{q}%"), Aset.kode_aset.ilike(f"%{q}%"))
        )
    if status:
        query = query.filter_by(status_aset=status)
    if kategori_id:
        query = query.filter_by(id_kategori=kategori_id)
    if gedung:
        query = query.filter_by(gedung=gedung)
    if lantai:
        query = query.filter_by(lantai=lantai)
    if ruangan:
        query = query.filter_by(ruangan=ruangan)

    filter_aktif = bool(q or status or kategori_id or gedung or lantai or ruangan)

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Aset.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    daftar_aset = pagination.items
    kategori_all = Kategori.query.all()
    gedung_all = [
        g[0] for g in db.session.query(Aset.gedung).distinct().order_by(Aset.gedung).all() if g[0]
    ]
    total_keseluruhan = Aset.query.count()
    return render_template(
        "aset/list.html",
        daftar_aset=daftar_aset,
        kategori_all=kategori_all,
        pagination=pagination,
        gedung_all=gedung_all,
        filter_aktif=filter_aktif,
        total_keseluruhan=total_keseluruhan,
    )


@app.route("/api/lantai")
@login_required
def api_lantai():
    gedung = request.args.get("gedung", "")
    if not gedung:
        return jsonify([])
    hasil = (
        db.session.query(Aset.lantai)
        .filter(Aset.gedung == gedung, Aset.lantai.isnot(None), Aset.lantai != "")
        .distinct()
        .order_by(Aset.lantai)
        .all()
    )
    return jsonify([r[0] for r in hasil])


@app.route("/api/ruangan")
@login_required
def api_ruangan():
    gedung = request.args.get("gedung", "")
    lantai = request.args.get("lantai", "")
    if not gedung:
        return jsonify([])
    filters = [Aset.gedung == gedung, Aset.ruangan.isnot(None), Aset.ruangan != ""]
    if lantai:
        filters.append(Aset.lantai == lantai)
    hasil = (
        db.session.query(Aset.ruangan)
        .filter(*filters)
        .distinct()
        .order_by(Aset.ruangan)
        .all()
    )
    return jsonify([r[0] for r in hasil])


@app.route("/api/aset-by-lokasi")
@login_required
def api_aset_by_lokasi():
    gedung = request.args.get("gedung", "")
    lantai = request.args.get("lantai", "")
    ruangan = request.args.get("ruangan", "")
    if not gedung:
        return jsonify([])
    filters = [Aset.gedung == gedung]
    if lantai:
        filters.append(Aset.lantai == lantai)
    if ruangan:
        filters.append(Aset.ruangan == ruangan)
    hasil = Aset.query.filter(*filters).all()
    return jsonify([{"id": a.id, "kode": a.kode_aset, "nama": a.nama} for a in hasil])


@app.route("/aset/create", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def aset_create():
    kode_aset = request.form.get("kode_aset", "").strip()
    if Aset.query.filter_by(kode_aset=kode_aset).first():
        flash("Kode aset sudah digunakan.", "danger")
        return redirect(url_for("aset_list"))

    # Ambil semua field
    area = request.form.get("area", "").strip() or None
    nama = request.form.get("nama", "").strip()
    fungsi = request.form.get("fungsi", "").strip() or None
    jenis_barang = request.form.get("jenis_barang", "").strip()  # nama kategori
    merek = request.form.get("merek", "").strip() or None
    serial_number = request.form.get("serial_number", "").strip() or None
    spesifikasi = request.form.get("spesifikasi", "").strip() or None
    tipe_aset = request.form.get("tipe_aset", "OPEX").strip()
    volume = request.form.get("volume", "").strip() or None
    satuan = request.form.get("satuan", "").strip() or None
    status_aset = request.form.get("status_aset", "Baik")
    gedung = request.form.get("gedung", "").strip()
    ruangan = request.form.get("ruangan", "").strip()
    lantai = request.form.get("lantai", "").strip() or None
    link_qr = request.form.get("link_qr", "").strip() or None
    tanggal_datang_str = request.form.get("tanggal_datang", "").strip()
    tanggal_datang = None
    if tanggal_datang_str:
        try:
            tanggal_datang = datetime.strptime(tanggal_datang_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    keterangan = request.form.get("keterangan", "").strip() or None

    # Cari/buat kategori
    id_kategori = None
    if jenis_barang:
        kategori = Kategori.query.filter(db.func.lower(Kategori.nama) == jenis_barang.lower()).first()
        if not kategori:
            kategori = Kategori(nama=jenis_barang)
            db.session.add(kategori)
            db.session.flush()
        id_kategori = kategori.id

    # Upload foto
    foto_file = request.files.get("foto")
    foto = None
    foto_error = None
    if foto_file and foto_file.filename:
        foto, foto_error = save_upload(foto_file, prefix="aset_")

    foto_url_raw = request.form.get("foto_url", "").strip()
    foto_url = convert_gdrive_to_thumbnail(foto_url_raw) if foto_url_raw else None

    aset = Aset(
        kode_aset=kode_aset,
        nama=nama,
        area=area,
        fungsi=fungsi,
        merek=merek,
        serial_number=serial_number,
        spesifikasi=spesifikasi,
        tipe_aset=tipe_aset,
        volume=volume,
        satuan=satuan,
        status_aset=status_aset,
        gedung=gedung,
        ruangan=ruangan,
        lantai=lantai,
        foto=foto,
        foto_url=foto_url,
        link_qr=link_qr,
        tanggal_datang=tanggal_datang,
        keterangan=keterangan,
        id_kategori=id_kategori,
    )
    db.session.add(aset)
    catat_aktivitas(
        aksi="CREATE",
        target_model="Aset",
        target_id=aset.id,
        deskripsi=f"Menambahkan aset baru: {aset.nama} ({aset.kode_aset})",
        data_baru={
            "kode_aset": aset.kode_aset,
            "nama": aset.nama,
            "area": aset.area,
            "fungsi": aset.fungsi,
            "merek": aset.merek,
            "serial_number": aset.serial_number,
            "spesifikasi": aset.spesifikasi,
            "tipe_aset": aset.tipe_aset,
            "volume": aset.volume,
            "satuan": aset.satuan,
            "status": aset.status_aset,
            "gedung": aset.gedung,
            "ruangan": aset.ruangan,
            "lantai": aset.lantai,
        }
    )
    db.session.commit()
    
    if foto_error:
        flash(f"Aset berhasil ditambahkan, tetapi foto gagal diupload: {foto_error}", "warning")
    else:
        flash("Aset berhasil ditambahkan.", "success")
    return redirect(url_for("aset_list"))


@app.route("/aset/<int:aset_id>/edit", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def aset_edit(aset_id):
    aset = Aset.query.get_or_404(aset_id)

    # Simpan data lama
    data_lama = {
        "nama": aset.nama,
        "area": aset.area,
        "fungsi": aset.fungsi,
        "merek": aset.merek,
        "serial_number": aset.serial_number,
        "spesifikasi": aset.spesifikasi,
        "tipe_aset": aset.tipe_aset,
        "volume": aset.volume,
        "satuan": aset.satuan,
        "status": aset.status_aset,
        "gedung": aset.gedung,
        "ruangan": aset.ruangan,
        "lantai": aset.lantai,
        "keterangan": aset.keterangan,
    }

    # Ambil data baru
    aset.nama = request.form.get("nama", "").strip()
    aset.area = request.form.get("area", "").strip() or None
    aset.fungsi = request.form.get("fungsi", "").strip() or None
    aset.merek = request.form.get("merek", "").strip() or None
    aset.serial_number = request.form.get("serial_number", "").strip() or None
    aset.spesifikasi = request.form.get("spesifikasi", "").strip() or None
    aset.tipe_aset = request.form.get("tipe_aset", "OPEX").strip()
    aset.volume = request.form.get("volume", "").strip() or None
    aset.satuan = request.form.get("satuan", "").strip() or None
    aset.status_aset = request.form.get("status_aset", aset.status_aset)
    aset.gedung = request.form.get("gedung", "").strip()
    aset.ruangan = request.form.get("ruangan", "").strip()
    aset.lantai = request.form.get("lantai", "").strip() or None
    aset.keterangan = request.form.get("keterangan", "").strip() or None

    # Link QR (tetap disimpan, tidak ditampilkan di UI)
    aset.link_qr = request.form.get("link_qr", "").strip() or None

    # Tanggal datang
    tanggal_datang_str = request.form.get("tanggal_datang", "").strip()
    if tanggal_datang_str:
        try:
            aset.tanggal_datang = datetime.strptime(tanggal_datang_str, "%Y-%m-%d").date()
        except ValueError:
            aset.tanggal_datang = None
    else:
        aset.tanggal_datang = None

    # Kategori (jenis_barang)
    jenis_barang = request.form.get("jenis_barang", "").strip()
    id_kategori = None
    if jenis_barang:
        kategori = Kategori.query.filter(db.func.lower(Kategori.nama) == jenis_barang.lower()).first()
        if not kategori:
            kategori = Kategori(nama=jenis_barang)
            db.session.add(kategori)
            db.session.flush()
        id_kategori = kategori.id
    aset.id_kategori = id_kategori

    # Foto
    foto_url_raw = request.form.get("foto_url", "").strip()
    if foto_url_raw:
        aset.foto_url = convert_gdrive_to_thumbnail(foto_url_raw)
    elif foto_url_raw == "" and request.form.get("hapus_foto"):
        aset.foto_url = None

    foto_file = request.files.get("foto")
    foto_error = None
    if foto_file and foto_file.filename:
        foto, foto_error = save_upload(foto_file, prefix="aset_")
        if foto:
            aset.foto = foto

    # Log aktivitas
    data_baru = {
        "nama": aset.nama,
        "area": aset.area,
        "fungsi": aset.fungsi,
        "merek": aset.merek,
        "serial_number": aset.serial_number,
        "spesifikasi": aset.spesifikasi,
        "tipe_aset": aset.tipe_aset,
        "volume": aset.volume,
        "satuan": aset.satuan,
        "status": aset.status_aset,
        "gedung": aset.gedung,
        "ruangan": aset.ruangan,
        "lantai": aset.lantai,
        "keterangan": aset.keterangan,
    }
    if data_lama != data_baru:
        catat_aktivitas(
            aksi="UPDATE",
            target_model="Aset",
            target_id=aset.id,
            deskripsi=f"Mengupdate aset: {aset.nama} ({aset.kode_aset})",
            data_lama=data_lama,
            data_baru=data_baru
        )

    db.session.commit()
    
    if foto_error:
        flash(f"Aset berhasil diperbarui, tetapi foto gagal diupload: {foto_error}", "warning")
    else:
        flash("Aset berhasil diperbarui.", "success")
    return redirect(url_for("aset_list"))


@app.route("/aset/<int:aset_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def aset_delete(aset_id):
    aset = Aset.query.get_or_404(aset_id)
    
    data_lama = {
        "kode_aset": aset.kode_aset,
        "nama": aset.nama,
        "area": aset.area,
        "fungsi": aset.fungsi,
        "merek": aset.merek,
        "serial_number": aset.serial_number,
        "spesifikasi": aset.spesifikasi,
        "tipe_aset": aset.tipe_aset,
        "volume": aset.volume,
        "satuan": aset.satuan,
        "status": aset.status_aset,
        "gedung": aset.gedung,
        "ruangan": aset.ruangan,
        "lantai": aset.lantai,
        "keterangan": aset.keterangan,
    }
    
    catat_aktivitas(
        aksi="DELETE",
        target_model="Aset",
        target_id=aset.id,
        deskripsi=f"Menghapus aset: {aset.nama} ({aset.kode_aset})",
        data_lama=data_lama,
        data_baru=None
    )
    
    db.session.delete(aset)
    db.session.commit()
    flash("Aset berhasil dihapus.", "success")
    return redirect(url_for("aset_list"))

@app.route("/aset/<int:aset_id>/detail")
@login_required
def aset_detail(aset_id):
    aset = Aset.query.get_or_404(aset_id)
    histori = HistoriAset.query.filter_by(id_aset=aset_id).order_by(HistoriAset.tanggal.desc()).all()
    histori_data = []
    for h in histori:
        histori_data.append({
            "jenis": h.jenis_event,
            "gedung": h.gedung or "",
            "lantai": h.lantai or "",
            "ruangan": h.ruangan or "",
            "gedung_asal": h.gedung_asal or "",
            "lantai_asal": h.lantai_asal or "",
            "ruangan_asal": h.ruangan_asal or "",
            "tanggal": h.tanggal.strftime("%d-%m-%Y %H:%M"),
            "id_tiket": h.id_tiket
        })
    
    foto_display = None
    if aset.foto_url:
        foto_display = aset.foto_url
    elif aset.foto:
        foto_display = aset.foto
    
    data = {
        "id": aset.id,
        "kode_aset": aset.kode_aset,
        "nama": aset.nama,
        "area": aset.area or "",
        "fungsi": aset.fungsi or "",
        "merek": aset.merek or "",
        "serial_number": aset.serial_number or "",
        "spesifikasi": aset.spesifikasi or "",
        "tipe_aset": aset.tipe_aset,
        "volume": aset.volume or "",
        "satuan": aset.satuan or "",
        "status_aset": aset.status_aset,
        "gedung": aset.gedung,
        "lantai": aset.lantai or "",
        "ruangan": aset.ruangan,
        "kategori": aset.kategori_ref.nama if aset.kategori_ref else "-",
        "foto": foto_display,
        "total_kerusakan": aset.total_kerusakan or 0,
        "tanggal_datang": aset.tanggal_datang.strftime("%d-%m-%Y") if aset.tanggal_datang else "",
        "keterangan": aset.keterangan or "",
        "histori": histori_data
        # link_qr TIDAK dikirim (di-hide)
    }
    return jsonify(data)

@app.route("/aset/<int:aset_id>/histori")
@login_required
def aset_histori(aset_id):
    aset = Aset.query.get_or_404(aset_id)
    histori = HistoriAset.query.filter_by(id_aset=aset_id).order_by(HistoriAset.tanggal.desc()).all()
    data = []
    for h in histori:
        data.append({
            "jenis": h.jenis_event,
            "gedung": h.gedung or "",
            "lantai": h.lantai or "",
            "ruangan": h.ruangan or "",
            "tanggal": h.tanggal.strftime("%d-%m-%Y %H:%M"),
            "id_tiket": h.id_tiket
        })
    return jsonify(data)


# ---------------------------------------------------------------------------
# EXPORT / IMPORT ASET (Excel)
# ---------------------------------------------------------------------------
EXPORT_HEADERS = [
    "area", "kode_aset", "nama", "fungsi", "jenis_barang", 
    "merek", "serial_number", "spesifikasi", "tipe_aset", 
    "volume", "satuan", "status_aset", "gedung", "ruangan", 
    "lantai", "foto_url", "nama_project", "harga_perolehan", 
    "tanggal_bast", "evidence_bast", "mitra", "link_qr", 
    "tanggal_datang", "keterangan"
]


@app.route("/aset/export")
@login_required
@role_required(ROLE_ADMIN)
def aset_export():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Aset"
    ws.append(EXPORT_HEADERS)

    for aset in Aset.query.order_by(Aset.id).all():
        ws.append([
            aset.kode_aset,
            aset.nama,
            aset.merek or "",
            aset.gedung,
            aset.lantai or "",
            aset.ruangan,
            aset.status_aset,
            aset.jenis_aset,
            aset.kategori.nama if aset.kategori else "",
            aset.sub_kategori.nama if aset.sub_kategori else "",
        ])

    for i in range(1, len(EXPORT_HEADERS) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nama_file = f"data_aset_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=nama_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/aset/import", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def aset_import():
    file = request.files.get("file_import")
    if not file or file.filename == "":
        flash("Pilih file Excel (.xlsx) terlebih dahulu.", "danger")
        return redirect(url_for("aset_list"))
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        flash("Format file harus .xlsx.", "danger")
        return redirect(url_for("aset_list"))

    try:
        wb = openpyxl.load_workbook(file.stream, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
    except Exception:
        flash("File Excel tidak valid atau rusak.", "danger")
        return redirect(url_for("aset_list"))

    ditambahkan, diperbarui, dilewati = 0, 0, 0
    error_baris = []

    # Header yang diharapkan (24 kolom)
    # area, kode_aset, nama, fungsi, jenis_barang, merek, serial_number, spesifikasi,
    # tipe_aset, volume, satuan, status_aset, gedung, ruangan, lantai, foto_url,
    # nama_project, harga_perolehan, tanggal_bast, evidence_bast, mitra, link_qr,
    # tanggal_datang, keterangan

    for i, row in enumerate(rows, start=2):
        if not row or not any(row):
            continue

        # Ambil 24 kolom, sisanya diabaikan
        cols = [str(c).strip() if c is not None else "" for c in row]
        cols += [""] * (24 - len(cols))
        cols = cols[:24]

        (area, kode_aset, nama, fungsi, jenis_barang, merek, serial_number,
         spesifikasi, tipe_aset, volume, satuan, status_aset, gedung, ruangan,
         lantai, foto_url, nama_project, harga_perolehan, tanggal_bast,
         evidence_bast, mitra, link_qr, tanggal_datang_str, keterangan) = cols

        kode_aset = kode_aset.strip()
        nama = nama.strip()
        if not kode_aset or not nama:
            dilewati += 1
            error_baris.append(f"Baris {i}: kode_aset atau nama kosong")
            continue

        # Cari/buat Kategori dari "jenis_barang"
        id_kategori = None
        if jenis_barang:
            kategori = Kategori.query.filter(db.func.lower(Kategori.nama) == jenis_barang.lower()).first()
            if not kategori:
                kategori = Kategori(nama=jenis_barang)
                db.session.add(kategori)
                db.session.flush()
            id_kategori = kategori.id

        # Parse tanggal datang
        tanggal_datang = None
        if tanggal_datang_str:
            try:
                tanggal_datang = datetime.strptime(tanggal_datang_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    tanggal_datang = datetime.strptime(tanggal_datang_str, "%d/%m/%Y").date()
                except ValueError:
                    pass

        # Status valid
        status_valid = status_aset if status_aset in ("Baik", "Rusak", "Dipindahkan") else "Baik"
        tipe_valid = tipe_aset if tipe_aset in ("CAPEX", "OPEX") else "OPEX"

        # Cek apakah aset sudah ada
        aset = Aset.query.filter_by(kode_aset=kode_aset).first()

        if aset:
            aset.area = area or None
            aset.nama = nama
            aset.fungsi = fungsi or None
            aset.merek = merek or None
            aset.serial_number = serial_number or None
            aset.spesifikasi = spesifikasi or None
            aset.tipe_aset = tipe_valid
            aset.volume = volume or None
            aset.satuan = satuan or None
            aset.status_aset = status_valid
            aset.gedung = gedung or "-"
            aset.ruangan = ruangan or "-"
            aset.lantai = lantai or None
            aset.foto_url = convert_gdrive_to_thumbnail(foto_url) if foto_url else None
            aset.link_qr = link_qr or None
            aset.tanggal_datang = tanggal_datang
            aset.keterangan = keterangan or None
            aset.id_kategori = id_kategori
            diperbarui += 1
        else:
            db.session.add(Aset(
                kode_aset=kode_aset,
                nama=nama,
                area=area or None,
                fungsi=fungsi or None,
                merek=merek or None,
                serial_number=serial_number or None,
                spesifikasi=spesifikasi or None,
                tipe_aset=tipe_valid,
                volume=volume or None,
                satuan=satuan or None,
                status_aset=status_valid,
                gedung=gedung or "-",
                ruangan=ruangan or "-",
                lantai=lantai or None,
                foto_url=convert_gdrive_to_thumbnail(foto_url) if foto_url else None,
                link_qr=link_qr or None,
                tanggal_datang=tanggal_datang,
                keterangan=keterangan or None,
                id_kategori=id_kategori,
            ))
            ditambahkan += 1

    db.session.commit()

    pesan = f"Import selesai: {ditambahkan} aset baru ditambahkan, {diperbarui} aset diperbarui."
    if dilewati:
        pesan += f" {dilewati} baris dilewati karena data tidak lengkap."
    flash(pesan, "warning" if dilewati else "success")
    if error_baris:
        flash(" | ".join(error_baris[:5]), "warning")

    return redirect(url_for("aset_list"))


# ---------------------------------------------------------------------------
# KATEGORI & SUB KATEGORI
# ---------------------------------------------------------------------------
@app.route("/kategori")
@login_required
@role_required(ROLE_ADMIN)
def kategori_list():
    kategori_all = Kategori.query.all()
    return render_template("kategori/list.html", kategori_all=kategori_all)


@app.route("/kategori/create", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def kategori_create():
    db.session.add(Kategori(nama=request.form.get("nama")))
    db.session.commit()
    flash("Kategori ditambahkan.", "success")
    return redirect(url_for("kategori_list"))

# ---------------------------------------------------------------------------
# HISTORY (TIKET READ-ONLY)
# ---------------------------------------------------------------------------
@app.route("/history")
@login_required
def history_list():
    """Halaman history terpadu: tiket + aktivitas admin."""
    
    # Ambil semua tiket
    tiket_all = Tiket.query.all()
    # Ambil semua aktivitas log
    aktivitas_all = AktivitasLog.query.all()

    # Buat list event
    events = []
    
    # === TAMBAHKAN TIKET (hanya 1 entri per tiket) ===
    for t in tiket_all:
        creator_name = "System"
        if t.created_by:
            creator = User.query.get(t.created_by)
            if creator:
                creator_name = creator.name
        elif t.log_status:
            first_log = t.log_status[0]
            if first_log.user_pengubah:
                creator_name = first_log.user_pengubah.name

        aset_list = ", ".join([ta.aset.nama for ta in t.aset_terkait[:3]])
        if len(t.aset_terkait) > 3:
            aset_list += f" dan {len(t.aset_terkait)-3} lainnya"

        events.append({
            "id": t.id,
            "waktu": t.created_at,
            "pelaku": creator_name,
            "jenis": "Tiket",
            "aksi": t.jenis_tiket,  # "Pemindahan" atau "Kerusakan"
            "detail": f"{t.nama_pemohon} - {aset_list or 'Tidak ada aset'}",
            "link": url_for("history_detail", tiket_id=t.id),
            "warna": "bg-rose-100 text-rose-700 border-rose-200" if t.jenis_tiket == "Kerusakan" else "bg-blue-100 text-blue-700 border-blue-200"
        })

    # === TAMBAHKAN AKTIVITAS ADMIN ===
    for a in aktivitas_all:
        user = User.query.get(a.id_user)
        pelaku = user.name if user else "Unknown"
        
        label_aksi = {
            "CREATE": "Tambah Aset",
            "UPDATE": "Edit Aset",
            "DELETE": "Hapus Aset",
            "MOVE": "Pemindahan Aset"
        }.get(a.aksi, a.aksi)

        events.append({
            "id": a.id,
            "waktu": a.created_at,
            "pelaku": pelaku,
            "jenis": "Aktivitas",
            "aksi": label_aksi,
            "detail": a.deskripsi or f"{label_aksi} ID {a.target_id}",
            "link": url_for("aktivitas_detail", log_id=a.id),  # <-- route baru
            "warna": "bg-indigo-100 text-indigo-700 border-indigo-200" if a.aksi == "CREATE" else "bg-amber-100 text-amber-700 border-amber-200" if a.aksi == "UPDATE" else "bg-rose-100 text-rose-700 border-rose-200" if a.aksi == "DELETE" else "bg-emerald-100 text-emerald-700 border-emerald-200",
            "data_lama": a.data_lama,
            "data_baru": a.data_baru
        })

    # Urutkan berdasarkan waktu terbaru
    events.sort(key=lambda x: x["waktu"], reverse=True)

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 10
    total = len(events)
    start = (page - 1) * per_page
    end = start + per_page
    events_page = events[start:end]
    total_pages = (total + per_page - 1) // per_page

    class PaginationDummy:
        def __init__(self, items, page, per_page, total, total_pages):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = total_pages
            self.has_prev = page > 1
            self.has_next = page < total_pages
            self.prev_num = page - 1 if page > 1 else None
            self.next_num = page + 1 if page < total_pages else None

    pagination = PaginationDummy(events_page, page, per_page, total, total_pages)
    daftar_history = events_page

    gedung_all = [
        g[0] for g in db.session.query(Aset.gedung).distinct().order_by(Aset.gedung).all() if g[0]
    ]

    return render_template(
        "history/list.html",
        daftar_history=daftar_history,
        pagination=pagination,
        gedung_all=gedung_all,
    )

@app.route("/aktivitas/<int:log_id>")
@login_required
def aktivitas_detail(log_id):
    """Detail aktivitas admin (tambah/edit/hapus aset)."""
    log = AktivitasLog.query.get_or_404(log_id)
    
    # Ambil nama aksi
    label_aksi = {
        "CREATE": "Tambah Aset",
        "UPDATE": "Edit Aset", 
        "DELETE": "Hapus Aset",
        "MOVE": "Pemindahan Aset"
    }.get(log.aksi, log.aksi)
    
    user = User.query.get(log.id_user)
    pelaku = user.name if user else "Unknown"
    
    return render_template(
        "history/aktivitas_detail.html",
        log=log,
        label_aksi=label_aksi,
        pelaku=pelaku
    )

@app.route("/history/<int:tiket_id>")
@login_required
def history_detail(tiket_id):
    """Detail history tiket (read-only)"""
    tiket = Tiket.query.get_or_404(tiket_id)
    return render_template("history/detail.html", tiket=tiket)

@app.route("/tiket/create/pemindahan", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_create_pemindahan():
    """Buat tiket pemindahan (langsung selesai)."""
    aset_ids = request.form.getlist("aset_ids[]")
    if not aset_ids:
        flash("Pilih minimal 1 aset.", "danger")
        return redirect(url_for("history_list"))

    gedung_asal = request.form.get("gedung_asal", "").strip()
    lantai_asal = request.form.get("lantai_asal", "").strip()
    ruangan_asal = request.form.get("ruangan_asal", "").strip()
    gedung_tujuan = request.form.get("gedung_tujuan", "").strip()
    lantai_tujuan = request.form.get("lantai_tujuan", "").strip()
    ruangan_tujuan = request.form.get("ruangan_tujuan", "").strip()
    nama_pemohon = request.form.get("nama_pemohon", "").strip()
    catatan = request.form.get("catatan", "").strip()

    foto, foto_error = save_upload(request.files.get("foto"), prefix="tiket_")

    tiket = Tiket(
        jenis_tiket="Pemindahan",
        nama_pemohon=nama_pemohon,
        gedung_asal=gedung_asal,
        lantai_asal=lantai_asal,
        ruangan_asal=ruangan_asal,
        gedung_tujuan=gedung_tujuan,
        lantai_tujuan=lantai_tujuan,
        ruangan_tujuan=ruangan_tujuan,
        catatan=catatan,
        foto=foto,
        created_by=current_user.id,
    )
    db.session.add(tiket)
    db.session.flush()

    for aid in aset_ids:
        aset = db.session.get(Aset, int(aid))
        if aset:
            # Simpan data lama
            data_lama = {
                "gedung": aset.gedung,
                "lantai": aset.lantai,
                "ruangan": aset.ruangan
            }

            # Catat histori pindah
            histori = HistoriAset(
                id_aset=aset.id,
                jenis_event="pindah",
                gedung=gedung_tujuan,
                lantai=lantai_tujuan,
                ruangan=ruangan_tujuan,
                gedung_asal=aset.gedung,
                lantai_asal=aset.lantai,
                ruangan_asal=aset.ruangan,
                id_tiket=tiket.id
            )
            db.session.add(histori)

            # Update lokasi aset
            aset.gedung = gedung_tujuan
            aset.lantai = lantai_tujuan or None
            aset.ruangan = ruangan_tujuan
            aset.status_aset = "Baik"

            # Catat log status (untuk tiket)
            db.session.add(LogStatus(
                id_tiket=tiket.id,
                status_lama=None,
                status_baru="Selesai",
                id_user_pengubah=current_user.id
            ))

            # Catat aktivitas admin
            catat_aktivitas(
                aksi="MOVE",
                target_model="Aset",
                target_id=aset.id,
                deskripsi=f"Memindahkan aset {aset.nama} dari {data_lama['gedung']} / {data_lama['ruangan']} ke {gedung_tujuan} / {ruangan_tujuan}",
                data_lama=data_lama,
                data_baru={
                    "gedung": aset.gedung,
                    "lantai": aset.lantai,
                    "ruangan": aset.ruangan
                }
            )

            db.session.add(TiketAset(id_tiket=tiket.id, id_aset=aset.id))

    db.session.commit()

    if foto_error:
        flash(f"Pemindahan berhasil, tetapi foto gagal diupload: {foto_error}", "warning")
    else:
        flash(f"Pemindahan berhasil. {len(aset_ids)} aset dipindahkan.", "success")
    return redirect(url_for("history_list"))

@app.route("/tiket/create/kerusakan", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_create_kerusakan():
    """Buat tiket kerusakan (hanya kerusakan, langsung selesai)."""
    aset_ids = request.form.getlist("aset_ids[]")
    if not aset_ids:
        flash("Pilih minimal 1 aset.", "danger")
        return redirect(url_for("history_list"))

    gedung_asal = request.form.get("gedung_asal", "").strip()
    lantai_asal = request.form.get("lantai_asal", "").strip()
    ruangan_asal = request.form.get("ruangan_asal", "").strip()
    nama_pemohon = request.form.get("nama_pemohon", "").strip()
    catatan = request.form.get("catatan", "").strip()

    foto = save_upload(request.files.get("foto"), prefix="tiket_")[0]

    tiket = Tiket(
        jenis_tiket="Kerusakan",
        nama_pemohon=nama_pemohon,
        gedung_asal=gedung_asal,
        lantai_asal=lantai_asal,
        ruangan_asal=ruangan_asal,
        catatan=catatan,
        foto=foto,
        status_tiket="Selesai",  # Langsung selesai, tidak ada alur
    )
    db.session.add(tiket)
    db.session.flush()

    for aid in aset_ids:
        aset = db.session.get(Aset, int(aid))
        if aset:
            # Update status aset menjadi Rusak
            aset.status_aset = "Rusak"
            aset.total_kerusakan = (aset.total_kerusakan or 0) + 1
            
            # Catat histori rusak
            histori = HistoriAset(
                id_aset=aset.id,
                jenis_event="rusak",
                gedung=aset.gedung,
                lantai=aset.lantai,
                ruangan=aset.ruangan,
                id_tiket=tiket.id
            )
            db.session.add(histori)
            
            db.session.add(TiketAset(id_tiket=tiket.id, id_aset=aset.id))

    catat_log(tiket, None, "Selesai")
    db.session.commit()
    flash(f"Laporan kerusakan berhasil dibuat. {len(aset_ids)} aset ditandai rusak.", "success")
    return redirect(url_for("history_list"))


# ---------------------------------------------------------------------------
# USERS (Admin only)
# ---------------------------------------------------------------------------
@app.route("/users")
@login_required
@role_required(ROLE_ADMIN)
def users_list():
    daftar_user = User.query.all()
    return render_template("users/list.html", daftar_user=daftar_user)


@app.route("/users/create", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def users_create():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role")

    if User.query.filter_by(email=email).first():
        flash("Email sudah terdaftar.", "danger")
        return redirect(url_for("users_list"))
    if len(password) < 8:
        flash("Password minimal 8 karakter.", "danger")
        return redirect(url_for("users_list"))
    if role != "admin":
        flash("Role tidak valid.", "danger")
        return redirect(url_for("users_list"))

    db.session.add(User(
        name=request.form.get("name"),
        email=email,
        password=generate_password_hash(password),
        role="admin",
    ))
    db.session.commit()
    flash("User berhasil ditambahkan.", "success")
    return redirect(url_for("users_list"))


@app.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def users_toggle(user_id):
    if user_id == current_user.id:
        flash("Tidak bisa menonaktifkan akun sendiri.", "danger")
        return redirect(url_for("users_list"))
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(
        f"User {'diaktifkan kembali' if user.is_active else 'dinonaktifkan'}.",
        "success",
    )
    return redirect(url_for("users_list"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)