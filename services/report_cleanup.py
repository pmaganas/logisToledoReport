#!/usr/bin/env python3
"""
Servicio de limpieza automática para reportes huérfanos o abandonados.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from models import BackgroundReport, db

logger = logging.getLogger(__name__)

class ReportCleanupService:
    """Servicio para limpiar reportes abandonados y mantener la base de datos limpia"""
    
    def __init__(self):
        self.logger = logger
    
    def cleanup_orphaned_reports(self, max_processing_time_minutes: int = 30) -> Dict:
        """
        Limpia reportes que han estado 'processing' por demasiado tiempo
        
        Args:
            max_processing_time_minutes: Tiempo máximo que un reporte puede estar procesando
            
        Returns:
            Dict con estadísticas de limpieza
        """
        try:
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(minutes=max_processing_time_minutes)
            
            # Buscar reportes huérfanos
            orphaned_reports = BackgroundReport.query.filter(
                BackgroundReport.status == 'processing',
                BackgroundReport.updated_at < cutoff_time
            ).all()
            
            cleaned_count = 0
            cleaned_reports = []
            
            for report in orphaned_reports:
                time_processing = current_time - report.updated_at
                self.logger.warning(f"Cleaning orphaned report {report.id} - processing for {time_processing}")
                
                # Marcar como error con mensaje explicativo
                error_message = f"Report abandoned after {time_processing}. Thread likely died or crashed."
                report.update_status('error', error_message=error_message)
                
                cleaned_reports.append({
                    'id': report.id,
                    'processing_time': str(time_processing),
                    'created_at': report.created_at,
                    'updated_at': report.updated_at
                })
                cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Successfully cleaned up {cleaned_count} orphaned report(s)")
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'cleaned_reports': cleaned_reports,
                'cutoff_time': cutoff_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error during orphaned reports cleanup: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0
            }
    
    def cleanup_old_reports(self, max_age_days: int = 7) -> Dict:
        """
        Limpia reportes completados muy antiguos para mantener la BD limpia
        
        Args:
            max_age_days: Días después de los cuales eliminar reportes completados
            
        Returns:
            Dict con estadísticas de limpieza
        """
        try:
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(days=max_age_days)
            
            # Buscar reportes completados antiguos
            old_reports = BackgroundReport.query.filter(
                BackgroundReport.status.in_(['completed', 'error', 'cancelled']),
                BackgroundReport.updated_at < cutoff_time
            ).all()
            
            deleted_count = 0
            deleted_reports = []
            
            for report in old_reports:
                age = current_time - report.updated_at
                self.logger.info(f"Deleting old report {report.id} - age: {age}")
                
                deleted_reports.append({
                    'id': report.id,
                    'status': report.status,
                    'age': str(age),
                    'created_at': report.created_at,
                    'updated_at': report.updated_at
                })
                
                # Eliminar de la BD
                db.session.delete(report)
                deleted_count += 1
            
            if deleted_count > 0:
                db.session.commit()
                self.logger.info(f"Successfully deleted {deleted_count} old report(s)")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'deleted_reports': deleted_reports,
                'cutoff_time': cutoff_time.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error during old reports cleanup: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0
            }
    
    def get_reports_statistics(self) -> Dict:
        """
        Obtiene estadísticas de los reportes en la BD
        
        Returns:
            Dict con estadísticas de reportes
        """
        try:
            current_time = datetime.utcnow()
            
            # Contar reportes por estado
            stats = {
                'pending': BackgroundReport.query.filter_by(status='pending').count(),
                'processing': BackgroundReport.query.filter_by(status='processing').count(),
                'completed': BackgroundReport.query.filter_by(status='completed').count(),
                'error': BackgroundReport.query.filter_by(status='error').count(),
                'cancelled': BackgroundReport.query.filter_by(status='cancelled').count(),
                'total': BackgroundReport.query.count()
            }
            
            # Reportes más antiguos
            oldest_report = BackgroundReport.query.order_by(BackgroundReport.created_at.asc()).first()
            newest_report = BackgroundReport.query.order_by(BackgroundReport.created_at.desc()).first()
            
            # Reportes procesando por más tiempo
            long_processing = BackgroundReport.query.filter(
                BackgroundReport.status == 'processing',
                BackgroundReport.updated_at < current_time - timedelta(minutes=10)
            ).all()
            
            stats.update({
                'oldest_report': {
                    'id': oldest_report.id,
                    'created_at': oldest_report.created_at.isoformat(),
                    'age': str(current_time - oldest_report.created_at)
                } if oldest_report else None,
                'newest_report': {
                    'id': newest_report.id,
                    'created_at': newest_report.created_at.isoformat(),
                    'age': str(current_time - newest_report.created_at)
                } if newest_report else None,
                'long_processing_count': len(long_processing),
                'long_processing_reports': [
                    {
                        'id': r.id,
                        'processing_time': str(current_time - r.updated_at),
                        'created_at': r.created_at.isoformat()
                    } for r in long_processing
                ]
            })
            
            return {
                'success': True,
                'timestamp': current_time.isoformat(),
                'statistics': stats
            }
            
        except Exception as e:
            self.logger.error(f"Error getting reports statistics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def full_cleanup(self) -> Dict:
        """
        Ejecuta una limpieza completa: reportes huérfanos y reportes antiguos
        
        Returns:
            Dict con resultados de ambas limpiezas
        """
        self.logger.info("Starting full cleanup process...")
        
        # Limpiar reportes huérfanos
        orphaned_result = self.cleanup_orphaned_reports()
        
        # Limpiar reportes antiguos
        old_reports_result = self.cleanup_old_reports()
        
        # Obtener estadísticas finales
        stats = self.get_reports_statistics()
        
        result = {
            'success': orphaned_result['success'] and old_reports_result['success'],
            'orphaned_cleanup': orphaned_result,
            'old_reports_cleanup': old_reports_result,
            'final_statistics': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        total_cleaned = orphaned_result['cleaned_count'] + old_reports_result['deleted_count']
        if total_cleaned > 0:
            self.logger.info(f"Full cleanup completed - {total_cleaned} reports processed")
        
        return result


# Función de conveniencia para uso directo
def cleanup_reports(orphaned_minutes=30, old_days=7):
    """Función de conveniencia para limpiar reportes"""
    service = ReportCleanupService()
    return service.full_cleanup()


if __name__ == "__main__":
    # Script ejecutable para limpiezas manuales
    import sys
    import os
    
    # Add the project root to Python path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        from app import create_app
        
        app = create_app()
        with app.app_context():
            print("🧹 Ejecutando limpieza de reportes...")
            
            service = ReportCleanupService()
            result = service.full_cleanup()
            
            if result['success']:
                print(f"✅ Limpieza exitosa:")
                print(f"   • Huérfanos limpiados: {result['orphaned_cleanup']['cleaned_count']}")
                print(f"   • Antiguos eliminados: {result['old_reports_cleanup']['deleted_count']}")
                print(f"   • Total reportes actuales: {result['final_statistics']['statistics']['total']}")
            else:
                print("❌ Error durante la limpieza")
                print(f"   • Error: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error ejecutando limpieza: {e}")
        import traceback
        traceback.print_exc()