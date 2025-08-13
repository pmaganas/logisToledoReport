"""
Validadores centralizados para la aplicación
"""
import re
from datetime import datetime, date
from typing import Optional, Tuple, Union, Dict, Any

from exceptions import (
    DateValidationError, 
    TokenValidationError, 
    EmployeeValidationError,
    OfficeValidationError,
    ValidationError
)


class DateValidator:
    """Validador para fechas"""
    
    DATE_FORMAT = '%Y-%m-%d'
    DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    @classmethod
    def validate_date_string(cls, date_str: str, field_name: str = "fecha") -> datetime:
        """
        Valida una fecha en formato string YYYY-MM-DD
        
        Args:
            date_str: Fecha en formato string
            field_name: Nombre del campo para errores
            
        Returns:
            datetime: Fecha parseada
            
        Raises:
            DateValidationError: Si la fecha es inválida
        """
        if not date_str:
            raise DateValidationError(
                f"La {field_name} es requerida",
                date_field=field_name
            )
        
        if not cls.DATE_REGEX.match(date_str):
            raise DateValidationError(
                f"Formato de {field_name} inválido. Use YYYY-MM-DD",
                date_field=field_name,
                details={'provided_value': date_str}
            )
        
        try:
            return datetime.strptime(date_str, cls.DATE_FORMAT)
        except ValueError as e:
            raise DateValidationError(
                f"Fecha {field_name} inválida: {date_str}",
                date_field=field_name,
                original_error=e,
                details={'provided_value': date_str}
            )
    
    @classmethod
    def validate_date_range(
        cls, 
        from_date: str, 
        to_date: str
    ) -> Tuple[datetime, datetime]:
        """
        Valida un rango de fechas
        
        Args:
            from_date: Fecha inicial
            to_date: Fecha final
            
        Returns:
            Tuple[datetime, datetime]: Fechas parseadas (inicio, fin)
            
        Raises:
            DateValidationError: Si las fechas son inválidas
        """
        start_date = cls.validate_date_string(from_date, "fecha de inicio")
        end_date = cls.validate_date_string(to_date, "fecha de fin")
        
        if start_date > end_date:
            raise DateValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin",
                details={
                    'from_date': from_date,
                    'to_date': to_date
                }
            )
        
        return start_date, end_date
    
    @classmethod
    def validate_date_not_future(cls, date_str: str, field_name: str = "fecha") -> datetime:
        """
        Valida que una fecha no sea futura
        
        Args:
            date_str: Fecha en formato string
            field_name: Nombre del campo
            
        Returns:
            datetime: Fecha validada
            
        Raises:
            DateValidationError: Si la fecha es futura
        """
        parsed_date = cls.validate_date_string(date_str, field_name)
        
        if parsed_date.date() > date.today():
            raise DateValidationError(
                f"La {field_name} no puede ser futura",
                date_field=field_name,
                details={'provided_date': date_str, 'today': date.today().isoformat()}
            )
        
        return parsed_date


class TokenValidator:
    """Validador para tokens de API"""
    
    # Patrón básico para tokens de Sesame (ajustar según sea necesario)
    TOKEN_MIN_LENGTH = 32
    TOKEN_MAX_LENGTH = 256
    TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9+/=_-]+$')
    
    @classmethod
    def validate_token(cls, token: str) -> str:
        """
        Valida un token de API
        
        Args:
            token: Token a validar
            
        Returns:
            str: Token validado (stripped)
            
        Raises:
            TokenValidationError: Si el token es inválido
        """
        if not token:
            raise TokenValidationError("El token es requerido")
        
        token = token.strip()
        
        if len(token) < cls.TOKEN_MIN_LENGTH:
            raise TokenValidationError(
                f"El token debe tener al menos {cls.TOKEN_MIN_LENGTH} caracteres",
                details={'token_length': len(token), 'min_length': cls.TOKEN_MIN_LENGTH}
            )
        
        if len(token) > cls.TOKEN_MAX_LENGTH:
            raise TokenValidationError(
                f"El token no puede exceder {cls.TOKEN_MAX_LENGTH} caracteres",
                details={'token_length': len(token), 'max_length': cls.TOKEN_MAX_LENGTH}
            )
        
        if not cls.TOKEN_PATTERN.match(token):
            raise TokenValidationError(
                "El token contiene caracteres inválidos",
                details={'allowed_pattern': 'A-Z, a-z, 0-9, +, /, =, _, -'}
            )
        
        return token


