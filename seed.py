"""
Script seeder untuk mengisi data awal database.
Jalankan dengan:  python seed.py

Akan membuat:
- 1 Admin, 2 Officer, 1 Teknisi (password sama: password123)
- 4 Kategori + sub-kategori sesuai contoh pada spesifikasi
- 5 contoh Aset
"""
from werkzeug.security import generate_password_hash
from app import app
from extensions import db
from models import User, Kategori, SubKategori, Aset


def run():
    with app.app_context():
        db.create_all()

        if User.query.first():
            print("Data sudah ada, seeder dibatalkan (hapus data manual jika ingin re-seed).")
            return

        # ---------------- Users ----------------
        pw = generate_password_hash("password123")
        users = [
            User(name="Admin Utama", email="admin@aset.com", password=pw, role="admin"),
            User(name="Officer Satu", email="officer1@aset.com", password=pw, role="officer"),
            User(name="Officer Dua", email="officer2@aset.com", password=pw, role="officer"),
            User(name="Teknisi Satu", email="teknisi1@aset.com", password=pw, role="teknisi"),
        ]
        db.session.add_all(users)

        # ---------------- Kategori & Sub Kategori ----------------
        struktur_kategori = {
            "Elektronik": ["TV", "AC", "Proyektor"],
            "Furniture": ["Meja", "Kursi", "Lemari"],
            "Kendaraan": ["Mobil", "Motor"],
            "Alat Kantor": ["Mesin Hitung", "Stapler"],
        }
        kategori_map = {}
        for nama_kategori, sub_list in struktur_kategori.items():
            kategori = Kategori(nama=nama_kategori)
            db.session.add(kategori)
            db.session.flush()
            kategori_map[nama_kategori] = kategori
            for nama_sub in sub_list:
                db.session.add(SubKategori(id_kategori=kategori.id, nama=nama_sub))
        db.session.flush()

        elektronik = kategori_map["Elektronik"]
        furniture = kategori_map["Furniture"]
        sub_tv = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="TV").first()
        sub_ac = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="AC").first()
        sub_meja = SubKategori.query.filter_by(id_kategori=furniture.id, nama="Meja").first()
        sub_kursi = SubKategori.query.filter_by(id_kategori=furniture.id, nama="Kursi").first()
        sub_proyektor = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="Proyektor").first()

        # ---------------- Contoh Aset ----------------
        # jenis_aset: "Pusat" untuk aset milik kantor pusat (Gedung A),
        # "Operasional" untuk aset di lokasi operasional/cabang (Gedung B & C).
        contoh_aset = [
            Aset(kode_aset="AST-001", nama="TV Samsung 42 inch", gedung="Gedung A", ruangan="Lobi",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=elektronik.id, id_sub_kategori=sub_tv.id),
            Aset(kode_aset="AST-002", nama="AC Daikin 1PK", gedung="Gedung A", ruangan="R. Meeting 1",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=elektronik.id, id_sub_kategori=sub_ac.id),
            Aset(kode_aset="AST-003", nama="Meja Kerja Kayu", gedung="Gedung B", ruangan="R. Staff",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=furniture.id, id_sub_kategori=sub_meja.id),
            Aset(kode_aset="AST-004", nama="Kursi Kantor Ergonomis", gedung="Gedung B", ruangan="R. Staff",
                 status_aset="Rusak", jenis_aset="Operasional",
                 id_kategori=furniture.id, id_sub_kategori=sub_kursi.id),
            Aset(kode_aset="AST-005", nama="Proyektor Epson", gedung="Gedung A", ruangan="R. Meeting 2",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=elektronik.id, id_sub_kategori=sub_proyektor.id),
            Aset(kode_aset="AST-006", nama="Laptop Asus Vivobook", gedung="Gedung C", ruangan="R. Lapangan",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=elektronik.id, id_sub_kategori=sub_tv.id),
            Aset(kode_aset="AST-007", nama="Kursi Direksi", gedung="Gedung A", ruangan="R. Direktur",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=furniture.id, id_sub_kategori=sub_kursi.id),
        ]
        db.session.add_all(contoh_aset)

        db.session.commit()
        print("Seeder selesai. Login dengan admin@aset.com / password123")


if __name__ == "__main__":
    run()
