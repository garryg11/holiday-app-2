from flask import Flask, request
from config import Config
from extensions import db, migrate, login_manager, bcrypt, mail
from models import User, HolidayRequest
from flask_babel import Babel

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    babel = Babel(app)
    
    # Set the locale selector function using assignment
    babel.locale_selector_func = lambda: request.accept_languages.best_match(app.config['LANGUAGES'])
    
    # Inject get_locale into Jinja2 context so templates can use it
    @app.context_processor
    def inject_locale():
        return dict(get_locale=babel.locale_selector_func)
    
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register Blueprints
    from auth.routes import auth_bp
    from main.routes import main_bp
    from admin.routes import admin_bp
    from hr.routes import hr_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(hr_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
