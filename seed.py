"""
Script seeder untuk mengisi data awal database.
Jalankan dengan:  python seed.py

Akan membuat:
- 1 Admin (password: password123)
- Kategori & sub-kategori
- Contoh Aset dengan berbagai lokasi
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

        # ---------------- Users - hanya admin ----------------
        pw = generate_password_hash("password123")
        users = [
            User(name="Admin Utama", email="admin@aset.com", password=pw, role="admin"),
        ]
        db.session.add_all(users)

        # ---------------- Kategori & Sub Kategori ----------------
        struktur_kategori = {
            "Elektronik": ["TV", "AC", "Proyektor", "Laptop"],
            "Furniture": ["Meja", "Kursi", "Lemari", "Printer"],
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

        # Ambil referensi kategori
        elektronik = kategori_map["Elektronik"]
        furniture = kategori_map["Furniture"]
        alat_kantor = kategori_map["Alat Kantor"]
        
        # Ambil referensi sub_kategori
        sub_tv = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="TV").first()
        sub_ac = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="AC").first()
        sub_proyektor = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="Proyektor").first()
        sub_laptop = SubKategori.query.filter_by(id_kategori=elektronik.id, nama="Laptop").first()
        
        sub_meja = SubKategori.query.filter_by(id_kategori=furniture.id, nama="Meja").first()
        sub_kursi = SubKategori.query.filter_by(id_kategori=furniture.id, nama="Kursi").first()
        sub_lemari = SubKategori.query.filter_by(id_kategori=furniture.id, nama="Lemari").first()
        sub_printer = SubKategori.query.filter_by(id_kategori=furniture.id, nama="Printer").first()
        
        sub_mesin_hitung = SubKategori.query.filter_by(id_kategori=alat_kantor.id, nama="Mesin Hitung").first()
        sub_stapler = SubKategori.query.filter_by(id_kategori=alat_kantor.id, nama="Stapler").first()

        # ---------------- Contoh Aset dengan berbagai lokasi ----------------
        contoh_aset = [
            # Gedung A (Pusat - 3 lantai)
            Aset(kode_aset="AST-001", nama="TV Samsung 42 inch", gedung="Gedung A", lantai="1", ruangan="Lobi",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=elektronik.id, id_sub_kategori=sub_tv.id),
            Aset(kode_aset="AST-002", nama="AC Daikin 1PK", gedung="Gedung A", lantai="1", ruangan="R. Meeting 1",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=elektronik.id, id_sub_kategori=sub_ac.id),
            Aset(kode_aset="AST-003", nama="Meja Kerja Kayu", gedung="Gedung A", lantai="2", ruangan="R. Staff A",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=furniture.id, id_sub_kategori=sub_meja.id),
            Aset(kode_aset="AST-004", nama="Kursi Direksi", gedung="Gedung A", lantai="3", ruangan="R. Direktur",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=furniture.id, id_sub_kategori=sub_kursi.id),
            Aset(kode_aset="AST-005", nama="Proyektor Epson", gedung="Gedung A", lantai="2", ruangan="R. Meeting 2",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=elektronik.id, id_sub_kategori=sub_proyektor.id),
            Aset(kode_aset="AST-013", nama="Lemari Arsip", gedung="Gedung A", lantai="3", ruangan="R. Arsip",
                 status_aset="Baik", jenis_aset="Pusat",
                 id_kategori=furniture.id, id_sub_kategori=sub_lemari.id),
            
            # Gedung B (Operasional - 2 lantai)
            Aset(kode_aset="AST-006", nama="Laptop Asus Vivobook", gedung="Gedung B", lantai="1", ruangan="R. Staff B1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=elektronik.id, id_sub_kategori=sub_laptop.id),
            Aset(kode_aset="AST-007", nama="Kursi Kantor Ergonomis", gedung="Gedung B", lantai="1", ruangan="R. Staff B1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=furniture.id, id_sub_kategori=sub_kursi.id),
            Aset(kode_aset="AST-008", nama="Printer HP LaserJet", gedung="Gedung B", lantai="2", ruangan="R. Admin B2",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=furniture.id, id_sub_kategori=sub_printer.id),
            Aset(kode_aset="AST-009", nama="AC Daikin 1PK", gedung="Gedung B", lantai="2", ruangan="R. Meeting B2",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=elektronik.id, id_sub_kategori=sub_ac.id),
            Aset(kode_aset="AST-014", nama="Meja Kerja Besi", gedung="Gedung B", lantai="1", ruangan="R. Staff B1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=furniture.id, id_sub_kategori=sub_meja.id),
            
            # Gedung C (Operasional - 1 lantai)
            Aset(kode_aset="AST-010", nama="Meja Kerja Besi", gedung="Gedung C", lantai="1", ruangan="R. Lapangan C1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=furniture.id, id_sub_kategori=sub_meja.id),
            Aset(kode_aset="AST-011", nama="TV LG 55 inch", gedung="Gedung C", lantai="1", ruangan="R. Lounge C1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=elektronik.id, id_sub_kategori=sub_tv.id),
            Aset(kode_aset="AST-012", nama="Laptop Asus ROG", gedung="Gedung C", lantai="1", ruangan="R. Staff C1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=elektronik.id, id_sub_kategori=sub_laptop.id),
            Aset(kode_aset="AST-015", nama="Mesin Hitung", gedung="Gedung C", lantai="1", ruangan="R. Kasir C1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=alat_kantor.id, id_sub_kategori=sub_mesin_hitung.id),
            Aset(kode_aset="AST-016", nama="Stapler Elektrik", gedung="Gedung C", lantai="1", ruangan="R. Staff C1",
                 status_aset="Baik", jenis_aset="Operasional",
                 id_kategori=alat_kantor.id, id_sub_kategori=sub_stapler.id),
        ]
        db.session.add_all(contoh_aset)

        db.session.commit()
        print("=" * 50)
        print("✅ Seeder selesai!")
        print(f"👤 Login: admin@aset.com / password123")
        print(f"📦 Total aset: {Aset.query.count()}")
        print("=" * 50)


if __name__ == "__main__":
    run()