class EmployeeValidator:
    """Validador para IDs de empleado"""
    
    @classmethod
    def validate_employee_id(cls, employee_id: Optional[str]) -> Optional[str]:
        """
        Valida un ID de empleado
        
        Args:
            employee_id: ID del empleado (puede ser None)
            
        Returns:
            Optional[str]: ID validado o None
            
        Raises:
            EmployeeValidationError: Si el ID es inválido
        """
        if not employee_id:
            return None
        
        employee_id = employee_id.strip()
        
        if not employee_id:
            return None
        
        # Validar que sea un UUID válido (formato típico de Sesame)
        uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        
        if not uuid_pattern.match(employee_id):
            raise EmployeeValidationError(
                "ID de empleado inválido. Debe ser un UUID válido",
                employee_id=employee_id
            )
        
        return employee_id


class OfficeValidator:
    """Validador para IDs de oficina"""
    
    @classmethod
    def validate_office_id(cls, office_id: Optional[str]) -> Optional[str]:
        """
        Valida un ID de oficina
        
        Args:
            office_id: ID de la oficina (puede ser None)
            
        Returns:
            Optional[str]: ID validado o None
            
        Raises:
            OfficeValidationError: Si el ID es inválido
        """
        if not office_id:
            return None
        
        office_id = office_id.strip()
        
        if not office_id:
            return None
        
        # Validar que sea un UUID válido
        uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        
        if not uuid_pattern.match(office_id):
            raise OfficeValidationError(
                "ID de oficina inválido. Debe ser un UUID válido",
                office_id=office_id
            )
        
        return office_id


class ReportValidator:
    """Validador para parámetros de reportes"""
    
    VALID_REPORT_TYPES = ['by_employee', 'by_activity', 'summary']
    VALID_FORMATS = ['xlsx', 'csv']
    
    @classmethod
    def validate_report_type(cls, report_type: str) -> str:
        """
        Valida el tipo de reporte
        
        Args:
            report_type: Tipo de reporte
            
        Returns:
            str: Tipo de reporte validado
            
        Raises:
            ValidationError: Si el tipo es inválido
        """
        if not report_type:
            raise ValidationError("El tipo de reporte es requerido", field="report_type")
        
        if report_type not in cls.VALID_REPORT_TYPES:
            raise ValidationError(
                f"Tipo de reporte inválido. Valores permitidos: {', '.join(cls.VALID_REPORT_TYPES)}",
                field="report_type",
                details={'provided_value': report_type, 'valid_values': cls.VALID_REPORT_TYPES}
            )
        
        return report_type
    
    @classmethod
    def validate_format(cls, format_type: str) -> str:
        """
        Valida el formato de reporte
        
        Args:
            format_type: Formato del reporte
            
        Returns:
            str: Formato validado
            
        Raises:
            ValidationError: Si el formato es inválido
        """
        if not format_type:
            return 'xlsx'  # Valor por defecto
        
        if format_type not in cls.VALID_FORMATS:
            raise ValidationError(
                f"Formato de reporte inválido. Valores permitidos: {', '.join(cls.VALID_FORMATS)}",
                field="format",
                details={'provided_value': format_type, 'valid_values': cls.VALID_FORMATS}
            )
        
        return format_type


class RegionValidator:
    """Validador para regiones de API"""
    
    VALID_REGIONS = ['eu1', 'eu2', 'eu3', 'eu4', 'eu5', 'br1', 'br2', 'mx1', 'demo1']
    
    @classmethod
    def validate_region(cls, region: str) -> str:
        """
        Valida una región de API
        
        Args:
            region: Región a validar
            
        Returns:
            str: Región validada
            
        Raises:
            ValidationError: Si la región es inválida
        """
        if not region:
            return 'eu1'  # Valor por defecto
        
        if region not in cls.VALID_REGIONS:
            raise ValidationError(
                f"Región inválida. Valores permitidos: {', '.join(cls.VALID_REGIONS)}",
                field="region",
                details={'provided_value': region, 'valid_values': cls.VALID_REGIONS}
            )
        
        return region