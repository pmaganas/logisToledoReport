"""
Excepciones relacionadas con la base de datos
"""
from typing import Optional, Dict, Any
from .base import AppError


class DatabaseError(AppError):
    """Error base para problemas con la base de datos"""
    pass


class TokenNotFoundError(DatabaseError):
    """Token no encontrado en la base de datos"""
    def __init__(self, message: str = "No se encontró un token activo configurado", **kwargs):
        super().__init__(message, error_code="TOKEN_NOT_FOUND_ERROR", **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Error de conexión con la base de datos"""
    def __init__(self, message: str = "Error de conexión con la base de datos", **kwargs):
        super().__init__(message, error_code="DATABASE_CONNECTION_ERROR", **kwargs)


class DatabaseOperationError(DatabaseError):
    """Error en operación de base de datos"""
    def __init__(
        self, 
        message: str = "Error en operación de base de datos", 
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        super().__init__(message, error_code="DATABASE_OPERATION_ERROR", details=details, **kwargs)