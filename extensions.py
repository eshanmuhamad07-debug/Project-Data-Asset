"""
File ini berisi instance ekstensi Flask (SQLAlchemy, LoginManager, CSRF, Limiter).
Dipisah dari app.py agar tidak terjadi circular import antara app.py <-> models.py
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Silakan login terlebih dahulu."
login_manager.login_message_category = "warning"

# Proteksi CSRF untuk semua form POST (Solusi #2)
csrf = CSRFProtect()

# Rate limiter, dipakai untuk membatasi percobaan login (Solusi #9)
limiter = Limiter(key_func=get_remote_address, default_limits=[])
