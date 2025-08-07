from flask import Flask
from flask_sqlalchemy import SQLAlchemy

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Inisialisasi OSS dan ISI
    from app.routes import init_routes
    init_routes(app)

    return app