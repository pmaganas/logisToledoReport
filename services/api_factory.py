"""
Factory para crear instancias de API
"""
from typing import Union, Optional, Protocol
from abc import ABC, abstractmethod

from config.settings import get_settings
from models import SesameToken
from exceptions import TokenNotFoundError, APIError


class SesameAPIProtocol(Protocol):
    """Protocolo que define la interfaz común de las APIs de Sesame"""
    
    def get_token_info(self) -> Optional[dict]:
        """Obtener información del token"""
        ...
    
    def get_offices(self) -> Optional[dict]:
        """Obtener lista de oficinas"""
        ...
    
    def get_departments(self) -> Optional[dict]:
        """Obtener lista de departamentos"""
        ...
    
    def get_time_tracking(
        self, 
        employee_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        office_id: Optional[str] = None,
        department_id: Optional[str] = None,
        page: int = 1
    ) -> Optional[dict]:
        """Obtener datos de seguimiento de tiempo"""
        ...


class APIFactory:
    """Factory para crear instancias de API de Sesame"""
    
    _instances = {}  # Cache de instancias
    
    @classmethod
    def create_api(
        cls, 
        parallel: bool = False, 
        force_new: bool = False
    ) -> SesameAPIProtocol:
        """
        Crear instancia de API de Sesame
        
        Args:
            parallel: Si usar la API paralela para mejor rendimiento
            force_new: Forzar creación de nueva instancia (no usar cache)
            
        Returns:
            Instancia de API de Sesame
            
        Raises:
            TokenNotFoundError: Si no hay token configurado
            APIError: Si hay error en la configuración
        """
        # Verificar que hay token activo
        active_token = SesameToken.get_active_token()
        if not active_token:
            raise TokenNotFoundError("No hay token de API configurado")
        
        # Crear clave de cache
        cache_key = f"{'parallel' if parallel else 'standard'}_{active_token.id}"
        
        # Usar instancia cacheada si existe y no se fuerza nueva
        if not force_new and cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Crear nueva instancia
        try:
            if parallel:
                from services.parallel_sesame_api import ParallelSesameAPI
                instance = ParallelSesameAPI()
            else:
                from services.sesame_api import SesameAPI
                instance = SesameAPI()
            
            # Cachear instancia
            cls._instances[cache_key] = instance
            
            return instance
            
        except ImportError as e:
            raise APIError(f"Error importando clase de API: {str(e)}", original_error=e)
        except Exception as e:
            raise APIError(f"Error creando instancia de API: {str(e)}", original_error=e)
    
    @classmethod
    def create_standard_api(cls, force_new: bool = False) -> SesameAPIProtocol:
        """
        Crear instancia de API estándar
        
        Args:
            force_new: Forzar creación de nueva instancia
            
        Returns:
            Instancia de API estándar
        """
        return cls.create_api(parallel=False, force_new=force_new)
    
    @classmethod
    def create_parallel_api(cls, force_new: bool = False) -> SesameAPIProtocol:
        """
        Crear instancia de API paralela
        
        Args:
            force_new: Forzar creación de nueva instancia
            
        Returns:
            Instancia de API paralela
        """
        return cls.create_api(parallel=True, force_new=force_new)
    
    @classmethod
    def get_recommended_api(cls, estimated_records: int = 100) -> SesameAPIProtocol:
        """
        Obtener API recomendada basada en la cantidad estimada de registros
        
        Args:
            estimated_records: Número estimado de registros a procesar
            
        Returns:
            Instancia de API recomendada
        """
        settings = get_settings()
        
        # Usar API paralela para grandes volúmenes de datos
        use_parallel = estimated_records > settings.api.page_size * 2
        
        return cls.create_api(parallel=use_parallel)
    
    @classmethod
    def clear_cache(cls):
        """Limpiar cache de instancias"""
        cls._instances.clear()
    
    @classmethod
    def refresh_instances(cls):
        """Refrescar todas las instancias cacheadas"""
        cls.clear_cache()
        # Las instancias se recrearán automáticamente en el próximo uso


class APIConnectionManager:
    """Gestor de conexiones de API"""
    
    def __init__(self, api_factory: APIFactory = None):
        self.api_factory = api_factory or APIFactory
        self._connection_tested = False
        self._last_test_result = None
    
    def test_connection(self, parallel: bool = False) -> dict:
        """
        Probar conexión con la API
        
        Args:
            parallel: Si probar con API paralela
            
        Returns:
            Diccionario con resultado de la prueba
        """
        try:
            api = self.api_factory.create_api(parallel=parallel, force_new=True)
            result = api.get_token_info()
            
            if result:
                self._connection_tested = True
                self._last_test_result = {
                    'success': True,
                    'message': 'Conexión exitosa',
                    'data': result
                }
            else:
                self._last_test_result = {
                    'success': False,
                    'message': 'No se pudo conectar a la API'
                }
            
            return self._last_test_result
            
        except Exception as e:
            self._last_test_result = {
                'success': False,
                'message': f'Error de conexión: {str(e)}',
                'error': str(e)
            }
            return self._last_test_result
    
    def is_connection_healthy(self) -> bool:
        """
        Verificar si la conexión está saludable
        
        Returns:
            True si la conexión está OK
        """
        return self._connection_tested and self._last_test_result and self._last_test_result.get('success', False)
    
    def get_last_test_result(self) -> Optional[dict]:
        """Obtener resultado de la última prueba de conexión"""
        return self._last_test_result


# Instancia global del gestor de conexiones
connection_manager = APIConnectionManager()


def get_api_for_report(
    report_type: str = "by_employee",
    estimated_records: int = 100
) -> SesameAPIProtocol:
    """
    Obtener API optimizada para generación de reportes
    
    Args:
        report_type: Tipo de reporte
        estimated_records: Registros estimados
        
    Returns:
        Instancia de API optimizada
    """
    # Reportes que típicamente requieren más datos
    heavy_report_types = ['by_activity', 'summary']
    
    if report_type in heavy_report_types:
        # Usar API paralela para reportes pesados
        return APIFactory.create_parallel_api()
    else:
        # Usar API recomendada basada en registros estimados
        return APIFactory.get_recommended_api(estimated_records)


def get_api_for_metadata() -> SesameAPIProtocol:
    """
    Obtener API optimizada para obtener metadatos (oficinas, departamentos, etc.)
    
    Returns:
        Instancia de API estándar (los metadatos no requieren paralelismo)
    """
    return APIFactory.create_standard_api()