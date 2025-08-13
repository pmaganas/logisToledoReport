"""
Servicio híbrido de reportes que combina compatibilidad con optimizaciones turbo
"""
import asyncio
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
import threading
import time

from services.turbo_report_generator import TurboReportGenerator, ReportConfig, generate_turbo_report
from services.no_breaks_report_generator import NoBreaksReportGenerator
from utils.logging_config import get_logger
from config.settings import get_settings
from exceptions import ReportGenerationError


class HybridReportService:
    """
    Servicio híbrido que selecciona automáticamente la mejor estrategia de generación
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.turbo_generator = TurboReportGenerator()
        self.legacy_generator = NoBreaksReportGenerator()
        
        # Configuración de thresholds para decidir estrategia
        self.turbo_threshold_records = 1000  # Usar turbo para +1000 registros estimados
        self.turbo_threshold_pages = 5       # Usar turbo para +5 páginas estimadas
    
    def generate_report_hybrid(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        employee_id: Optional[str] = None,
        office_id: Optional[str] = None,
        department_id: Optional[str] = None,
        report_type: str = "by_employee",
        format_type: str = "xlsx",
        progress_callback: Optional[Callable] = None,
        force_turbo: bool = False,
        force_legacy: bool = False
    ) -> bytes:
        """
        Generar reporte usando estrategia híbrida óptima
        
        Args:
            from_date: Fecha inicial
            to_date: Fecha final
            employee_id: ID del empleado
            office_id: ID de oficina
            department_id: ID de departamento
            report_type: Tipo de reporte
            format_type: Formato de archivo
            progress_callback: Callback de progreso
            force_turbo: Forzar uso de generador turbo
            force_legacy: Forzar uso de generador legacy
            
        Returns:
            Datos del reporte en bytes
        """
        start_time = time.time()
        
        # Crear configuración del reporte
        config = ReportConfig(
            from_date=from_date,
            to_date=to_date,
            employee_id=employee_id,
            office_id=office_id,
            department_id=department_id,
            report_type=report_type,
            format_type=format_type,
            use_compression=False,  # Comprimir solo para archivos muy grandes
            enable_streaming=True,
            max_concurrent_requests=min(20, self.settings.api.pool_maxsize * 2),
            chunk_size=self.settings.reports.chunk_size
        )
        
        try:
            # Decidir estrategia de generación
            if force_legacy:
                strategy = "legacy"
                self.logger.info("🔄 Usando generador LEGACY (forzado)")
            elif force_turbo:
                strategy = "turbo"
                self.logger.info("🚀 Usando generador TURBO (forzado)")
            else:
                strategy = self._decide_generation_strategy(config)
            
            # Generar reporte usando la estrategia seleccionada
            if strategy == "turbo":
                report_bytes = self._generate_with_turbo(config, progress_callback)
            else:
                report_bytes = self._generate_with_legacy(config, progress_callback)
            
            generation_time = time.time() - start_time
            self.logger.info(f"✅ Reporte híbrido completado usando {strategy.upper()} en {generation_time:.2f}s")
            
            return report_bytes
            
        except Exception as e:
            self.logger.error(f"❌ Error en generación híbrida: {str(e)}")
            
            # Fallback: si turbo falla, intentar legacy
            if strategy == "turbo" and not force_turbo:
                self.logger.warning("⚠️ Turbo falló, intentando fallback a legacy...")
                try:
                    return self._generate_with_legacy(config, progress_callback)
                except Exception as fallback_error:
                    self.logger.error(f"❌ Fallback legacy también falló: {str(fallback_error)}")
                    raise ReportGenerationError(
                        f"Error en generación turbo y fallback: {str(e)} | {str(fallback_error)}"
                    )
            
            raise ReportGenerationError(f"Error en generación híbrida: {str(e)}", original_error=e)
    
    def _decide_generation_strategy(self, config: ReportConfig) -> str:
        """
        Decidir qué estrategia de generación usar basada en estimaciones
        
        Args:
            config: Configuración del reporte
            
        Returns:
            'turbo' o 'legacy'
        """
        try:
            # Estimar volumen de datos basado en parámetros
            estimated_records = self._estimate_record_count(config)
            estimated_pages = max(1, estimated_records // self.settings.api.page_size)
            
            self.logger.info(f"📊 Estimación: ~{estimated_records} registros en ~{estimated_pages} páginas")
            
            # Criterios para usar turbo
            use_turbo = (
                estimated_records >= self.turbo_threshold_records or
                estimated_pages >= self.turbo_threshold_pages or
                config.format_type == 'csv'  # CSV se beneficia más del streaming
            )
            
            strategy = "turbo" if use_turbo else "legacy"
            
            self.logger.info(
                f"🎯 Estrategia seleccionada: {strategy.upper()} "
                f"(registros: {estimated_records}, páginas: {estimated_pages})"
            )
            
            return strategy
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error estimando, usando legacy por seguridad: {str(e)}")
            return "legacy"
    
    def _estimate_record_count(self, config: ReportConfig) -> int:
        """
        Estimar cantidad de registros basado en parámetros
        
        Args:
            config: Configuración del reporte
            
        Returns:
            Estimación de registros
        """
        base_estimate = 100  # Estimación base mínima
        
        # Factor por empleado específico vs todos
        if config.employee_id:
            employee_factor = 1.0
        else:
            employee_factor = 10.0  # Múltiples empleados
        
        # Factor por rango de fechas
        if config.from_date and config.to_date:
            try:
                from_dt = datetime.strptime(config.from_date, '%Y-%m-%d')
                to_dt = datetime.strptime(config.to_date, '%Y-%m-%d')
                days_diff = (to_dt - from_dt).days + 1
                
                # Estimar registros por día
                records_per_day = 2 if config.employee_id else 20  # Entrada/salida por empleado promedio
                date_factor = days_diff * records_per_day
            except:
                date_factor = 100  # Fallback si no se pueden parsear fechas
        else:
            date_factor = 50  # Un día promedio
        
        # Factor por oficina/departamento
        if config.office_id or config.department_id:
            scope_factor = 5.0  # Oficina/departamento específico
        else:
            scope_factor = 20.0  # Toda la empresa
        
        # Calcular estimación final
        estimated = int(base_estimate * employee_factor * date_factor * scope_factor / 100)
        
        # Límites razonables
        return max(10, min(estimated, 50000))
    
    def _generate_with_turbo(self, config: ReportConfig, progress_callback: Optional[Callable]) -> bytes:
        """Generar usando motor turbo"""
        self.logger.info("🚀 Iniciando generación TURBO...")
        
        # Ejecutar generación asíncrona en thread separado
        def run_turbo():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    generate_turbo_report(config, progress_callback)
                )
            finally:
                loop.close()
        
        # Ejecutar en thread para no bloquear
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_turbo)
            return future.result(timeout=600)  # 10 minutos timeout
    
    def _generate_with_legacy(self, config: ReportConfig, progress_callback: Optional[Callable]) -> bytes:
        """Generar usando motor legacy"""
        self.logger.info("🔄 Iniciando generación LEGACY...")
        
        return self.legacy_generator.generate_report(
            from_date=config.from_date,
            to_date=config.to_date,
            employee_id=config.employee_id,
            office_id=config.office_id,
            department_id=config.department_id,
            report_type=config.report_type,
            format=config.format_type,
            progress_callback=progress_callback
        )
    
    def get_performance_comparison(self) -> Dict[str, Any]:
        """
        Obtener comparación de performance entre estrategias
        
        Returns:
            Diccionario con métricas comparativas
        """
        try:
            turbo_metrics = self.turbo_generator.get_performance_metrics()
            
            return {
                'strategy_thresholds': {
                    'turbo_threshold_records': self.turbo_threshold_records,
                    'turbo_threshold_pages': self.turbo_threshold_pages
                },
                'turbo_performance': turbo_metrics,
                'recommendations': {
                    'use_turbo_when': [
                        f"Más de {self.turbo_threshold_records} registros estimados",
                        f"Más de {self.turbo_threshold_pages} páginas de datos",
                        "Formato CSV (se beneficia del streaming)",
                        "Reportes de múltiples empleados",
                        "Rangos de fechas amplios (>7 días)"
                    ],
                    'use_legacy_when': [
                        "Pocos registros (<1000)",
                        "Un solo empleado y fecha específica",
                        "Necesitas compatibilidad 100% con código existente",
                        "Reportes simples y rápidos"
                    ]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas de comparación: {str(e)}")
            return {
                'error': str(e),
                'strategy_thresholds': {
                    'turbo_threshold_records': self.turbo_threshold_records,
                    'turbo_threshold_pages': self.turbo_threshold_pages
                }
            }
    
    def configure_thresholds(
        self,
        turbo_threshold_records: Optional[int] = None,
        turbo_threshold_pages: Optional[int] = None
    ):
        """
        Configurar thresholds para decisión de estrategia
        
        Args:
            turbo_threshold_records: Threshold de registros para usar turbo
            turbo_threshold_pages: Threshold de páginas para usar turbo
        """
        if turbo_threshold_records is not None:
            self.turbo_threshold_records = turbo_threshold_records
            self.logger.info(f"🎯 Threshold de registros para turbo: {turbo_threshold_records}")
        
        if turbo_threshold_pages is not None:
            self.turbo_threshold_pages = turbo_threshold_pages
            self.logger.info(f"🎯 Threshold de páginas para turbo: {turbo_threshold_pages}")


# Instancia global del servicio híbrido
hybrid_service = HybridReportService()


def generate_report_smart(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    employee_id: Optional[str] = None,
    office_id: Optional[str] = None,
    department_id: Optional[str] = None,
    report_type: str = "by_employee",
    format_type: str = "xlsx",
    progress_callback: Optional[Callable] = None,
    force_turbo: bool = False
) -> bytes:
    """
    Función de conveniencia para generar reportes con selección automática de estrategia
    
    Args:
        from_date: Fecha inicial
        to_date: Fecha final  
        employee_id: ID del empleado
        office_id: ID de oficina
        department_id: ID de departamento
        report_type: Tipo de reporte
        format_type: Formato ('xlsx' o 'csv')
        progress_callback: Callback de progreso
        force_turbo: Forzar uso de motor turbo
        
    Returns:
        Datos del reporte en bytes
    """
    return hybrid_service.generate_report_hybrid(
        from_date=from_date,
        to_date=to_date,
        employee_id=employee_id,
        office_id=office_id,
        department_id=department_id,
        report_type=report_type,
        format_type=format_type,
        progress_callback=progress_callback,
        force_turbo=force_turbo
    )