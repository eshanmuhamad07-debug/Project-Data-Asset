import os
import io
from functools import wraps
from datetime import datetime

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
    TiketUser, KomentarTiket, LogStatus, Notifikasi
)
from roles import ROLE_ADMIN, ROLE_OFFICER, ROLE_TEKNISI, ROLES

# ---------------------------------------------------------------------------
# Konfigurasi Aplikasi
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)

# --- Solusi #3: Secret key & kredensial DB dari environment variable ---
# Sebelum menjalankan di server sungguhan, set env var berikut (jangan pakai
# nilai default di production):
#   SECRET_KEY, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, FLASK_DEBUG
# Contoh (Linux/Mac):
#   export SECRET_KEY="ganti-dengan-string-acak-panjang"
#   export DB_USER=root DB_PASSWORD= DB_HOST=localhost DB_NAME=db_manajemen_aset
# Kalau env var tidak di-set, dipakai nilai default yang cocok untuk XAMPP lokal.
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
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB per file

db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)          # Solusi #2: proteksi CSRF di semua form POST
limiter.init_app(app)       # Solusi #9: rate limit percobaan login


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


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
    except Exception:
        return False


def save_upload(file_storage, prefix=""):
    """Simpan file upload ke static/uploads, return nama file atau None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    if not is_valid_image(file_storage):
        return None
    filename = secure_filename(file_storage.filename)
    unique_name = f"{prefix}{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
    return unique_name


def user_terlibat_tiket(tiket):
    """Solusi #1: True jika current_user adalah admin, atau pembuat/pelaksana
    tiket ini. Dipakai untuk menutup celah otorisasi di route tiket."""
    if current_user.role == ROLE_ADMIN:
        return True
    return (
        TiketUser.query.filter_by(id_tiket=tiket.id, id_user=current_user.id).count()
        > 0
    )


def role_required(*roles):
    """Decorator untuk membatasi akses route berdasarkan role user."""
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


def buat_notifikasi(user_id, tiket_id, pesan):
    db.session.add(Notifikasi(id_user=user_id, id_tiket=tiket_id, pesan=pesan))


def notif_count():
    if not current_user.is_authenticated:
        return 0
    return Notifikasi.query.filter_by(id_user=current_user.id, is_read=False).count()


@app.context_processor
def inject_notif():
    return {"notif_count": notif_count() if current_user.is_authenticated else 0}


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(IntegrityError)
def handle_integrity_error(e):
    """Solusi #9: tangkap error database (mis. data duplikat / masih
    dipakai tabel lain) dan tampilkan pesan ramah alih-alih halaman 500."""
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
@limiter.limit("8 per minute", methods=["POST"])  # Solusi #6: cegah brute-force
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
    total_proses = Tiket.query.filter_by(status_tiket="Proses").count()

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
        total_proses=total_proses,
        chart_labels=chart_labels,
        chart_values=chart_values,
        tiket_terbaru=tiket_terbaru,
    )


# ---------------------------------------------------------------------------
# ASET (CRUD)
# ---------------------------------------------------------------------------
# Jenis Aset: setiap aset punya salah satu dari dua jenis berikut
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
    )  # Solusi #10: pagination server-side agar tetap cepat untuk data besar
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
    """Daftar lantai unik yang ada untuk suatu gedung (dipakai filter cascading)."""
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
    """Daftar ruangan unik untuk suatu gedung + lantai (dipakai filter cascading)."""
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

    foto = save_upload(request.files.get("foto"), prefix="aset_")
    aset = Aset(
        kode_aset=kode_aset,
        nama=request.form.get("nama"),
        foto=foto,
        gedung=request.form.get("gedung"),
        lantai=request.form.get("lantai") or None,
        ruangan=request.form.get("ruangan"),
        status_aset=request.form.get("status_aset", "Baik"),
        jenis_aset=jenis_aset,
        id_kategori=request.form.get("id_kategori") or None,
        id_sub_kategori=request.form.get("id_sub_kategori") or None,
    )
    db.session.add(aset)
    db.session.commit()
    flash("Aset berhasil ditambahkan.", "success")
    return redirect(url_for("aset_list"))


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
    jenis_aset = request.form.get("jenis_aset", aset.jenis_aset)
    aset.jenis_aset = jenis_aset if jenis_aset in JENIS_ASET_OPTIONS else aset.jenis_aset
    aset.id_kategori = request.form.get("id_kategori") or None
    aset.id_sub_kategori = request.form.get("id_sub_kategori") or None

    foto = save_upload(request.files.get("foto"), prefix="aset_")
    if foto:
        aset.foto = foto

    db.session.commit()
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


# ---------------------------------------------------------------------------
# EXPORT / IMPORT ASET (Excel) -- fitur baru
# ---------------------------------------------------------------------------
EXPORT_HEADERS = ["kode_aset", "nama", "gedung", "lantai", "ruangan", "status_aset", "jenis_aset", "kategori", "sub_kategori"]


@app.route("/aset/export")
@login_required
@role_required(ROLE_ADMIN)
def aset_export():
    """Unduh seluruh data aset sebagai file .xlsx. File hasil export ini bisa
    diedit lalu di-import ulang lewat /aset/import untuk memperbarui data."""
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
    """Import data aset dari file .xlsx (format sama dengan hasil /aset/export).
    Aset dicocokkan berdasarkan `kode_aset`: kalau kode sudah ada -> datanya
    DIPERBARUI, kalau belum ada -> dibuat sebagai aset baru. Kategori/sub-
    kategori yang belum ada di sistem akan otomatis dibuat agar prosesnya
    tetap lancar tanpa harus bolak-balik menambahkan kategori dulu."""
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
            continue  # baris kosong dilewati diam-diam

        kolom = (list(row) + [None] * len(EXPORT_HEADERS))[: len(EXPORT_HEADERS)]
        kode_aset, nama, gedung, lantai, ruangan, status_aset, jenis_aset, nama_kategori, nama_sub = kolom

        kode_aset = str(kode_aset).strip() if kode_aset else ""
        nama = str(nama).strip() if nama else ""
        if not kode_aset or not nama:
            dilewati += 1
            error_baris.append(f"Baris {i}: kode_aset atau nama kosong")
            continue

        # Cari/buat kategori & sub-kategori berdasarkan nama (opsional)
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

        status_valid = status_aset if status_aset in ("Baik", "Rusak", "Dipindahkan") else "Baik"
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
    """Dipakai oleh chained dropdown vanilla JS di form aset."""
    subs = SubKategori.query.filter_by(id_kategori=kategori_id).all()
    return jsonify([{"id": s.id, "nama": s.nama} for s in subs])


# ---------------------------------------------------------------------------
# TIKET
# ---------------------------------------------------------------------------
@app.route("/tiket")
@login_required
def tiket_list():
    status = request.args.get("status", "")
    query = Tiket.query
    if status:
        query = query.filter_by(status_tiket=status)

    # teknisi/officer hanya lihat tiket miliknya (pembuat/pelaksana) + admin lihat semua
    if current_user.role != "admin":
        my_ids = [
            tu.id_tiket for tu in TiketUser.query.filter_by(id_user=current_user.id).all()
        ]
        query = query.filter(Tiket.id.in_(my_ids)) if my_ids else query.filter(False)

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Tiket.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    daftar_tiket = pagination.items
    daftar_aset = Aset.query.all()
    return render_template(
        "tiket/list.html",
        daftar_tiket=daftar_tiket,
        daftar_aset=daftar_aset,
        pagination=pagination,
    )


@app.route("/tiket/create", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_OFFICER)
def tiket_create():
    jenis = request.form.get("jenis_tiket")
    aset_ids = request.form.getlist("aset_ids")
    if not aset_ids:
        flash("Pilih minimal 1 aset.", "danger")
        return redirect(url_for("tiket_list"))

    foto = save_upload(request.files.get("foto"), prefix="tiket_")
    tiket = Tiket(
        jenis_tiket=jenis,
        nama_pemohon=request.form.get("nama_pemohon"),
        gedung_tujuan=request.form.get("gedung_tujuan"),
        ruangan_tujuan=request.form.get("ruangan_tujuan"),
        catatan=request.form.get("catatan"),
        foto=foto,
        status_tiket="Pending",
    )
    db.session.add(tiket)
    db.session.flush()  # supaya tiket.id tersedia

    for aid in aset_ids:
        aset = db.session.get(Aset, int(aid))
        status_awal = aset.status_aset if aset else None
        db.session.add(TiketAset(
            id_tiket=tiket.id, id_aset=int(aid), status_sebelum=status_awal
        ))
        if aset:
            aset.status_aset = "Dipindahkan" if jenis == "Pemindahan" else "Rusak"

    db.session.add(TiketUser(id_tiket=tiket.id, id_user=current_user.id, peran_di_tiket="pembuat"))
    catat_log(tiket, None, "Pending")

    # Notifikasi ke semua admin
    for admin in User.query.filter_by(role="admin").all():
        buat_notifikasi(admin.id, tiket.id, f"Tiket baru #{tiket.id} menunggu review.")

    db.session.commit()
    flash("Tiket berhasil dibuat.", "success")
    return redirect(url_for("tiket_list"))


@app.route("/tiket/<int:tiket_id>")
@login_required
def tiket_detail(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)
    if not user_terlibat_tiket(tiket):  # Solusi #1
        abort(403)
    calon_pelaksana = User.query.filter_by(
        role=ROLE_OFFICER if tiket.jenis_tiket == "Pemindahan" else ROLE_TEKNISI,
        is_active=True,
    ).all()
    return render_template("tiket/detail.html", tiket=tiket, calon_pelaksana=calon_pelaksana)


@app.route("/tiket/<int:tiket_id>/approve", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_approve(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)
    pelaksana_ids = request.form.getlist("pelaksana_ids")
    catatan_internal = request.form.get("catatan_internal", "").strip()

    # Hapus pelaksana lama (selain pembuat), lalu tambahkan yang baru
    TiketUser.query.filter_by(id_tiket=tiket.id, peran_di_tiket="pelaksana").delete()
    for uid in pelaksana_ids:
        db.session.add(TiketUser(id_tiket=tiket.id, id_user=int(uid), peran_di_tiket="pelaksana"))
        buat_notifikasi(int(uid), tiket.id, f"Anda ditunjuk sebagai pelaksana tiket #{tiket.id}.")

    if catatan_internal:
        db.session.add(KomentarTiket(id_tiket=tiket.id, id_user=current_user.id, pesan=f"[Catatan Internal] {catatan_internal}"))

    catat_log(tiket, tiket.status_tiket, "Disetujui")
    tiket.status_tiket = "Disetujui"
    db.session.commit()
    flash("Tiket disetujui dan pelaksana ditugaskan.", "success")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


@app.route("/tiket/<int:tiket_id>/tolak", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_tolak(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)

    # Solusi #7: kembalikan status aset ke kondisi sebelum tiket dibuat --
    # sebelumnya status aset (mis. "Rusak"/"Dipindahkan") tidak pernah
    # dikembalikan saat tiket ditolak, jadi aset selamanya nyangkut salah status.
    for ta in tiket.aset_terkait:
        if ta.aset and ta.status_sebelum:
            ta.aset.status_aset = ta.status_sebelum

    catat_log(tiket, tiket.status_tiket, "Ditolak")
    tiket.status_tiket = "Ditolak"
    db.session.commit()
    flash("Tiket ditolak, status aset dikembalikan seperti semula.", "info")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


@app.route("/tiket/<int:tiket_id>/assign", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def tiket_assign_edit(tiket_id):
    """Admin bisa mengedit pelaksana kapan saja meski status Proses."""
    tiket = Tiket.query.get_or_404(tiket_id)
    pelaksana_ids = request.form.getlist("pelaksana_ids")

    TiketUser.query.filter_by(id_tiket=tiket.id, peran_di_tiket="pelaksana").delete()
    for uid in pelaksana_ids:
        db.session.add(TiketUser(id_tiket=tiket.id, id_user=int(uid), peran_di_tiket="pelaksana"))
        buat_notifikasi(int(uid), tiket.id, f"Penugasan Anda pada tiket #{tiket.id} diperbarui.")

    db.session.commit()
    flash("Daftar pelaksana diperbarui.", "success")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


@app.route("/tiket/<int:tiket_id>/mulai", methods=["POST"])
@login_required
def tiket_mulai(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)
    if not user_terlibat_tiket(tiket):  # Solusi #1
        abort(403)
    catat_log(tiket, tiket.status_tiket, "Proses")
    tiket.status_tiket = "Proses"
    db.session.commit()
    flash("Tiket mulai diproses.", "success")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


@app.route("/tiket/<int:tiket_id>/selesai", methods=["POST"])
@login_required
def tiket_selesai(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)
    if not user_terlibat_tiket(tiket):  # Solusi #1
        abort(403)
    catat_log(tiket, tiket.status_tiket, "Selesai")
    tiket.status_tiket = "Selesai"

    for ta in tiket.aset_terkait:
        aset = ta.aset
        if tiket.jenis_tiket == "Pemindahan":
            aset.gedung = tiket.gedung_tujuan or aset.gedung
            aset.ruangan = tiket.ruangan_tujuan or aset.ruangan
            aset.status_aset = "Baik"
        else:
            aset.status_aset = "Baik"

    db.session.commit()
    flash("Tiket selesai. Data aset diperbarui otomatis.", "success")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


@app.route("/tiket/<int:tiket_id>/komentar", methods=["POST"])
@login_required
def tiket_komentar(tiket_id):
    tiket = Tiket.query.get_or_404(tiket_id)
    if not user_terlibat_tiket(tiket):  # Solusi #1
        abort(403)
    foto = save_upload(request.files.get("foto"), prefix="komentar_")
    db.session.add(KomentarTiket(
        id_tiket=tiket.id,
        id_user=current_user.id,
        pesan=request.form.get("pesan"),
        foto_komentar=foto,
    ))

    # notifikasi ke admin jika yang komentar pelaksana (misal minta bantuan)
    if current_user.role != "admin":
        for admin in User.query.filter_by(role="admin").all():
            buat_notifikasi(admin.id, tiket.id, f"Komentar baru di tiket #{tiket.id} dari {current_user.name}.")

    db.session.commit()
    flash("Komentar ditambahkan.", "success")
    return redirect(url_for("tiket_detail", tiket_id=tiket.id))


# ---------------------------------------------------------------------------
# NOTIFIKASI
# ---------------------------------------------------------------------------
@app.route("/notifikasi")
@login_required
def notifikasi_list():
    daftar = Notifikasi.query.filter_by(id_user=current_user.id).order_by(Notifikasi.created_at.desc()).all()
    for n in daftar:
        n.is_read = True
    db.session.commit()
    return render_template("notifikasi.html", daftar=daftar)


@app.route("/api/notifikasi/count")
@login_required
def api_notif_count():
    return jsonify({"count": notif_count()})


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
    if len(password) < 8:  # Solusi #11: validasi minimal password
        flash("Password minimal 8 karakter.", "danger")
        return redirect(url_for("users_list"))
    if role not in ROLES:  # Solusi #12: hanya izinkan role yang valid
        flash("Role tidak valid.", "danger")
        return redirect(url_for("users_list"))

    db.session.add(User(
        name=request.form.get("name"),
        email=email,
        password=generate_password_hash(password),
        role=role,
    ))
    db.session.commit()
    flash("User berhasil ditambahkan.", "success")
    return redirect(url_for("users_list"))


@app.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def users_toggle(user_id):
    """Solusi #8: nonaktifkan/aktifkan akun (soft-delete) alih-alih hapus
    permanen -- menghapus user yang punya riwayat tiket/komentar akan gagal
    karena foreign key (IntegrityError)."""
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
    # Solusi #4: debug mode HARUS mati saat aplikasi diakses publik
    # (debugger Werkzeug bisa dieksploitasi jadi remote code execution).
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)
