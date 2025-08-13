"""
Excepción base para la aplicación
"""
from typing import Optional, Dict, Any


class AppError(Exception):
    """
    Excepción base para todos los errores de la aplicación
    """
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir excepción a diccionario para JSON responses"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', error_code='{self.error_code}')"