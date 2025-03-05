from flask import Flask
from config import Config
from extensions import db, migrate, login_manager, bcrypt, mail
from models import User, HolidayRequest

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    
    login_manager.login_view = 'auth.login'
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register Blueprints
    from auth.routes import auth_bp
    from main.routes import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    return app
