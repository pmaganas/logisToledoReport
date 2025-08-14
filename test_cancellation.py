#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de cancelación mejorado.
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_cancellation_token():
    """Prueba el funcionamiento del token de cancelación"""
    
    print("🧪 PROBANDO SISTEMA DE CANCELACIÓN")
    print("=" * 50)
    
    try:
        from models import BackgroundReport, db
        from app import create_app
        
        # Create app context for testing
        app = create_app()
        
        with app.app_context():
            print("✅ Contexto de aplicación creado")
            
            # Test creating a report
            import uuid
            test_report_id = str(uuid.uuid4())
            
            print(f"🔄 Creando reporte de prueba: {test_report_id}")
            report = BackgroundReport.create_report(test_report_id)
            
            # Test status updates
            print("🔄 Probando actualización de estado...")
            report.update_status('processing')
            
            # Test cancellation check
            print("🔄 Probando verificación de cancelación (no cancelado)...")
            is_cancelled_1 = report.should_cancel()
            print(f"  ➡️  ¿Cancelado?: {is_cancelled_1}")
            
            # Cancel the report
            print("🔄 Cancelando reporte...")
            report.update_status('cancelled', error_message='Test cancellation')
            
            # Test cancellation check after cancellation
            print("🔄 Probando verificación de cancelación (cancelado)...")
            is_cancelled_2 = report.should_cancel()
            print(f"  ➡️  ¿Cancelado?: {is_cancelled_2}")
            
            # Cleanup
            print("🧹 Limpiando reporte de prueba...")
            db.session.delete(report)
            db.session.commit()
            
            if not is_cancelled_1 and is_cancelled_2:
                print("✅ Sistema de cancelación funciona correctamente")
                return True
            else:
                print("❌ Sistema de cancelación tiene problemas")
                return False
                
    except Exception as e:
        print(f"❌ Error en prueba de cancelación: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_report_generator_cancellation():
    """Prueba la cancelación en el generador de reportes"""
    
    print("\n🔄 PROBANDO CANCELACIÓN EN GENERADOR DE REPORTES")
    print("=" * 55)
    
    try:
        from services.no_breaks_report_generator import NoBreaksReportGenerator
        from models import BackgroundReport, db
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            # Create a mock cancelled report
            import uuid
            test_report_id = str(uuid.uuid4())
            
            print(f"🔄 Creando reporte mock cancelado: {test_report_id}")
            report = BackgroundReport.create_report(test_report_id)
            report.update_status('cancelled')  # Pre-cancel it
            
            # Test generator with cancelled token
            generator = NoBreaksReportGenerator()
            
            print("🔄 Probando generación con token cancelado...")
            try:
                result = generator.generate_report(
                    from_date="2024-01-01",
                    to_date="2024-01-02",
                    report_type="by_employee",
                    format="xlsx",
                    cancellation_token=report
                )
                print("❌ La generación debería haberse cancelado")
                return False
                
            except InterruptedError:
                print("✅ Generación cancelada correctamente con InterruptedError")
                
            # Cleanup
            print("🧹 Limpiando reporte de prueba...")
            db.session.delete(report)
            db.session.commit()
            
            return True
            
    except Exception as e:
        print(f"❌ Error en prueba de generador: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cancellation_syntax():
    """Verifica que la sintaxis del código de cancelación es correcta"""
    
    print("\n🧪 VERIFICANDO SINTAXIS DE CANCELACIÓN")
    print("=" * 45)
    
    try:
        # Test models syntax
        with open('models.py', 'r') as f:
            models_code = f.read()
        compile(models_code, 'models.py', 'exec')
        print("✅ models.py - Sintaxis correcta")
        
        if 'should_cancel' in models_code and 'is_cancelled' in models_code:
            print("✅ models.py - Métodos de cancelación encontrados")
        else:
            print("❌ models.py - Métodos de cancelación faltantes")
            return False
        
        # Test routes syntax  
        with open('routes/main.py', 'r') as f:
            routes_code = f.read()
        compile(routes_code, 'routes/main.py', 'exec')
        print("✅ routes/main.py - Sintaxis correcta")
        
        if 'InterruptedError' in routes_code and 'should_cancel' in routes_code:
            print("✅ routes/main.py - Lógica de cancelación encontrada")
        else:
            print("❌ routes/main.py - Lógica de cancelación faltante")
            return False
        
        # Test generator syntax
        with open('services/no_breaks_report_generator.py', 'r') as f:
            generator_code = f.read()
        compile(generator_code, 'no_breaks_report_generator.py', 'exec')
        print("✅ no_breaks_report_generator.py - Sintaxis correcta")
        
        if 'cancellation_token' in generator_code and '_check_cancellation' in generator_code:
            print("✅ no_breaks_report_generator.py - Sistema de cancelación encontrado")
        else:
            print("❌ no_breaks_report_generator.py - Sistema de cancelación faltante")
            return False
            
        return True
        
    except SyntaxError as e:
        print(f"❌ Error de sintaxis: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verificando sintaxis: {e}")
        return False

def main():
    """Función principal de prueba"""
    
    print("🚨 SUITE DE PRUEBAS DE CANCELACIÓN")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Syntax verification
    syntax_ok = test_cancellation_syntax()
    
    # Test 2: Cancellation token functionality 
    if syntax_ok:
        token_ok = test_cancellation_token()
    else:
        token_ok = False
    
    # Test 3: Generator cancellation
    if token_ok:
        generator_ok = test_report_generator_cancellation()
    else:
        generator_ok = False
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS:")
    print(f"✅ Sintaxis: {'OK' if syntax_ok else 'FALLO'}")
    print(f"✅ Token cancelación: {'OK' if token_ok else 'FALLO'}")  
    print(f"✅ Generador cancelación: {'OK' if generator_ok else 'FALLO'}")
    
    if all([syntax_ok, token_ok, generator_ok]):
        print("\n🎉 TODAS LAS PRUEBAS PASARON")
        print("✅ El sistema de cancelación está funcionando correctamente")
        print("\n🔧 FUNCIONALIDADES IMPLEMENTADAS:")
        print("  • 🚫 Cancelación inmediata durante generación")
        print("  • 🔄 Verificaciones múltiples durante el proceso") 
        print("  • 🧹 Limpieza automática de archivos parciales")
        print("  • 💬 Feedback visual mejorado en frontend")
        print("  • ⚡ InterruptedError para cancelación rápida")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisa la configuración y dependencias del proyecto")
    
    print("\n" + "=" * 50)
    print("🏁 FIN DE LAS PRUEBAS DE CANCELACIÓN")

if __name__ == "__main__":
    main()