"""
Excepciones relacionadas con la generación de reportes
"""
from typing import Optional, Dict, Any
from .base import AppError


class ReportError(AppError):
    """Error base para problemas con reportes"""
    pass


class ReportGenerationError(ReportError):
    """Error durante la generación de reportes"""
    def __init__(
        self, 
        message: str = "Error al generar el reporte", 
        report_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if report_type:
            details['report_type'] = report_type
        super().__init__(message, error_code="REPORT_GENERATION_ERROR", details=details, **kwargs)


class ReportFileError(ReportError):
    """Error relacionado con archivos de reporte"""
    def __init__(
        self, 
        message: str = "Error al manejar archivo de reporte", 
        file_path: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if file_path:
            details['file_path'] = file_path
        super().__init__(message, error_code="REPORT_FILE_ERROR", details=details, **kwargs)


class ReportNotFoundError(ReportError):
    """Reporte no encontrado"""
    def __init__(
        self, 
        message: str = "Reporte no encontrado", 
        report_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if report_id:
            details['report_id'] = report_id
        super().__init__(message, error_code="REPORT_NOT_FOUND_ERROR", details=details, **kwargs)


class ReportLimitExceededError(ReportError):
    """Límite de reportes excedido"""
    def __init__(
        self, 
        message: str = "Límite máximo de reportes excedido", 
        current_count: Optional[int] = None,
        max_allowed: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if current_count is not None:
            details['current_count'] = current_count
        if max_allowed is not None:
            details['max_allowed'] = max_allowed
        super().__init__(message, error_code="REPORT_LIMIT_EXCEEDED_ERROR", details=details, **kwargs)