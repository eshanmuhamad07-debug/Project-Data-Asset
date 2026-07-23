"""
Script seeder untuk mengisi data awal database.
Jalankan dengan:  python seed.py

Akan membuat:
- 1 Akun Admin (password: password123)
- Struktur database (tabel-tabel dibuat oleh SQLAlchemy)
- Tidak ada data dummy (aset, kategori, dll)
"""
from werkzeug.security import generate_password_hash
from app import app
from extensions import db
from models import User


def run():
    with app.app_context():
        # Buat semua tabel (jika belum ada)
        db.create_all()

        # Cek apakah sudah ada user
        if User.query.first():
            print("=" * 50)
            print("⚠️  Data sudah ada, seeder dibatalkan.")
            print("💡 Jika ingin reset, hapus database dan jalankan ulang.")
            print("=" * 50)
            return

        # ---------------- Buat Akun Admin ----------------
        pw = generate_password_hash("password123")
        admin = User(
            name="Admin Utama",
            email="admin@aset.com",
            password=pw,
            role="admin",
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()

        print("=" * 50)
        print("✅ Seeder selesai!")
        print(f"👤 Login: admin@aset.com")
        print(f"🔑 Password: password123")
        print("📂 Struktur database telah dibuat.")
        print("💡 Silakan import data aset melalui menu Data Aset.")
        print("=" * 50)


if __name__ == "__main__":
    run()