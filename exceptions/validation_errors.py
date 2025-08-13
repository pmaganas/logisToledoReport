"""
Excepciones relacionadas con validación de datos
"""
from typing import Optional, Dict, Any
from .base import AppError


class ValidationError(AppError):
    """Error base para problemas de validación"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        self.field = field
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details, **kwargs)


class DateValidationError(ValidationError):
    """Error de validación de fechas"""
    def __init__(
        self, 
        message: str = "Formato de fecha inválido", 
        date_field: Optional[str] = None,
        expected_format: str = "YYYY-MM-DD",
        **kwargs
    ):
        details = kwargs.get('details', {})
        details.update({
            'expected_format': expected_format,
            'date_field': date_field
        })
        super().__init__(message, field=date_field, error_code="DATE_VALIDATION_ERROR", details=details, **kwargs)


class TokenValidationError(ValidationError):
    """Error de validación de token"""
    def __init__(self, message: str = "Token de API inválido", **kwargs):
        super().__init__(message, field="token", error_code="TOKEN_VALIDATION_ERROR", **kwargs)


class EmployeeValidationError(ValidationError):
    """Error de validación de empleado"""
    def __init__(self, message: str = "ID de empleado inválido", employee_id: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if employee_id:
            details['employee_id'] = employee_id
        super().__init__(message, field="employee_id", error_code="EMPLOYEE_VALIDATION_ERROR", details=details, **kwargs)


class OfficeValidationError(ValidationError):
    """Error de validación de oficina"""
    def __init__(self, message: str = "ID de oficina inválido", office_id: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if office_id:
            details['office_id'] = office_id
        super().__init__(message, field="office_id", error_code="OFFICE_VALIDATION_ERROR", details=details, **kwargs)