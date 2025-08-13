"""
Aplicación Flask principal para generación de reportes de Sesame Time Tracking
"""
import os
from typing import Tuple
from flask import Flask, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

from config.settings import init_settings, Settings
from utils.logging_config import setup_logging
from exceptions import AppError

class Base(DeclarativeBase):
    """Base class para modelos de SQLAlchemy"""
    pass


db: SQLAlchemy = SQLAlchemy(model_class=Base)


def create_app(config_override: Settings = None) -> Flask:
    """
    Factory function para crear la aplicación Flask
    
    Args:
        config_override: Configuración personalizada (opcional)
        
    Returns:
        Instancia configurada de Flask
    """
    # Inicializar configuración
    settings = config_override or init_settings()
    
    # Configurar logging
    setup_logging()
    
    # Crear aplicación Flask
    app = Flask(__name__)
    
    # Configurar aplicación
    _configure_app(app, settings)
    
    # Inicializar extensiones
    _init_extensions(app)
    
    # Registrar blueprints
    _register_blueprints(app)
    
    # Registrar manejadores de errores
    _register_error_handlers(app)
    
    return app


def _configure_app(app: Flask, settings: Settings) -> None:
    """
    Configurar aplicación Flask
    
    Args:
        app: Instancia de Flask
        settings: Configuración de la aplicación
    """
    app.secret_key = settings.security.session_secret
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database.url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": settings.database.pool_recycle,
        "pool_pre_ping": settings.database.pool_pre_ping,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Configurar sesiones
    app.permanent_session_lifetime = 86400  # 24 horas
    

def _init_extensions(app: Flask) -> None:
    """
    Inicializar extensiones Flask
    
    Args:
        app: Instancia de Flask
    """
    db.init_app(app)
    
    with app.app_context():
        # Importar modelos para crear tablas
        import models  # noqa: F401
        db.create_all()


def _register_blueprints(app: Flask) -> None:
    """
    Registrar blueprints de la aplicación
    
    Args:
        app: Instancia de Flask
    """
    from routes.main import main_bp
    app.register_blueprint(main_bp)


def _register_error_handlers(app: Flask) -> None:
    """
    Registrar manejadores de errores globales
    
    Args:
        app: Instancia de Flask
    """
    @app.errorhandler(404)
    def not_found_error(error) -> Tuple[str, int]:
        """Manejador para errores 404"""
        return "Página no encontrada", 404

    @app.errorhandler(500)
    def internal_error(error) -> Tuple[str, int]:
        """Manejador para errores 500"""
        app.logger.error(f"Error interno del servidor: {error}")
        return "Error interno del servidor", 500
    
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError) -> Tuple[Response, int]:
        """Manejador para errores de aplicación personalizados"""
        from flask import jsonify, request
        
        app.logger.error(f"AppError: {error}")
        
        if request.is_json:
            return jsonify(error.to_dict()), 400
        else:
            return f"Error: {error.message}", 400

# Crear instancia de la aplicación
app: Flask = create_app()
