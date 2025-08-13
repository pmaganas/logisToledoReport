"""
Punto de entrada principal para la aplicación de reportes de Sesame
"""
import os
from typing import NoReturn

from app import app
from config.settings import get_settings
from utils.logging_config import get_logger


def main() -> NoReturn:
    """
    Función principal para ejecutar la aplicación
    """
    logger = get_logger(__name__)
    settings = get_settings()
    
    # Determinar configuración de ejecución
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"Iniciando aplicación en {host}:{port} (debug={debug_mode})")
    logger.info(f"Base de datos: {settings.database.url}")
    logger.info(f"Directorio de reportes temporales: {settings.reports.temp_dir}")
    
    try:
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            use_reloader=debug_mode,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Error iniciando aplicación: {str(e)}")
        raise


if __name__ == "__main__":
    main()
