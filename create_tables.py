"""
Script untuk membuat tabel baru yang belum ada di database TANPA
menyentuh data yang sudah ada (aset, user, dll tetap aman).

Dipakai setiap kali ada model/tabel baru ditambahkan ke models.py
(mis. saat menambahkan fitur baru) supaya tidak perlu hapus database
atau import ulang Excel -- cukup jalankan sekali:

    python create_tables.py

Aman dijalankan berkali-kali: db.create_all() SQLAlchemy hanya membuat
tabel yang belum ada, tabel yang sudah ada (beserta isinya) tidak
disentuh/diubah/dihapus sama sekali.
"""
from app import app
from extensions import db

with app.app_context():
    sebelum = set(db.inspect(db.engine).get_table_names())
    db.create_all()
    sesudah = set(db.inspect(db.engine).get_table_names())
    baru = sesudah - sebelum

    print("=" * 50)
    if baru:
        print(f"✅ Tabel baru berhasil dibuat: {', '.join(sorted(baru))}")
    else:
        print("ℹ️  Tidak ada tabel baru -- semua tabel sudah ada.")
    print("💡 Data yang sudah ada (aset, user, dll) tidak diubah/dihapus.")
    print("=" * 50)
