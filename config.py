import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("THE_SECRET_KEY") or "replace-this-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(basedir, "holiday_approval.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail settings (adjust these for your SMTP provider)
    MAIL_SERVER = os.environ.get("MAIL_SERVER") or "smtp.gmail.com"
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") == "True" or True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or "admin@gmail.com"
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or "jholiday76"
