"""
Excepciones relacionadas con la API de Sesame
"""
from typing import Optional, Dict, Any
from .base import AppError


class APIError(AppError):
    """Error base para problemas con la API de Sesame"""
    pass


class APIConnectionError(APIError):
    """Error de conexión con la API"""
    def __init__(self, message: str = "Error de conexión con la API de Sesame", **kwargs):
        super().__init__(message, error_code="API_CONNECTION_ERROR", **kwargs)


class APITimeoutError(APIError):
    """Timeout en requests a la API"""
    def __init__(self, message: str = "Timeout en la conexión con la API", **kwargs):
        super().__init__(message, error_code="API_TIMEOUT_ERROR", **kwargs)


class APIAuthError(APIError):
    """Error de autenticación con la API"""
    def __init__(self, message: str = "Token de API inválido o expirado", **kwargs):
        super().__init__(message, error_code="API_AUTH_ERROR", **kwargs)


class APIRateLimitError(APIError):
    """Error de límite de rate en la API"""
    def __init__(self, message: str = "Límite de requests excedido", **kwargs):
        super().__init__(message, error_code="API_RATE_LIMIT_ERROR", **kwargs)


class APIServerError(APIError):
    """Error del servidor de la API (5xx)"""
    def __init__(self, status_code: int, message: str = "Error interno del servidor API", **kwargs):
        self.status_code = status_code
        details = kwargs.get('details', {})
        details.update({'status_code': status_code})
        super().__init__(message, error_code="API_SERVER_ERROR", details=details, **kwargs)