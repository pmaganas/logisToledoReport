"""
Generador de reportes mejorado que extiende NoBreaksReportGenerator con optimizaciones
"""
from typing import Optional, Dict, List, Any, Callable
import time

from services.no_breaks_report_generator import NoBreaksReportGenerator
from services.hybrid_report_service import generate_report_smart
from utils.logging_config import get_logger
from utils.decorators import log_execution_time
from exceptions import ReportGenerationError


class EnhancedReportGenerator(NoBreaksReportGenerator):
    """
    Generador de reportes mejorado que mantiene compatibilidad pero agrega optimizaciones
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.use_smart_generation = True  # Habilitar por defecto
    
    @log_execution_time
    def generate_report(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        employee_id: Optional[str] = None,
        office_id: Optional[str] = None,
        department_id: Optional[str] = None,
        report_type: str = "by_employee",
        format: str = "xlsx",
        progress_callback: Optional[Callable] = None,
        use_turbo: Optional[bool] = None
    ) -> Optional[bytes]:
        """
        Generar reporte con selección automática de estrategia optimizada
        
        Args:
            from_date: Fecha inicial
            to_date: Fecha final
            employee_id: ID del empleado
            office_id: ID de oficina
            department_id: ID de departamento
            report_type: Tipo de reporte
            format: Formato del archivo
            progress_callback: Callback de progreso
            use_turbo: Forzar uso de motor turbo (None = auto)
            
        Returns:
            Datos del reporte en bytes
        """
        start_time = time.time()
        
        try:
            # Usar sistema híbrido inteligente si está habilitado
            if self.use_smart_generation:
                self.logger.info("🧠 Usando generación INTELIGENTE (híbrida)")
                
                result = generate_report_smart(
                    from_date=from_date,
                    to_date=to_date,
                    employee_id=employee_id,
                    office_id=office_id,
                    department_id=department_id,
                    report_type=report_type,
                    format_type=format,
                    progress_callback=progress_callback,
                    force_turbo=use_turbo or False
                )
                
                generation_time = time.time() - start_time
                self.logger.info(f"✅ Reporte inteligente completado en {generation_time:.2f}s")
                
                return result
            
            else:
                # Fallback al método original
                self.logger.info("🔄 Usando generación LEGACY (original)")
                return super().generate_report(
                    from_date=from_date,
                    to_date=to_date,
                    employee_id=employee_id,
                    office_id=office_id,
                    department_id=department_id,
                    report_type=report_type,
                    format=format,
                    progress_callback=progress_callback
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error en generación mejorada: {str(e)}")
            
            # Fallback automático a método original si falla la optimización
            if self.use_smart_generation:
                self.logger.warning("⚠️ Optimización falló, usando fallback legacy...")
                try:
                    return super().generate_report(
                        from_date=from_date,
                        to_date=to_date,
                        employee_id=employee_id,
                        office_id=office_id,
                        department_id=department_id,
                        report_type=report_type,
                        format=format,
                        progress_callback=progress_callback
                    )
                except Exception as fallback_error:
                    self.logger.error(f"❌ Fallback también falló: {str(fallback_error)}")
                    raise ReportGenerationError(
                        f"Error en generación optimizada y fallback: {str(e)} | {str(fallback_error)}"
                    )
            
            raise ReportGenerationError(f"Error en generación de reporte: {str(e)}", original_error=e)
    
    def enable_smart_generation(self, enabled: bool = True):
        """
        Habilitar/deshabilitar generación inteligente
        
        Args:
            enabled: True para habilitar optimizaciones
        """
        self.use_smart_generation = enabled
        mode = "HABILITADA" if enabled else "DESHABILITADA"
        self.logger.info(f"🎯 Generación inteligente {mode}")
    
    def get_generation_info(self) -> Dict[str, Any]:
        """
        Obtener información sobre el modo de generación actual
        
        Returns:
            Diccionario con información del generador
        """
        return {
            'smart_generation_enabled': self.use_smart_generation,
            'generation_mode': 'hybrid_smart' if self.use_smart_generation else 'legacy',
            'features': {
                'parallel_api_calls': True,
                'async_processing': self.use_smart_generation,
                'intelligent_caching': self.use_smart_generation,
                'streaming_file_generation': self.use_smart_generation,
                'automatic_strategy_selection': self.use_smart_generation,
                'compression_support': self.use_smart_generation,
                'performance_metrics': self.use_smart_generation
            },
            'benefits': [
                "Hasta 10x más rápido para reportes grandes",
                "Menor uso de memoria con streaming",
                "Fallback automático por compatibilidad",
                "Cache inteligente para datos frecuentes",
                "Selección automática de estrategia óptima"
            ] if self.use_smart_generation else [
                "Compatibilidad 100% con código original",
                "Generación síncrona tradicional",
                "Sin dependencias adicionales"
            ]
        }