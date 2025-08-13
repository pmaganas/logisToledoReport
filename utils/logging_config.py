"""
Configuración avanzada de logging
"""
import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from config.settings import get_settings


class ColoredFormatter(logging.Formatter):
    """Formatter con colores para terminal"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        # Aplicar color al nivel
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """Formatter estructurado para producción"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Añadir información extra si existe
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'execution_time'):
            log_data['execution_time'] = record.execution_time
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Convertir a string formateado
        return ' | '.join([
            f"{log_data['timestamp']}",
            f"{log_data['level']:8}",
            f"{log_data['logger']}",
            f"{log_data['function']}:{log_data['line']}",
            f"{log_data['message']}"
        ])


class RequestContextFilter(logging.Filter):
    """Filtro para añadir contexto de request"""
    
    def filter(self, record):
        # Intentar obtener contexto de Flask
        try:
            from flask import request, g
            if request:
                record.request_id = getattr(g, 'request_id', None)
                record.user_id = getattr(g, 'user_id', None)
                record.request_method = request.method
                record.request_path = request.path
        except (ImportError, RuntimeError):
            # No hay contexto de Flask disponible
            pass
        
        return True


class SensitiveDataFilter(logging.Filter):
    """Filtro para remover datos sensibles de los logs"""
    
    SENSITIVE_PATTERNS = [
        'token', 'password', 'secret', 'api_key', 'bearer',
        'authorization', 'credential', 'private'
    ]
    
    def filter(self, record):
        # Censurar datos sensibles en el mensaje
        message = record.getMessage().lower()
        
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                # Reemplazar con versión censurada
                record.msg = self._censor_message(str(record.msg))
                record.args = ()
                break
        
        return True
    
    def _censor_message(self, message: str) -> str:
        """Censurar partes sensibles del mensaje"""
        import re
        
        # Patrón para tokens y claves
        patterns = [
            r'token["\s]*[:=]["\s]*([A-Za-z0-9+/=_-]{8,})',
            r'password["\s]*[:=]["\s]*([^"\s]{4,})',
            r'Bearer\s+([A-Za-z0-9+/=_-]+)',
            r'api[_-]?key["\s]*[:=]["\s]*([A-Za-z0-9+/=_-]{8,})'
        ]
        
        for pattern in patterns:
            message = re.sub(pattern, lambda m: f"{m.group(0).split(m.group(1))[0]}{'*' * 8}", message, flags=re.IGNORECASE)
        
        return message


class LoggingManager:
    """Gestor de configuración de logging"""
    
    def __init__(self):
        self.settings = get_settings()
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        self._configured = False
    
    def setup_logging(self, environment: str = 'development'):
        """
        Configurar sistema de logging
        
        Args:
            environment: Entorno de ejecución ('development', 'production')
        """
        if self._configured:
            return
        
        # Configuración base
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.logging.level))
        
        # Limpiar handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        if environment == 'development':
            self._setup_development_logging()
        else:
            self._setup_production_logging()
        
        # Configurar loggers específicos
        self._configure_third_party_loggers()
        
        # Añadir filtros globales
        self._add_global_filters()
        
        self._configured = True
    
    def _setup_development_logging(self):
        """Configurar logging para desarrollo"""
        # Handler para consola con colores
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        colored_formatter = ColoredFormatter(
            '%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(colored_formatter)
        
        # Handler para archivo
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'app_debug.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Añadir handlers al root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def _setup_production_logging(self):
        """Configurar logging para producción"""
        # Handler para archivo principal
        main_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / 'app.log',
            when='D',  # Rotar diariamente
            interval=1,
            backupCount=30  # Mantener 30 días
        )
        main_handler.setLevel(logging.INFO)
        
        structured_formatter = StructuredFormatter()
        main_handler.setFormatter(structured_formatter)
        
        # Handler para errores
        error_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_dir / 'error.log',
            when='D',
            interval=1,
            backupCount=90  # Mantener errores por más tiempo
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(structured_formatter)
        
        # Handler para consola (solo errores críticos)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # Añadir handlers al root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)
    
    def _configure_third_party_loggers(self):
        """Configurar loggers de librerías externas"""
        # Suprimir logs verbose de urllib3 como en el código original
        if self.settings.logging.suppress_urllib3:
            logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
            logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
        
        # Configurar otros loggers específicos
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    def _add_global_filters(self):
        """Añadir filtros globales"""
        root_logger = logging.getLogger()
        
        # Filtro de contexto de request
        request_filter = RequestContextFilter()
        
        # Filtro de datos sensibles
        sensitive_filter = SensitiveDataFilter()
        
        for handler in root_logger.handlers:
            handler.addFilter(request_filter)
            handler.addFilter(sensitive_filter)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Obtener logger configurado"""
        return logging.getLogger(name)
    
    def create_report_logger(self, report_id: str) -> logging.Logger:
        """
        Crear logger específico para un reporte
        
        Args:
            report_id: ID del reporte
            
        Returns:
            Logger configurado para el reporte
        """
        logger_name = f"report.{report_id}"
        logger = logging.getLogger(logger_name)
        
        # Handler específico para el reporte
        report_handler = logging.FileHandler(
            self.log_dir / f'report_{report_id}.log'
        )
        report_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        report_handler.setFormatter(formatter)
        
        logger.addHandler(report_handler)
        logger.setLevel(logging.DEBUG)
        
        return logger


# Instancia global del gestor de logging
logging_manager = LoggingManager()


def setup_logging(environment: str = None):
    """
    Configurar logging de la aplicación
    
    Args:
        environment: Entorno ('development' o 'production')
    """
    if environment is None:
        environment = 'development' if os.getenv('FLASK_ENV') == 'development' else 'production'
    
    logging_manager.setup_logging(environment)


def get_logger(name: str) -> logging.Logger:
    """Obtener logger configurado"""
    return logging_manager.get_logger(name)


def get_report_logger(report_id: str) -> logging.Logger:
    """Obtener logger para reporte específico"""
    return logging_manager.create_report_logger(report_id)


class LogContext:
    """Context manager para añadir contexto a logs"""
    
    def __init__(self, **context):
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)