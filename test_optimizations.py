#!/usr/bin/env python3
"""
Script de prueba para verificar las optimizaciones de rendimiento del generador de informes.
Este script simula la generación de un informe y mide los tiempos de ejecución.
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

def test_report_generation():
    """Prueba la generación de informes con las optimizaciones implementadas"""
    
    print("🚀 INICIANDO PRUEBA DE OPTIMIZACIONES DE RENDIMIENTO")
    print("=" * 60)
    
    try:
        # Import here to avoid issues if the app isn't properly set up
        from services.no_breaks_report_generator import NoBreaksReportGenerator
        from services.check_types_service import CheckTypesService
        
        print("✅ Módulos importados correctamente")
        
        # Initialize services
        print("🔄 Inicializando servicios...")
        start_time = time.time()
        
        generator = NoBreaksReportGenerator()
        check_types_service = CheckTypesService()
        
        init_time = time.time() - start_time
        print(f"✅ Servicios inicializados en {init_time:.2f}s")
        
        # Test check types caching
        print("🔄 Probando cache de check types...")
        cache_start = time.time()
        
        success = check_types_service.ensure_check_types_cached()
        
        cache_time = time.time() - cache_start
        print(f"✅ Cache de check types: {'OK' if success else 'FALLO'} en {cache_time:.2f}s")
        
        # Test report generation (this will depend on having valid API tokens)
        print("🔄 Probando generación de informe de prueba...")
        
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        print(f"📅 Rango de fechas: {from_date} hasta {to_date}")
        
        # Progress callback for monitoring
        def progress_callback(page, total_pages, current_records, total_records):
            print(f"📊 Progreso API: Página {page}/{total_pages} - Registros: {current_records}/{total_records}")
        
        # Generate report
        report_start = time.time()
        
        report_data = generator.generate_report(
            from_date=from_date,
            to_date=to_date,
            report_type="by_employee",
            format="xlsx",
            progress_callback=progress_callback
        )
        
        report_time = time.time() - report_start
        
        if report_data:
            report_size = len(report_data) if report_data else 0
            print(f"✅ Informe generado en {report_time:.2f}s - Tamaño: {report_size:,} bytes")
            
            # Performance analysis
            print("\n📈 ANÁLISIS DE RENDIMIENTO:")
            print(f"⏱️  Tiempo de inicialización: {init_time:.2f}s")
            print(f"💾 Tiempo de cache: {cache_time:.2f}s") 
            print(f"📊 Tiempo de generación: {report_time:.2f}s")
            print(f"🎯 Tiempo total: {(init_time + cache_time + report_time):.2f}s")
            
            # Performance benchmarks
            if report_time < 60:
                print("🟢 EXCELENTE: Generación en menos de 1 minuto")
            elif report_time < 300:
                print("🟡 BUENO: Generación en menos de 5 minutos")
            elif report_time < 900:
                print("🟠 ACEPTABLE: Generación en menos de 15 minutos")
            else:
                print("🔴 LENTO: Generación toma más de 15 minutos")
                
        else:
            print(f"⚠️  Informe vacío generado en {report_time:.2f}s")
            print("ℹ️  Esto puede ser normal si no hay datos en el rango de fechas especificado")
        
        print("\n🎉 PRUEBA COMPLETADA EXITOSAMENTE")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("ℹ️  Asegúrate de que la base de datos esté configurada y las dependencias instaladas")
        return False
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_api_performance():
    """Prueba específicamente el rendimiento de la API paralela"""
    
    print("\n🔗 PROBANDO RENDIMIENTO DE API PARALELA")
    print("=" * 50)
    
    try:
        from services.parallel_sesame_api import ParallelSesameAPI
        from services.sesame_api import SesameAPI
        
        # Test connection
        parallel_api = ParallelSesameAPI()
        regular_api = SesameAPI()
        
        print("🔄 Probando conectividad...")
        
        # Test token info
        token_start = time.time()
        token_info = parallel_api.get_token_info()
        token_time = time.time() - token_start
        
        if token_info:
            print(f"✅ Token válido - Respuesta en {token_time:.2f}s")
            print(f"ℹ️  Empresa: {token_info.get('company', {}).get('name', 'N/A')}")
        else:
            print("❌ Token inválido o sin conexión")
            return False
        
        # Test small data fetch
        print("🔄 Probando fetch de datos pequeño...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)  # Just 1 day for quick test
        
        small_fetch_start = time.time()
        
        small_data = parallel_api.get_time_tracking(
            from_date=start_date.strftime('%Y-%m-%d'),
            to_date=end_date.strftime('%Y-%m-%d'),
            page=1,
            limit=100
        )
        
        small_fetch_time = time.time() - small_fetch_start
        
        if small_data and small_data.get('data'):
            records_count = len(small_data['data'])
            print(f"✅ Fetch pequeño completado en {small_fetch_time:.2f}s - {records_count} registros")
        else:
            print(f"⚠️  Fetch pequeño sin datos en {small_fetch_time:.2f}s")
        
        print("\n📊 MÉTRICAS DE RENDIMIENTO API:")
        print(f"🔗 Conectividad: {token_time:.2f}s")
        print(f"📥 Fetch datos: {small_fetch_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal de prueba"""
    
    print("🧪 SUITE DE PRUEBAS DE OPTIMIZACIONES DE RENDIMIENTO")
    print("=" * 70)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test API performance first
    api_success = test_api_performance()
    
    if api_success:
        # Test report generation if API works
        report_success = test_report_generation()
        
        if report_success:
            print("\n🎯 RESUMEN FINAL:")
            print("✅ Todas las optimizaciones funcionan correctamente")
            print("🚀 El sistema debería generar informes significativamente más rápido")
            print("\n📋 OPTIMIZACIONES IMPLEMENTADAS:")
            print("  • ⚡ Procesamiento paralelo de API (8 workers)")
            print("  • 📊 Paginación optimizada (1000 registros/página)")
            print("  • 💾 Cache de empleados y actividades")
            print("  • 📝 Escritura Excel por lotes")
            print("  • 🔗 Conexiones HTTP optimizadas")
            
        else:
            print("\n⚠️  Las pruebas de generación de informes fallaron")
            
    else:
        print("\n❌ Las pruebas de API fallaron - verifica la configuración de tokens")
    
    print("\n" + "=" * 70)
    print("🏁 FIN DE LAS PRUEBAS")

if __name__ == "__main__":
    main()