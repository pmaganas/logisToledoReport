"""
Utilidades optimizadas para manejo de archivos
"""
import os
import glob
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import uuid

from config.settings import get_settings
from exceptions import ReportFileError, ReportLimitExceededError, ReportNotFoundError


class FileManager:
    """Gestor optimizado de archivos de reporte"""
    
    def __init__(self):
        self.settings = get_settings()
        self.temp_dir = Path(self.settings.reports.temp_dir)
        self.max_reports = self.settings.reports.max_reports
        self.logger = logging.getLogger(__name__)
        
        # Crear directorio si no existe
        self.temp_dir.mkdir(exist_ok=True)
    
    def save_report(
        self, 
        report_data: bytes, 
        report_id: str, 
        format_type: str = 'xlsx',
        custom_filename: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Guardar reporte en archivo temporal
        
        Args:
            report_data: Datos del reporte en bytes
            report_id: ID único del reporte
            format_type: Formato del archivo ('xlsx' o 'csv')
            custom_filename: Nombre personalizado (opcional)
            
        Returns:
            Tuple[str, str]: (file_path, filename)
            
        Raises:
            ReportFileError: Si hay error al guardar
        """
        try:
            # Generar nombre de archivo
            if custom_filename:
                filename = custom_filename
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                extension = 'csv' if format_type == 'csv' else 'xlsx'
                filename = f"reporte_actividades_{timestamp}.{extension}"
            
            # Añadir prefijo con report_id para identificación
            file_path = self.temp_dir / f"{report_id}_{filename}"
            
            # Verificar límite de reportes antes de guardar
            self._check_report_limit()
            
            # Guardar archivo
            with open(file_path, 'wb') as f:
                f.write(report_data)
            
            self.logger.info(f"Reporte guardado: {file_path} ({len(report_data)} bytes)")
            
            return str(file_path), filename
            
        except Exception as e:
            self.logger.error(f"Error guardando reporte {report_id}: {str(e)}")
            raise ReportFileError(
                f"Error al guardar reporte: {str(e)}",
                file_path=str(file_path) if 'file_path' in locals() else None,
                original_error=e
            )
    
    def get_report_file(self, report_id: str) -> Tuple[str, str]:
        """
        Obtener ruta y nombre de archivo de un reporte
        
        Args:
            report_id: ID del reporte
            
        Returns:
            Tuple[str, str]: (file_path, original_filename)
            
        Raises:
            ReportNotFoundError: Si el reporte no existe
        """
        pattern = str(self.temp_dir / f"{report_id}_*")
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            raise ReportNotFoundError(
                f"Reporte no encontrado: {report_id}",
                report_id=report_id
            )
        
        file_path = matching_files[0]
        
        # Extraer nombre original del archivo
        filename = os.path.basename(file_path)
        parts = filename.split('_', 1)
        original_filename = parts[1] if len(parts) > 1 else filename
        
        return file_path, original_filename
    
    def delete_report(self, report_id: str) -> bool:
        """
        Eliminar archivo de reporte
        
        Args:
            report_id: ID del reporte
            
        Returns:
            bool: True si se eliminó exitosamente
            
        Raises:
            ReportNotFoundError: Si el reporte no existe
        """
        try:
            file_path, _ = self.get_report_file(report_id)
            
            os.remove(file_path)
            self.logger.info(f"Reporte eliminado: {file_path}")
            
            return True
            
        except FileNotFoundError:
            raise ReportNotFoundError(
                f"Reporte no encontrado para eliminar: {report_id}",
                report_id=report_id
            )
        except Exception as e:
            self.logger.error(f"Error eliminando reporte {report_id}: {str(e)}")
            raise ReportFileError(
                f"Error al eliminar reporte: {str(e)}",
                original_error=e
            )
    
    def list_reports(self) -> List[Dict[str, Any]]:
        """
        Listar todos los reportes disponibles
        
        Returns:
            Lista de diccionarios con información de reportes
        """
        reports = []
        
        try:
            # Buscar archivos de reporte
            patterns = [
                str(self.temp_dir / "*.xlsx"),
                str(self.temp_dir / "*.csv")
            ]
            
            report_files = []
            for pattern in patterns:
                report_files.extend(glob.glob(pattern))
            
            for file_path in report_files:
                try:
                    filename = os.path.basename(file_path)
                    
                    # Extraer report_id y timestamp
                    parts = filename.split('_')
                    if len(parts) >= 4:
                        report_id = parts[0]
                        timestamp_str = '_'.join(parts[-2:]).rsplit('.', 1)[0]
                        
                        # Parse timestamp
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        except ValueError:
                            timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        # Obtener tamaño del archivo
                        file_size = os.path.getsize(file_path)
                        file_size_mb = round(file_size / (1024 * 1024), 2)
                        
                        # Extraer nombre original
                        original_parts = filename.split('_', 1)
                        original_filename = original_parts[1] if len(original_parts) > 1 else filename
                        
                        reports.append({
                            'report_id': report_id,
                            'filename': filename,
                            'original_filename': original_filename,
                            'created_at': timestamp,
                            'size_mb': file_size_mb,
                            'file_path': file_path,
                            'format': 'csv' if filename.endswith('.csv') else 'xlsx'
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Error procesando archivo {file_path}: {str(e)}")
                    continue
            
            # Ordenar por fecha de creación (más reciente primero)
            reports.sort(key=lambda x: x['created_at'], reverse=True)
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Error listando reportes: {str(e)}")
            return []
    
    def enforce_report_limit(self) -> List[str]:
        """
        Aplicar límite de reportes, eliminando los más antiguos
        
        Returns:
            Lista de nombres de archivos eliminados
        """
        deleted_files = []
        
        try:
            reports = self.list_reports()
            
            if len(reports) <= self.max_reports:
                return deleted_files
            
            # Calcular cuántos archivos eliminar
            files_to_delete = len(reports) - self.max_reports
            
            # Eliminar los más antiguos (los últimos en la lista ordenada)
            for i in range(files_to_delete):
                report_to_delete = reports[-(i + 1)]  # Empezar desde el final
                
                try:
                    os.remove(report_to_delete['file_path'])
                    deleted_files.append(report_to_delete['filename'])
                    
                    self.logger.info(
                        f"Archivo eliminado por límite: {report_to_delete['filename']} "
                        f"(límite: {self.max_reports})"
                    )
                    
                except Exception as e:
                    self.logger.warning(
                        f"Error eliminando archivo por límite {report_to_delete['file_path']}: {str(e)}"
                    )
            
            return deleted_files
            
        except Exception as e:
            self.logger.error(f"Error aplicando límite de reportes: {str(e)}")
            return deleted_files
    
    def _check_report_limit(self):
        """
        Verificar límite de reportes antes de crear uno nuevo
        
        Raises:
            ReportLimitExceededError: Si se excede el límite
        """
        current_reports = self.list_reports()
        
        if len(current_reports) >= self.max_reports:
            # Intentar limpiar automáticamente
            deleted = self.enforce_report_limit()
            
            # Verificar si aún se excede el límite
            current_reports = self.list_reports()
            if len(current_reports) >= self.max_reports:
                raise ReportLimitExceededError(
                    f"Límite de reportes excedido",
                    current_count=len(current_reports),
                    max_allowed=self.max_reports
                )
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de almacenamiento
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            reports = self.list_reports()
            
            total_size = sum(report['size_mb'] for report in reports)
            total_files = len(reports)
            
            # Estadísticas por formato
            xlsx_files = [r for r in reports if r['format'] == 'xlsx']
            csv_files = [r for r in reports if r['format'] == 'csv']
            
            return {
                'total_files': total_files,
                'total_size_mb': round(total_size, 2),
                'max_reports': self.max_reports,
                'available_slots': max(0, self.max_reports - total_files),
                'xlsx_files': len(xlsx_files),
                'csv_files': len(csv_files),
                'oldest_report': min(reports, key=lambda x: x['created_at'])['created_at'] if reports else None,
                'newest_report': max(reports, key=lambda x: x['created_at'])['created_at'] if reports else None
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'max_reports': self.max_reports,
                'available_slots': self.max_reports,
                'xlsx_files': 0,
                'csv_files': 0,
                'oldest_report': None,
                'newest_report': None,
                'error': str(e)
            }
    
    def cleanup_orphaned_files(self) -> List[str]:
        """
        Limpiar archivos huérfanos (sin report_id válido)
        
        Returns:
            Lista de archivos eliminados
        """
        cleaned_files = []
        
        try:
            # Buscar todos los archivos
            all_files = glob.glob(str(self.temp_dir / "*"))
            
            for file_path in all_files:
                filename = os.path.basename(file_path)
                
                # Verificar si el archivo tiene formato de report_id válido
                if not self._is_valid_report_file(filename):
                    try:
                        os.remove(file_path)
                        cleaned_files.append(filename)
                        self.logger.info(f"Archivo huérfano eliminado: {filename}")
                    except Exception as e:
                        self.logger.warning(f"Error eliminando archivo huérfano {filename}: {str(e)}")
            
            return cleaned_files
            
        except Exception as e:
            self.logger.error(f"Error limpiando archivos huérfanos: {str(e)}")
            return cleaned_files
    
    def _is_valid_report_file(self, filename: str) -> bool:
        """
        Verificar si un archivo tiene formato válido de reporte
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            bool: True si es válido
        """
        import re
        
        # Patrón: {uuid}_reporte_actividades_{timestamp}.{ext}
        pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_.*\.(xlsx|csv)$'
        
        return bool(re.match(pattern, filename))


# Instancia global del gestor de archivos
file_manager = FileManager()


def save_report_file(
    report_data: bytes, 
    report_id: str, 
    format_type: str = 'xlsx'
) -> Tuple[str, str]:
    """
    Función de conveniencia para guardar reporte
    
    Args:
        report_data: Datos del reporte
        report_id: ID del reporte
        format_type: Formato del archivo
        
    Returns:
        Tuple[str, str]: (file_path, filename)
    """
    return file_manager.save_report(report_data, report_id, format_type)


def get_report_file_info(report_id: str) -> Tuple[str, str]:
    """
    Función de conveniencia para obtener info de reporte
    
    Args:
        report_id: ID del reporte
        
    Returns:
        Tuple[str, str]: (file_path, original_filename)
    """
    return file_manager.get_report_file(report_id)


def delete_report_file(report_id: str) -> bool:
    """
    Función de conveniencia para eliminar reporte
    
    Args:
        report_id: ID del reporte
        
    Returns:
        bool: True si se eliminó exitosamente
    """
    return file_manager.delete_report(report_id)


def list_available_reports() -> List[Dict[str, Any]]:
    """
    Función de conveniencia para listar reportes
    
    Returns:
        Lista de reportes disponibles
    """
    return file_manager.list_reports()


def get_file_storage_stats() -> Dict[str, Any]:
    """
    Función de conveniencia para obtener estadísticas
    
    Returns:
        Estadísticas de almacenamiento
    """
    return file_manager.get_storage_stats()