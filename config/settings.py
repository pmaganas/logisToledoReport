"""
Configuración centralizada de la aplicación
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    url: str
    pool_recycle: int = 300
    pool_pre_ping: bool = True


@dataclass
class APIConfig:
    """Configuración de API Sesame"""
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.3
    page_size: int = 500
    pool_connections: int = 10
    pool_maxsize: int = 10


@dataclass
class ReportConfig:
    """Configuración de generación de reportes"""
    max_reports: int = 10
    temp_dir: str = 'temp_reports'
    max_pages: int = 100
    chunk_size: int = 1000


@dataclass
class SecurityConfig:
    """Configuración de seguridad"""
    session_secret: str
    admin_username: str
    admin_password: str
    session_permanent: bool = True


@dataclass
class LoggingConfig:
    """Configuración de logging"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    suppress_urllib3: bool = True


@dataclass
class Settings:
    """Configuración principal de la aplicación"""
    database: DatabaseConfig
    api: APIConfig
    reports: ReportConfig
    security: SecurityConfig
    logging: LoggingConfig
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Crear configuración desde variables de entorno"""
        
        # Validar variables requeridas
        required_vars = ['DATABASE_URL', 'SESSION_SECRET', 'ADMIN_USERNAME', 'ADMIN_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Variables de entorno requeridas no encontradas: {', '.join(missing_vars)}")
        
        return cls(
            database=DatabaseConfig(
                url=os.getenv('DATABASE_URL'),
                pool_recycle=int(os.getenv('DB_POOL_RECYCLE', 300)),
                pool_pre_ping=os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true'
            ),
            api=APIConfig(
                timeout=int(os.getenv('API_TIMEOUT', 30)),
                max_retries=int(os.getenv('API_MAX_RETRIES', 3)),
                backoff_factor=float(os.getenv('API_BACKOFF_FACTOR', 0.3)),
                page_size=int(os.getenv('API_PAGE_SIZE', 500)),
                pool_connections=int(os.getenv('API_POOL_CONNECTIONS', 10)),
                pool_maxsize=int(os.getenv('API_POOL_MAXSIZE', 10))
            ),
            reports=ReportConfig(
                max_reports=int(os.getenv('MAX_REPORTS', 10)),
                temp_dir=os.getenv('TEMP_REPORTS_DIR', 'temp_reports'),
                max_pages=int(os.getenv('REPORT_MAX_PAGES', 100)),
                chunk_size=int(os.getenv('REPORT_CHUNK_SIZE', 1000))
            ),
            security=SecurityConfig(
                session_secret=os.getenv('SESSION_SECRET'),
                admin_username=os.getenv('ADMIN_USERNAME'),
                admin_password=os.getenv('ADMIN_PASSWORD'),
                session_permanent=os.getenv('SESSION_PERMANENT', 'true').lower() == 'true'
            ),
            logging=LoggingConfig(
                level=os.getenv('LOG_LEVEL', 'INFO'),
                format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                suppress_urllib3=os.getenv('SUPPRESS_URLLIB3_LOGS', 'true').lower() == 'true'
            )
        )


# Instancia global de configuración
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Obtener configuración global"""
    global settings
    if settings is None:
        settings = Settings.from_env()
    return settings


def init_settings() -> Settings:
    """Inicializar configuración"""
    global settings
    settings = Settings.from_env()
    return settings