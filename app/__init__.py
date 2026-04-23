from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def normalize_database_url(database_url):
    """Normalize DB URL so SQLAlchemy can consume common provider formats."""
    if not database_url:
        return database_url

    # SQLAlchemy defaults postgresql:// to psycopg2; force psycopg v3 dialect.
    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql+psycopg://', 1)

    if database_url.startswith('postgresql://'):
        return database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

    if database_url.startswith('postgresql+psycopg://'):
        return database_url

    return database_url

def create_app(register_blueprints=True):
    app = Flask(__name__)
    
    # Configuration
    raw_database_url = os.getenv('DATABASE_URL')
    if not raw_database_url:
        raise RuntimeError('DATABASE_URL wajib diisi dan harus mengarah ke PostgreSQL.')

    database_url = normalize_database_url(raw_database_url)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'app/static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu.'
    
    # User loader untuk Flask-Login
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    if register_blueprints:
        from app.routes import main, chat, plant_analysis, auth
        app.register_blueprint(main.bp)
        app.register_blueprint(chat.bp)
        app.register_blueprint(plant_analysis.bp)
        app.register_blueprint(auth.bp)
    
    with app.app_context():
        db.create_all()
    
    return app
