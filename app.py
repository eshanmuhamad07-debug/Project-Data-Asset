import os
import io
from functools import wraps
from datetime import datetime
import logging
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

from extensions import db, login_manager, csrf, limiter
from models import (
    User, Kategori, SubKategori, Aset, Tiket, TiketAset,
    LogStatus, HistoriAset
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

logging.basicConfig(level=logging.DEBUG)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def is_valid_image(file_storage):
    """Solusi #5: pastikan file BENAR-BENAR gambar, bukan cuma nama
    berekstensi gambar (mis. file .exe yang diganti nama jadi .jpg)."""
    try:
        pos = file_storage.stream.tell()
        Image.open(file_storage.stream).verify()
        file_storage.stream.seek(pos)
        return True
    except Exception as e:
        logging.debug(f"is_valid_image: Error verifying image: {e}")
        return False


def save_upload(file_storage, prefix=""):
    """Simpan file upload ke static/uploads, return (filename, error).
    - (filename, None) jika berhasil
    - (None, error_message) jika gagal
    """
    if not file_storage or file_storage.filename == "":
        return None, None  # Tidak ada file, bukan error
    
    if not allowed_file(file_storage.filename):
        return None, f"Ekstensi file tidak diizinkan. Gunakan: {', '.join(ALLOWED_EXT)}"
    
    if not is_valid_image(file_storage):
        return None, "File yang diupload bukan gambar yang valid (rusak atau tidak sesuai format)."
    
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None, "Nama file tidak valid."
    
    unique_name = f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    
    try:
        file_storage.save(filepath)
        return unique_name, None
    except Exception as e:
        return None, f"Gagal menyimpan file: {str(e)}"

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
    total_pending = Tiket.query.filter_by(status_tiket="Pending").count()
    total_selesai = Tiket.query.filter_by(status_tiket="Selesai").count()

    kategori_chart = (
        db.session.query(Kategori.nama, db.func.count(Aset.id))
        .outerjoin(Aset, Aset.id_kategori == Kategori.id)
        .group_by(Kategori.id)
        .all()
    )
    chart_labels = [k[0] for k in kategori_chart]
    chart_values = [k[1] for k in kategori_chart]

    tiket_terbaru = Tiket.query.order_by(Tiket.created_at.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        total_aset=total_aset,
        total_pending=total_pending,
        total_selesai=total_selesai,
        chart_labels=chart_labels,
        chart_values=chart_values,
        tiket_terbaru=tiket_terbaru,
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
    sub_id = request.args.get("sub_kategori", "")
    gedung = request.args.get("gedung", "")
    lantai = request.args.get("lantai", "")
    ruangan = request.args.get("ruangan", "")
    jenis = request.args.get("jenis", "")

    query = Aset.query
    if q:
        query = query.filter(
            db.or_(Aset.nama.ilike(f"%{q}%"), Aset.kode_aset.ilike(f"%{q}%"))
        )
    if status:
        query = query.filter_by(status_aset=status)
    if kategori_id:
        query = query.filter_by(id_kategori=kategori_id)
    if sub_id:
        query = query.filter_by(id_sub_kategori=sub_id)
    if gedung:
        query = query.filter_by(gedung=gedung)
    if lantai:
        query = query.filter_by(lantai=lantai)
    if ruangan:
        query = query.filter_by(ruangan=ruangan)
    if jenis:
        query = query.filter_by(jenis_aset=jenis)

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Aset.id.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    daftar_aset = pagination.items
    kategori_all = Kategori.query.all()
    sub_kategori_terpilih = SubKategori.query.get(sub_id) if sub_id else None
    gedung_all = [
        g[0] for g in db.session.query(Aset.gedung).distinct().order_by(Aset.gedung).all() if g[0]
    ]
    return render_template(
        "aset/list.html",
        daftar_aset=daftar_aset,
        kategori_all=kategori_all,
        pagination=pagination,
        sub_kategori_terpilih=sub_kategori_terpilih,
        gedung_all=gedung_all,
        jenis_aset_options=JENIS_ASET_OPTIONS,
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
    """Ambil daftar aset berdasarkan gedung, lantai, ruangan."""
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

    jenis_aset = request.form.get("jenis_aset", "Operasional")
    if jenis_aset not in JENIS_ASET_OPTIONS:
        jenis_aset = "Operasional"

    # Upload foto jika ada
    foto_file = request.files.get("foto")
    foto = None
    foto_error = None
    
    if foto_file and foto_file.filename:
        foto, foto_error = save_upload(foto_file, prefix="aset_")
    
    # Ambil foto_url jika diisi
    foto_url = request.form.get("foto_url", "").strip() or None

    aset = Aset(
        kode_aset=kode_aset,
        nama=request.form.get("nama"),
        foto=foto,
        foto_url=foto_url,
        gedung=request.form.get("gedung"),
        lantai=request.form.get("lantai") or None,
        ruangan=request.form.get("ruangan"),
        status_aset=request.form.get("status_aset", "Baik"),
        jenis_aset=jenis_aset,
        spesifikasi=request.form.get("spesifikasi", "").strip() or None,
        id_kategori=request.form.get("id_kategori") or None,
        id_sub_kategori=request.form.get("id_sub_kategori") or None,
    )
    db.session.add(aset)
    db.session.commit()
    
    # Flash message
    if foto_error:
        flash(f"Aset berhasil ditambahkan, tetapi foto gagal diupload: {foto_error}", "warning")
    else:
        flash("Aset berhasil ditambahkan.", "success")
    
    return redirect(url_for("aset_list"))

@app.route("/aset/<int:aset_id>/detail")
@login_required
def aset_detail(aset_id):
    """API untuk mengambil detail aset + histori (dipakai modal detail)."""
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
    
    # Tentukan foto mana yang akan ditampilkan (prioritas: foto_url > foto)
    foto_display = aset.foto_url or aset.foto
    
    data = {
        "id": aset.id,
        "kode_aset": aset.kode_aset,
        "nama": aset.nama,
        "jenis_aset": aset.jenis_aset,
        "status_aset": aset.status_aset,
        "gedung": aset.gedung,
        "lantai": aset.lantai or "",
        "ruangan": aset.ruangan,
        "kategori": aset.kategori.nama if aset.kategori else "-",
        "sub_kategori": aset.sub_kategori.nama if aset.sub_kategori else "-",
        "foto": foto_display,  # kirim foto yang akan ditampilkan
        "foto_file": aset.foto,      # file upload
        "foto_url": aset.foto_url,   # link URL
        "total_kerusakan": aset.total_kerusakan or 0,
        "spesifikasi": aset.spesifikasi or "-",
        "histori": histori_data
    }
    return jsonify(data)

@app.route("/aset/<int:aset_id>/edit", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def aset_edit(aset_id):
    aset = Aset.query.get_or_404(aset_id)
    aset.nama = request.form.get("nama")
    aset.gedung = request.form.get("gedung")
    aset.lantai = request.form.get("lantai") or None
    aset.ruangan = request.form.get("ruangan")
    aset.status_aset = request.form.get("status_aset", aset.status_aset)
    aset.spesifikasi = request.form.get("spesifikasi", "").strip() or None
    
    # Update foto_url jika diisi
    foto_url = request.form.get("foto_url", "").strip()
    if foto_url:
        aset.foto_url = foto_url
    elif foto_url == "" and request.form.get("hapus_foto"):
        aset.foto_url = None
    
    jenis_aset = request.form.get("jenis_aset", aset.jenis_aset)
    aset.jenis_aset = jenis_aset if jenis_aset in JENIS_ASET_OPTIONS else aset.jenis_aset
    aset.id_kategori = request.form.get("id_kategori") or None
    aset.id_sub_kategori = request.form.get("id_sub_kategori") or None

    # Upload foto baru jika ada
    foto_file = request.files.get("foto")
    foto_error = None
    
    if foto_file and foto_file.filename:
        foto, foto_error = save_upload(foto_file, prefix="aset_")
        if foto:
            aset.foto = foto

    db.session.commit()
    
    # Flash message
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
    db.session.delete(aset)
    db.session.commit()
    flash("Aset berhasil dihapus.", "success")
    return redirect(url_for("aset_list"))


@app.route("/aset/<int:aset_id>/histori")
@login_required
def aset_histori(aset_id):
    """API untuk mengambil histori aset tertentu."""
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
EXPORT_HEADERS = ["kode_aset", "nama", "gedung", "lantai", "ruangan", "status_aset", "jenis_aset", "kategori", "sub_kategori"]


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
        flash("Format file harus .xlsx (gunakan hasil export dari aplikasi ini).", "danger")
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

    for i, row in enumerate(rows, start=2):
        if not row or not any(row):
            continue

        kolom = (list(row) + [None] * len(EXPORT_HEADERS))[: len(EXPORT_HEADERS)]
        kode_aset, nama, gedung, lantai, ruangan, status_aset, jenis_aset, nama_kategori, nama_sub = kolom

        kode_aset = str(kode_aset).strip() if kode_aset else ""
        nama = str(nama).strip() if nama else ""
        if not kode_aset or not nama:
            dilewati += 1
            error_baris.append(f"Baris {i}: kode_aset atau nama kosong")
            continue

        id_kategori = None
        id_sub_kategori = None
        if nama_kategori:
            nama_kategori = str(nama_kategori).strip()
            kategori = Kategori.query.filter(
                db.func.lower(Kategori.nama) == nama_kategori.lower()
            ).first()
            if not kategori:
                kategori = Kategori(nama=nama_kategori)
                db.session.add(kategori)
                db.session.flush()
            id_kategori = kategori.id

            if nama_sub:
                nama_sub = str(nama_sub).strip()
                sub = SubKategori.query.filter(
                    db.func.lower(SubKategori.nama) == nama_sub.lower(),
                    SubKategori.id_kategori == kategori.id,
                ).first()
                if not sub:
                    sub = SubKategori(id_kategori=kategori.id, nama=nama_sub)
                    db.session.add(sub)
                    db.session.flush()
                id_sub_kategori = sub.id

        status_valid = status_aset if status_aset in ("Baik", "Rusak") else "Baik"
        jenis_valid = jenis_aset if jenis_aset in JENIS_ASET_OPTIONS else "Operasional"
        aset = Aset.query.filter_by(kode_aset=kode_aset).first()

        if aset:
            aset.nama = nama
            aset.gedung = gedung or aset.gedung
            aset.lantai = lantai or aset.lantai
            aset.ruangan = ruangan or aset.ruangan
            aset.status_aset = status_valid
            aset.jenis_aset = jenis_valid
            if id_kategori:
                aset.id_kategori = id_kategori
            if id_sub_kategori:
                aset.id_sub_kategori = id_sub_kategori
            diperbarui += 1
        else:
            db.session.add(Aset(
                kode_aset=kode_aset,
                nama=nama,
                gedung=gedung or "-",
                lantai=lantai or None,
                ruangan=ruangan or "-",
                status_aset=status_valid,
                jenis_aset=jenis_valid,
                id_kategori=id_kategori,
                id_sub_kategori=id_sub_kategori,
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


@app.route("/sub-kategori/create", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def sub_kategori_create():
    db.session.add(SubKategori(
        id_kategori=request.form.get("id_kategori"),
        nama=request.form.get("nama"),
    ))
    db.session.commit()
    flash("Sub-kategori ditambahkan.", "success")
    return redirect(url_for("kategori_list"))


@app.route("/api/sub-kategori/<int:kategori_id>")
@login_required
def api_sub_kategori(kategori_id):
    subs = SubKategori.query.filter_by(id_kategori=kategori_id).all()
    return jsonify([{"id": s.id, "nama": s.nama} for s in subs])


# ---------------------------------------------------------------------------
# TIKET (LAPORAN)
# ---------------------------------------------------------------------------
@app.route("/tiket")
@login_required
def tiket_list():
    status = request.args.get("status", "")
    jenis = request.args.get("jenis", "")
    query = Tiket.query
    if status:
        query = query.filter_by(status_tiket=status)
    if jenis:
        query = query.filter_by(jenis_tiket=jenis)

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Tiket.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    daftar_tiket = pagination.items
    
    # Ambil daftar gedung unik dari Aset untuk dropdown
    gedung_all = [
        g[0] for g in db.session.query(Aset.gedung).distinct().order_by(Aset.gedung).all() if g[0]
    ]
    
    return render_template(
        "tiket/list.html",
        daftar_tiket=daftar_tiket,
        pagination=pagination,
        gedung_all=gedung_all,
    )


@app.route("/tiket/create/pemindahan", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_create_pemindahan():
    """Buat tiket pemindahan."""
    aset_ids = request.form.getlist("aset_ids[]")
    if not aset_ids:
        flash("Pilih minimal 1 aset.", "danger")
        return redirect(url_for("tiket_list"))

    gedung_asal = request.form.get("gedung_asal", "").strip()
    lantai_asal = request.form.get("lantai_asal", "").strip()
    ruangan_asal = request.form.get("ruangan_asal", "").strip()
    gedung_tujuan = request.form.get("gedung_tujuan", "").strip()
    lantai_tujuan = request.form.get("lantai_tujuan", "").strip()
    ruangan_tujuan = request.form.get("ruangan_tujuan", "").strip()
    nama_pemohon = request.form.get("nama_pemohon", "").strip()
    catatan = request.form.get("catatan", "").strip()

    foto = save_upload(request.files.get("foto"), prefix="tiket_")

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
        status_tiket="Selesai",
    )
    db.session.add(tiket)
    db.session.flush()

    for aid in aset_ids:
        aset = db.session.get(Aset, int(aid))
        if aset:
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
            
            aset.gedung = gedung_tujuan
            aset.lantai = lantai_tujuan or None
            aset.ruangan = ruangan_tujuan
            aset.status_aset = "Baik"
            
            db.session.add(TiketAset(id_tiket=tiket.id, id_aset=aset.id))

    catat_log(tiket, None, "Selesai")
    db.session.commit()
    flash(f"Tiket pemindahan berhasil dibuat. {len(aset_ids)} aset dipindahkan.", "success")
    return redirect(url_for("tiket_list"))


@app.route("/tiket/create/kerusakan", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_create_kerusakan():
    """Buat tiket kerusakan."""
    aset_ids = request.form.getlist("aset_ids[]")
    if not aset_ids:
        flash("Pilih minimal 1 aset.", "danger")
        return redirect(url_for("tiket_list"))

    gedung_asal = request.form.get("gedung_asal", "").strip()
    lantai_asal = request.form.get("lantai_asal", "").strip()
    ruangan_asal = request.form.get("ruangan_asal", "").strip()
    nama_pemohon = request.form.get("nama_pemohon", "").strip()
    catatan = request.form.get("catatan", "").strip()

    foto = save_upload(request.files.get("foto"), prefix="tiket_")

    tiket = Tiket(
        jenis_tiket="Kerusakan",
        nama_pemohon=nama_pemohon,
        gedung_asal=gedung_asal,
        lantai_asal=lantai_asal,
        ruangan_asal=ruangan_asal,
        catatan=catatan,
        foto=foto,
        status_tiket="Pending",  # Menunggu perbaikan
    )
    db.session.add(tiket)
    db.session.flush()

    for aid in aset_ids:
        aset = db.session.get(Aset, int(aid))
        if aset:
            # Update status aset menjadi Rusak
            aset.status_aset = "Rusak"
            # Increment total kerusakan
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
            
            # Relasi tiket-aset
            db.session.add(TiketAset(id_tiket=tiket.id, id_aset=aset.id))

    catat_log(tiket, None, "Pending")
    db.session.commit()
    flash(f"Tiket kerusakan berhasil dibuat. {len(aset_ids)} aset rusak.", "success")
    return redirect(url_for("tiket_list"))


@app.route("/tiket/<int:tiket_id>")
@login_required
def tiket_detail(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)
    return render_template("tiket/detail.html", tiket=tiket)


@app.route("/tiket/<int:tiket_id>/selesai", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_selesai(tiket_id):
    """Tandai tiket kerusakan selesai (aset sudah diperbaiki)."""
    tiket = Tiket.query.get_or_404(tiket_id)
    
    if tiket.jenis_tiket != "Kerusakan":
        flash("Hanya tiket kerusakan yang bisa ditandai selesai.", "danger")
        return redirect(url_for("tiket_detail", tiket_id=tiket.id))
    
    if tiket.status_tiket != "Pending":
        flash("Tiket sudah selesai.", "warning")
        return redirect(url_for("tiket_detail", tiket_id=tiket.id))

    # Proses setiap aset
    for ta in tiket.aset_terkait:
        aset = ta.aset
        if aset:
            # Kembalikan status aset menjadi Baik
            aset.status_aset = "Baik"
            
            # Catat histori perbaikan
            histori = HistoriAset(
                id_aset=aset.id,
                jenis_event="perbaikan",
                gedung=aset.gedung,
                lantai=aset.lantai,
                ruangan=aset.ruangan,
                id_tiket=tiket.id
            )
            db.session.add(histori)

    catat_log(tiket, "Pending", "Selesai")
    tiket.status_tiket = "Selesai"
    db.session.commit()
    flash("Tiket kerusakan selesai. Aset sudah diperbaiki.", "success")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


# ---------------------------------------------------------------------------
# SCHEDULE (KALENDER)
# ---------------------------------------------------------------------------
@app.route("/schedule")
@login_required
def schedule():
    daftar_tiket = Tiket.query.order_by(Tiket.created_at.desc()).all()
    return render_template("schedule.html", daftar_tiket=daftar_tiket)


@app.route("/api/schedule-events")
@login_required
def api_schedule_events():
    """API untuk FullCalendar - ambil semua tiket sebagai event."""
    tiket_all = Tiket.query.order_by(Tiket.created_at).all()
    events = []
    for t in tiket_all:
        color = "#3b82f6" if t.jenis_tiket == "Pemindahan" else "#ef4444"  # Biru untuk pindah, merah untuk rusak
        events.append({
            "id": t.id,
            "title": f"#{t.id} - {t.jenis_tiket} - {t.nama_pemohon}",
            "start": t.created_at.isoformat(),
            "url": url_for("tiket_detail", tiket_id=t.id),
            "color": color,
            "extendedProps": {
                "jenis": t.jenis_tiket,
                "status": t.status_tiket,
                "pemohon": t.nama_pemohon
            }
        })
    return jsonify(events)


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
    if role != "admin":  # Hanya admin yang boleh
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
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)