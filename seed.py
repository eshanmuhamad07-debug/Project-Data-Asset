"""
Script seeder untuk mengisi data awal database.
Jalankan dengan:  python seed.py

Akan membuat:
- 1 Admin (password: password123)
- Kategori
- Contoh Aset dengan berbagai lokasi dan field lengkap
"""
from werkzeug.security import generate_password_hash
from app import app
from extensions import db
from models import User, Kategori, Aset
from datetime import date


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

        # ---------------- Kategori (tanpa SubKategori) ----------------
        daftar_kategori = [
            "Elektronik", "Furniture", "Kendaraan", "Alat Kantor",
            "IT", "Mesin", "Perlengkapan", "Kendaraan Operasional"
        ]
        kategori_map = {}
        for nama_kategori in daftar_kategori:
            kategori = Kategori(nama=nama_kategori)
            db.session.add(kategori)
            db.session.flush()
            kategori_map[nama_kategori] = kategori

        # Ambil referensi kategori
        elektronik = kategori_map["Elektronik"]
        furniture = kategori_map["Furniture"]
        alat_kantor = kategori_map["Alat Kantor"]
        it = kategori_map["IT"]
        mesin = kategori_map["Mesin"]

        # ---------------- Contoh Aset dengan field lengkap ----------------
        contoh_aset = [
            # ===== GEDUNG A (Pusat/CAPEX - 3 lantai) =====
            Aset(
                kode_aset="AST-001",
                nama="TV Samsung 42 inch",
                area="Pusat",
                fungsi="Display Informasi",
                merek="Samsung",
                serial_number="SN-TV-001",
                spesifikasi="42 inch LED, Full HD, Smart TV, tahun 2022",
                tipe_aset="CAPEX",
                volume="1",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="1",
                ruangan="Lobi",
                tanggal_datang=date(2022, 1, 15),
                keterangan="TV untuk display informasi di lobi",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-002",
                nama="AC Daikin 1PK",
                area="Pusat",
                fungsi="Pendingin Ruangan",
                merek="Daikin",
                serial_number="SN-AC-002",
                spesifikasi="1PK, R32, Inverter, low watt",
                tipe_aset="CAPEX",
                volume="1",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="1",
                ruangan="R. Meeting 1",
                tanggal_datang=date(2022, 3, 10),
                keterangan="AC untuk ruang meeting",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-003",
                nama="Meja Kerja Kayu",
                area="Pusat",
                fungsi="Meja Staff",
                merek="Informa",
                serial_number="SN-MEJ-003",
                spesifikasi="Meja kerja kayu jati ukuran 120x60cm",
                tipe_aset="CAPEX",
                volume="2",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="2",
                ruangan="R. Staff A",
                tanggal_datang=date(2022, 5, 20),
                keterangan="Meja untuk staff administrasi",
                id_kategori=furniture.id,
            ),
            Aset(
                kode_aset="AST-004",
                nama="Kursi Direksi",
                area="Pusat",
                fungsi="Kursi Kerja",
                merek="Informa",
                serial_number="SN-KUR-004",
                spesifikasi="Kursi direksi berbahan kulit sintetis, ergonomis",
                tipe_aset="CAPEX",
                volume="3",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="3",
                ruangan="R. Direktur",
                tanggal_datang=date(2022, 6, 5),
                keterangan="Kursi untuk ruang direktur",
                id_kategori=furniture.id,
            ),
            Aset(
                kode_aset="AST-005",
                nama="Proyektor Epson",
                area="Pusat",
                fungsi="Presentasi",
                merek="Epson",
                serial_number="SN-PRO-005",
                spesifikasi="Proyektor 4000 lumens, Full HD, kecepatan refresh 120Hz",
                tipe_aset="CAPEX",
                volume="1",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="2",
                ruangan="R. Meeting 2",
                tanggal_datang=date(2023, 1, 15),
                keterangan="Proyektor untuk presentasi di ruang meeting",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-013",
                nama="Lemari Arsip",
                area="Pusat",
                fungsi="Penyimpanan Dokumen",
                merek="Informa",
                serial_number="SN-LEM-013",
                spesifikasi="Lemari arsip 4 laci, besi, warna abu-abu",
                tipe_aset="CAPEX",
                volume="2",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="3",
                ruangan="R. Arsip",
                tanggal_datang=date(2022, 8, 1),
                keterangan="Lemari untuk menyimpan dokumen penting",
                id_kategori=furniture.id,
            ),
            Aset(
                kode_aset="AST-017",
                nama="Server Dell PowerEdge",
                area="Pusat",
                fungsi="Server Database",
                merek="Dell",
                serial_number="SN-SRV-017",
                spesifikasi="Dell PowerEdge R740, 64GB RAM, 2TB Storage",
                tipe_aset="CAPEX",
                volume="1",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung A",
                lantai="2",
                ruangan="R. Server",
                tanggal_datang=date(2023, 6, 20),
                keterangan="Server untuk database perusahaan",
                id_kategori=it.id,
            ),

            # ===== GEDUNG B (Operasional/OPEX - 2 lantai) =====
            Aset(
                kode_aset="AST-006",
                nama="Laptop Asus Vivobook",
                area="Operasional",
                fungsi="Komputer Staff",
                merek="Asus",
                serial_number="SN-LAP-006",
                spesifikasi="Intel Core i5, RAM 8GB, SSD 512GB, Windows 11",
                tipe_aset="OPEX",
                volume="5",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung B",
                lantai="1",
                ruangan="R. Staff B1",
                tanggal_datang=date(2023, 3, 10),
                keterangan="Laptop untuk staff operasional",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-007",
                nama="Kursi Kantor Ergonomis",
                area="Operasional",
                fungsi="Kursi Kerja Staff",
                merek="Informa",
                serial_number="SN-KUR-007",
                spesifikasi="Kursi ergonomis, bisa diatur ketinggian, sandaran tangan",
                tipe_aset="OPEX",
                volume="10",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung B",
                lantai="1",
                ruangan="R. Staff B1",
                tanggal_datang=date(2023, 4, 5),
                keterangan="Kursi untuk staff di gedung B",
                id_kategori=furniture.id,
            ),
            Aset(
                kode_aset="AST-008",
                nama="Printer HP LaserJet",
                area="Operasional",
                fungsi="Pencetakan Dokumen",
                merek="HP",
                serial_number="SN-PRN-008",
                spesifikasi="HP LaserJet Pro M404dn, kecepatan cetak 38 ppm",
                tipe_aset="OPEX",
                volume="2",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung B",
                lantai="2",
                ruangan="R. Admin B2",
                tanggal_datang=date(2023, 5, 20),
                keterangan="Printer untuk kebutuhan admin",
                id_kategori=alat_kantor.id,
            ),
            Aset(
                kode_aset="AST-009",
                nama="AC Daikin 1PK",
                area="Operasional",
                fungsi="Pendingin Ruangan",
                merek="Daikin",
                serial_number="SN-AC-009",
                spesifikasi="1PK, R32, Inverter, low watt",
                tipe_aset="OPEX",
                volume="3",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung B",
                lantai="2",
                ruangan="R. Meeting B2",
                tanggal_datang=date(2023, 6, 15),
                keterangan="AC untuk ruang meeting gedung B",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-014",
                nama="Meja Kerja Besi",
                area="Operasional",
                fungsi="Meja Staff",
                merek="Informa",
                serial_number="SN-MEJ-014",
                spesifikasi="Meja kerja besi, ukuran 140x70cm",
                tipe_aset="OPEX",
                volume="8",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung B",
                lantai="1",
                ruangan="R. Staff B1",
                tanggal_datang=date(2023, 7, 1),
                keterangan="Meja untuk staff gedung B",
                id_kategori=furniture.id,
            ),
            Aset(
                kode_aset="AST-018",
                nama="Mesin Fotocopy Canon",
                area="Operasional",
                fungsi="Fotocopy Dokumen",
                merek="Canon",
                serial_number="SN-FOT-018",
                spesifikasi="Canon IR-ADV C356, color, duplex, 35 ppm",
                tipe_aset="OPEX",
                volume="1",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung B",
                lantai="1",
                ruangan="R. Admin B1",
                tanggal_datang=date(2023, 8, 10),
                keterangan="Mesin fotocopy untuk administrasi",
                id_kategori=mesin.id,
            ),

            # ===== GEDUNG C (Operasional/OPEX - 1 lantai) =====
            Aset(
                kode_aset="AST-010",
                nama="Meja Kerja Besi",
                area="Operasional",
                fungsi="Meja Lapangan",
                merek="Informa",
                serial_number="SN-MEJ-010",
                spesifikasi="Meja kerja besi, ukuran 160x80cm, kuat dan tahan lama",
                tipe_aset="OPEX",
                volume="6",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung C",
                lantai="1",
                ruangan="R. Lapangan C1",
                tanggal_datang=date(2023, 9, 5),
                keterangan="Meja untuk tim lapangan",
                id_kategori=furniture.id,
            ),
            Aset(
                kode_aset="AST-011",
                nama="TV LG 55 inch",
                area="Operasional",
                fungsi="Display Hiburan",
                merek="LG",
                serial_number="SN-TV-011",
                spesifikasi="55 inch 4K UHD, Smart TV, webOS",
                tipe_aset="OPEX",
                volume="1",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung C",
                lantai="1",
                ruangan="R. Lounge C1",
                tanggal_datang=date(2023, 10, 1),
                keterangan="TV untuk ruang lounge",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-012",
                nama="Laptop Asus ROG",
                area="Operasional",
                fungsi="Komputer Tim IT",
                merek="Asus",
                serial_number="SN-LAP-012",
                spesifikasi="Intel Core i7, RAM 16GB, SSD 1TB, RTX 3060",
                tipe_aset="OPEX",
                volume="2",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung C",
                lantai="1",
                ruangan="R. Staff C1",
                tanggal_datang=date(2023, 11, 15),
                keterangan="Laptop untuk tim IT",
                id_kategori=elektronik.id,
            ),
            Aset(
                kode_aset="AST-015",
                nama="Mesin Hitung",
                area="Operasional",
                fungsi="Penghitungan Uang",
                merek="Aurora",
                serial_number="SN-MES-015",
                spesifikasi="Mesin hitung uang, multi-mata uang, 1000 lembar/menit",
                tipe_aset="OPEX",
                volume="2",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung C",
                lantai="1",
                ruangan="R. Kasir C1",
                tanggal_datang=date(2023, 12, 1),
                keterangan="Mesin hitung untuk kasir",
                id_kategori=alat_kantor.id,
            ),
            Aset(
                kode_aset="AST-016",
                nama="Stapler Elektrik",
                area="Operasional",
                fungsi="Penyatuan Dokumen",
                merek="Max",
                serial_number="SN-STA-016",
                spesifikasi="Stapler elektrik, kapasitas 50 lembar",
                tipe_aset="OPEX",
                volume="3",
                satuan="Unit",
                status_aset="Baik",
                gedung="Gedung C",
                lantai="1",
                ruangan="R. Staff C1",
                tanggal_datang=date(2023, 12, 20),
                keterangan="Stapler elektrik untuk staff",
                id_kategori=alat_kantor.id,
            ),
        ]
        db.session.add_all(contoh_aset)

        db.session.commit()
        print("=" * 50)
        print("✅ Seeder selesai!")
        print(f"👤 Login: admin@aset.com / password123")
        print(f"📦 Total aset: {Aset.query.count()}")
        print(f"📂 Total kategori: {Kategori.query.count()}")
        print("=" * 50)


if __name__ == "__main__":
    run()