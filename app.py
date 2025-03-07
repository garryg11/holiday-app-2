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
    
    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register Blueprints
    from auth.routes import auth_bp
    from main.routes import main_bp
    from admin.routes import admin_bp  # Import the admin blueprint
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)   # Register the admin blueprint
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
