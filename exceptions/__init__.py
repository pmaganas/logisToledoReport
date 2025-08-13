"""
Sistema de excepciones personalizado para la aplicación
"""

from .base import AppError
from .api_errors import APIError, APIConnectionError, APITimeoutError, APIAuthError, APIRateLimitError
from .validation_errors import ValidationError, DateValidationError, TokenValidationError
from .report_errors import ReportError, ReportGenerationError, ReportFileError
from .database_errors import DatabaseError, TokenNotFoundError

__all__ = [
    'AppError',
    'APIError', 'APIConnectionError', 'APITimeoutError', 'APIAuthError', 'APIRateLimitError',
    'ValidationError', 'DateValidationError', 'TokenValidationError', 
    'ReportError', 'ReportGenerationError', 'ReportFileError',
    'DatabaseError', 'TokenNotFoundError'
]