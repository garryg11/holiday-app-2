import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "replace-this-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(basedir, "holiday_approval.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail settings for Gmail using SSL on port 465
    MAIL_SERVER = os.environ.get("MAIL_SERVER") or "mail.gmx.net"
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 465)
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or "sabine.grasel@gmx.at"
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or "Office24#"
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "sabine.grasel@gmx.at"

    # Babel configuration
    LANGUAGES = ['en', 'de']