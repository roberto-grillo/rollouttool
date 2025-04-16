# config.py
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///attivita.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.abspath(os.path.join("static", "uploads"))
    # Microsoft OAuth
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    TENANT_ID = os.getenv("TENANT_ID")
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    SCOPE = ["openid", "email", "profile", "User.Read"]

    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    AUTH_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
    TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"

    MAX_UPLOAD_SIZE_MB = 1
    ENABLE_CHANGE_HISTORY = True
