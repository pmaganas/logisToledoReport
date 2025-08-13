"""
Modelos de respuesta para APIs
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import json


@dataclass
class BaseResponse:
    """Respuesta base para todas las APIs"""
    status: str
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convertir a JSON"""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class SuccessResponse(BaseResponse):
    """Respuesta exitosa"""
    data: Optional[Any] = None
    
    def __post_init__(self):
        self.status = 'success'


@dataclass
class ErrorResponse(BaseResponse):
    """Respuesta de error"""
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        self.status = 'error'


@dataclass
class ValidationErrorResponse(ErrorResponse):
    """Respuesta de error de validación"""
    field: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.error_code = self.error_code or 'VALIDATION_ERROR'


@dataclass
class APIConnectionResponse(BaseResponse):
    """Respuesta de conexión a la API"""
    connected: bool
    company_name: Optional[str] = None
    token_info: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.connected:
            self.status = 'success'
            self.message = self.message or 'Conexión exitosa'
        else:
            self.status = 'error'
            self.message = self.message or 'Error de conexión'


@dataclass
class TokenInfo:
    """Información de token"""
    masked_token: str
    region: str
    description: Optional[str]
    created_at: datetime
    company_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'masked_token': self.masked_token,
            'region': self.region,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'company_name': self.company_name
        }


@dataclass
class TokenResponse(SuccessResponse):
    """Respuesta de información de token"""
    has_token: bool
    token_info: Optional[TokenInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.token_info:
            result['token_info'] = self.token_info.to_dict()
        return result


@dataclass
class ReportProgress:
    """Progreso de generación de reporte"""
    current_page: int
    total_pages: int
    current_records: int
    total_records: int
    pagination_complete: bool = False
    
    @property
    def percentage(self) -> float:
        """Calcular porcentaje de progreso"""
        if self.total_pages == 0:
            return 0.0
        return min((self.current_page / self.total_pages) * 100, 100.0)


@dataclass
class ReportStatus:
    """Estado de un reporte"""
    report_id: str
    status: str  # 'starting', 'processing', 'completed', 'error', 'cancelled'
    created_at: datetime
    filename: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[ReportProgress] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'report_id': self.report_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'filename': self.filename,
            'error': self.error
        }
        
        if self.progress:
            result['progress'] = {
                'current_page': self.progress.current_page,
                'total_pages': self.progress.total_pages,
                'current_records': self.progress.current_records,
                'total_records': self.progress.total_records,
                'pagination_complete': self.progress.pagination_complete,
                'percentage': self.progress.percentage
            }
        
        return result


@dataclass
class ReportStatusResponse(SuccessResponse):
    """Respuesta del estado de un reporte"""
    report_status: ReportStatus
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['report_status'] = self.report_status.to_dict()
        return result


@dataclass
class ReportFile:
    """Información de archivo de reporte"""
    report_id: str
    filename: str
    original_filename: str
    created_at: datetime
    size_mb: float
    file_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'created_at': self.created_at.isoformat(),
            'size_mb': self.size_mb,
            'file_path': self.file_path
        }


@dataclass
class ReportListResponse(SuccessResponse):
    """Respuesta con lista de reportes"""
    reports: List[ReportFile]
    max_reports: int
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['reports'] = [report.to_dict() for report in self.reports]
        result['max_reports'] = self.max_reports
        return result


@dataclass
class ProcessingReportsResponse(SuccessResponse):
    """Respuesta con reportes en procesamiento"""
    has_processing: bool
    processing_count: int
    reports: List[ReportStatus]
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['has_processing'] = self.has_processing
        result['processing_count'] = self.processing_count
        result['reports'] = [report.to_dict() for report in self.reports]
        return result


@dataclass
class Office:
    """Información de oficina"""
    id: str
    name: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


@dataclass
class Department:
    """Información de departamento"""
    id: str
    name: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


@dataclass
class OfficesResponse(SuccessResponse):
    """Respuesta con lista de oficinas"""
    offices: List[Office]
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['offices'] = [office.to_dict() for office in self.offices]
        return result


@dataclass
class DepartmentsResponse(SuccessResponse):
    """Respuesta con lista de departamentos"""
    departments: List[Department]
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['departments'] = [dept.to_dict() for dept in self.departments]
        return result


class ResponseBuilder:
    """Constructor de respuestas"""
    
    @staticmethod
    def success(message: str, data: Any = None) -> SuccessResponse:
        """Crear respuesta exitosa"""
        return SuccessResponse(message=message, data=data)
    
    @staticmethod
    def error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ErrorResponse:
        """Crear respuesta de error"""
        return ErrorResponse(message=message, error_code=error_code, details=details)
    
    @staticmethod
    def validation_error(
        message: str, 
        field: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ) -> ValidationErrorResponse:
        """Crear respuesta de error de validación"""
        return ValidationErrorResponse(message=message, field=field, details=details)
    
    @staticmethod
    def api_connection(
        connected: bool, 
        message: Optional[str] = None,
        company_name: Optional[str] = None,
        token_info: Optional[Dict[str, Any]] = None
    ) -> APIConnectionResponse:
        """Crear respuesta de conexión API"""
        return APIConnectionResponse(
            message=message or '',
            connected=connected,
            company_name=company_name,
            token_info=token_info
        )
    
    @staticmethod
    def token_info(
        has_token: bool,
        token_info: Optional[TokenInfo] = None,
        message: Optional[str] = None
    ) -> TokenResponse:
        """Crear respuesta de información de token"""
        return TokenResponse(
            message=message or ('Token encontrado' if has_token else 'No hay token configurado'),
            has_token=has_token,
            token_info=token_info
        )
    
    @staticmethod
    def report_status(report_status: ReportStatus, message: Optional[str] = None) -> ReportStatusResponse:
        """Crear respuesta de estado de reporte"""
        return ReportStatusResponse(
            message=message or 'Estado del reporte obtenido',
            report_status=report_status
        )
    
    @staticmethod
    def report_list(reports: List[ReportFile], max_reports: int) -> ReportListResponse:
        """Crear respuesta con lista de reportes"""
        return ReportListResponse(
            message=f'Se encontraron {len(reports)} reportes',
            reports=reports,
            max_reports=max_reports
        )
    
    @staticmethod
    def offices(offices: List[Office]) -> OfficesResponse:
        """Crear respuesta con lista de oficinas"""
        return OfficesResponse(
            message=f'Se encontraron {len(offices)} oficinas',
            offices=offices
        )
    
    @staticmethod
    def departments(departments: List[Department]) -> DepartmentsResponse:
        """Crear respuesta con lista de departamentos"""
        return DepartmentsResponse(
            message=f'Se encontraron {len(departments)} departamentos',
            departments=departments
        )