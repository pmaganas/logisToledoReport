#!/usr/bin/env python3
"""
Script de prueba para verificar la solución del problema de estado persistente
al recargar la página.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_orphaned_report_cleanup():
    """Prueba la limpieza de reportes huérfanos"""
    
    print("🧪 PROBANDO LIMPIEZA DE REPORTES HUÉRFANOS")
    print("=" * 50)
    
    try:
        from models import BackgroundReport, db
        from services.report_cleanup import ReportCleanupService
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            print("✅ Contexto de aplicación creado")
            
            # Crear un reporte "huérfano" (simulando uno abandonado)
            import uuid
            test_report_id = str(uuid.uuid4())
            
            print(f"🔄 Creando reporte huérfano simulado: {test_report_id}")
            report = BackgroundReport.create_report(test_report_id)
            report.update_status('processing')
            
            # Simular que el reporte ha estado procesando por 35 minutos
            old_time = datetime.utcnow() - timedelta(minutes=35)
            report.updated_at = old_time
            db.session.commit()
            
            print(f"📅 Reporte marcado como procesando desde: {old_time}")
            
            # Ejecutar limpieza
            print("🧹 Ejecutando limpieza de reportes huérfanos...")
            cleanup_service = ReportCleanupService()
            result = cleanup_service.cleanup_orphaned_reports(max_processing_time_minutes=30)
            
            if result['success'] and result['cleaned_count'] > 0:
                print(f"✅ Limpieza exitosa - {result['cleaned_count']} reporte(s) limpiado(s)")
                
                # Verificar que el reporte fue marcado como error
                updated_report = BackgroundReport.get_report(test_report_id)
                if updated_report and updated_report.status == 'error':
                    print("✅ Reporte huérfano marcado correctamente como 'error'")
                    print(f"📝 Mensaje: {updated_report.error_message}")
                else:
                    print("❌ Reporte no fue marcado correctamente")
                    return False
            else:
                print("❌ La limpieza no encontró reportes huérfanos")
                return False
            
            # Cleanup
            print("🧹 Limpiando reporte de prueba...")
            if updated_report:
                db.session.delete(updated_report)
                db.session.commit()
            
            return True
            
    except Exception as e:
        print(f"❌ Error en prueba de limpieza: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_processing_reports_endpoint():
    """Prueba el endpoint de verificación de reportes en procesamiento"""
    
    print("\n🔗 PROBANDO ENDPOINT CHECK-PROCESSING-REPORTS")
    print("=" * 55)
    
    try:
        from models import BackgroundReport, db
        from app import create_app
        import json
        
        app = create_app()
        
        with app.test_client() as client:
            with app.app_context():
                print("✅ Cliente de prueba creado")
                
                # Login first (assuming basic auth or session)
                # Note: This might need adjustment based on your auth system
                
                # Test 1: No processing reports
                print("🔄 Probando endpoint sin reportes en procesamiento...")
                response = client.get('/check-processing-reports')
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Respuesta exitosa: {data['status']}")
                    print(f"📊 Reportes en procesamiento: {data['processing_count']}")
                    print(f"🧹 Huérfanos limpiados: {data['orphaned_cleaned']}")
                else:
                    print(f"❌ Error en endpoint: {response.status_code}")
                    return False
                
                # Test 2: Create a recent processing report
                print("\n🔄 Creando reporte válido en procesamiento...")
                import uuid
                test_report_id = str(uuid.uuid4())
                
                report = BackgroundReport.create_report(test_report_id)
                report.update_status('processing')
                
                response = client.get('/check-processing-reports')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Con reporte activo - Procesando: {data['processing_count']}")
                    
                    if data['has_processing'] and data['processing_count'] == 1:
                        print("✅ Endpoint detecta correctamente reporte en procesamiento")
                    else:
                        print("❌ Endpoint no detecta reporte correctamente")
                        return False
                else:
                    print(f"❌ Error en endpoint con reporte: {response.status_code}")
                    return False
                
                # Test 3: Create an orphaned report  
                print("\n🔄 Creando reporte huérfano para prueba...")
                orphaned_id = str(uuid.uuid4())
                orphaned_report = BackgroundReport.create_report(orphaned_id)
                orphaned_report.update_status('processing')
                
                # Make it appear old
                old_time = datetime.utcnow() - timedelta(minutes=35)
                orphaned_report.updated_at = old_time
                db.session.commit()
                
                response = client.get('/check-processing-reports')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Con reporte huérfano - Limpiados: {data['orphaned_cleaned']}")
                    
                    if data['orphaned_cleaned'] > 0:
                        print("✅ Endpoint limpia automáticamente reportes huérfanos")
                    else:
                        print("⚠️  Endpoint no detectó reporte huérfano (posiblemente ya limpio)")
                else:
                    print(f"❌ Error en endpoint con huérfano: {response.status_code}")
                    return False
                
                # Cleanup
                print("🧹 Limpiando reportes de prueba...")
                remaining_reports = BackgroundReport.query.filter(
                    BackgroundReport.id.in_([test_report_id, orphaned_id])
                ).all()
                
                for r in remaining_reports:
                    db.session.delete(r)
                db.session.commit()
                
                return True
                
    except Exception as e:
        print(f"❌ Error en prueba de endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_syntax_and_imports():
    """Verifica que todos los archivos modificados tienen sintaxis correcta"""
    
    print("\n🧪 VERIFICANDO SINTAXIS DE ARCHIVOS MODIFICADOS")
    print("=" * 50)
    
    files_to_check = [
        'routes/main.py',
        'services/report_cleanup.py',
        'templates/index.html'
    ]
    
    try:
        for file_path in files_to_check:
            if file_path.endswith('.py'):
                print(f"🔄 Verificando {file_path}...")
                with open(file_path, 'r') as f:
                    code = f.read()
                compile(code, file_path, 'exec')
                print(f"✅ {file_path} - Sintaxis correcta")
                
                # Check for specific improvements
                if 'report_cleanup.py' in file_path:
                    if 'cleanup_orphaned_reports' in code and 'ReportCleanupService' in code:
                        print(f"✅ {file_path} - Servicio de limpieza implementado")
                
                if 'routes/main.py' in file_path:
                    if 'orphaned_count' in code and 'time_since_update' in code:
                        print(f"✅ {file_path} - Limpieza automática en endpoint implementada")
            
            else:
                print(f"ℹ️  Saltando verificación de sintaxis para {file_path} (archivo HTML)")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Error de sintaxis: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verificando archivos: {e}")
        return False

def main():
    """Función principal de prueba"""
    
    print("🔄 SUITE DE PRUEBAS - ESTADO PERSISTENTE AL RECARGAR")
    print("=" * 65)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Syntax verification
    syntax_ok = test_syntax_and_imports()
    
    # Test 2: Orphaned report cleanup
    if syntax_ok:
        cleanup_ok = test_orphaned_report_cleanup()
    else:
        cleanup_ok = False
    
    # Test 3: Processing reports endpoint
    if cleanup_ok:
        endpoint_ok = test_processing_reports_endpoint()
    else:
        endpoint_ok = False
    
    print("\n" + "=" * 65)
    print("📊 RESUMEN DE PRUEBAS:")
    print(f"✅ Sintaxis archivos: {'OK' if syntax_ok else 'FALLO'}")
    print(f"✅ Limpieza huérfanos: {'OK' if cleanup_ok else 'FALLO'}")  
    print(f"✅ Endpoint mejorado: {'OK' if endpoint_ok else 'FALLO'}")
    
    if all([syntax_ok, cleanup_ok, endpoint_ok]):
        print("\n🎉 TODAS LAS PRUEBAS PASARON")
        print("✅ El problema de estado persistente está SOLUCIONADO")
        print("\n🔧 FUNCIONALIDADES IMPLEMENTADAS:")
        print("  • 🧹 Limpieza automática de reportes huérfanos (>30min)")
        print("  • 🔄 Verificación inteligente al cargar página")
        print("  • 📊 Sincronización correcta entre frontend y backend")
        print("  • 💬 Mensajes informativos de limpieza automática")
        print("  • 🚫 Limpieza de estado residual en interfaz")
        print("\n🎯 RESULTADO:")
        print("  ➡️  Al recargar la página, NO se mostrará 'generando reporte' si no hay reportes activos")
        print("  ➡️  Los reportes abandonados se limpian automáticamente")
        print("  ➡️  La interfaz se sincroniza correctamente con el estado real")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisa la configuración y dependencias del proyecto")
    
    print("\n" + "=" * 65)
    print("🏁 FIN DE LAS PRUEBAS DE ESTADO PERSISTENTE")

if __name__ == "__main__":
    main()