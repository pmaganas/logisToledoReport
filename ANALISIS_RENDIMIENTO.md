# Análisis de Rendimiento - Generación de Reportes

## 🔍 Problemas Identificados

### 1. **Múltiples Llamadas API Secuenciales (PRINCIPAL CUELLO DE BOTELLA)**

#### Problema:
- Para cada reporte, el sistema hace **múltiples llamadas secuenciales** a la API de Sesame:
  1. Una llamada para obtener todos los check-type-collections (grupos)
  2. **Una llamada individual para CADA grupo** para obtener sus detalles
  3. Si hay 20 grupos, son 21 llamadas API solo para mapear los grupos

#### Código problemático:
```python
# En sesame_api.py línea 256-274
for collection in collections:
    collection_id = collection.get("id")
    # LLAMADA API INDIVIDUAL para cada colección
    details_response = self.get_check_type_collection_details(collection_id)
```

#### Impacto:
- Con 20 grupos: **21 llamadas API × 2 segundos promedio = 42 segundos**
- Esto ocurre ANTES de empezar a obtener los datos del reporte

### 2. **Timeout Insuficiente para APIs Lentas**

#### Problema:
- Timeout configurado: `(5, 15)` segundos (conexión, lectura)
- La API de Sesame puede ser lenta, especialmente con muchos datos
- Timeouts frecuentes causan reintentos, duplicando el tiempo

#### Código:
```python
# En sesame_api.py línea 68
timeout=(5, 15)  # Muy corto para APIs lentas
```

### 3. **Procesamiento Ineficiente de Datos**

#### Problemas:
- **Ordenamiento múltiple**: Los datos se ordenan 3-4 veces durante el procesamiento
- **Búsquedas lineales**: Para cada pausa, busca linealmente las entradas anteriores/siguientes
- **Manipulación de fechas repetitiva**: Parsea la misma fecha múltiples veces

#### Código problemático:
```python
# En no_breaks_report_generator.py
# Línea 466: Primera ordenación
all_entries.sort(key=self._get_entry_sort_key)
# Línea 472: Segunda ordenación después de procesar pausas
processed_entries.sort(key=self._get_entry_sort_key)
```

### 4. **Límite de Paginación Conservador**

#### Problema:
- Límite actual: 300 registros por página
- La API podría soportar hasta 500-1000 registros por página
- Más páginas = más llamadas API = más tiempo

### 5. **Sin Caché de Datos Frecuentes**

#### Problemas:
- Los grupos (check-type-collections) se obtienen CADA VEZ
- Los check-types se sincronizan completos cada vez
- No hay caché temporal durante la sesión

## 📊 Análisis de Tiempos

Para un reporte típico con 1000 registros y 20 grupos:

| Operación | Tiempo Actual | Tiempo Optimizado |
|-----------|---------------|-------------------|
| Obtener grupos | 42s | 2s (con caché) |
| Obtener datos (4 páginas) | 8s | 4s (páginas más grandes) |
| Procesamiento | 5s | 2s (optimizado) |
| **TOTAL** | **55s** | **8s** |

## 🚀 Soluciones Propuestas

### Solución 1: Implementar Caché de Grupos (PRIORIDAD ALTA)

```python
class CheckTypesService:
    _collections_cache = None
    _cache_timestamp = None
    CACHE_DURATION = 3600  # 1 hora
    
    def get_collections_mapping(self):
        now = time.time()
        if (self._collections_cache and 
            self._cache_timestamp and 
            now - self._cache_timestamp < self.CACHE_DURATION):
            return self._collections_cache
        
        # Si no hay caché o expiró, obtener de API
        self._collections_cache = self._fetch_collections_from_api()
        self._cache_timestamp = now
        return self._collections_cache
```

### Solución 2: Aumentar Timeouts

```python
timeout=(30, 120)  # 30s conexión, 120s lectura
```

### Solución 3: Aumentar Límite de Paginación

```python
limit = 500  # En lugar de 300
```

### Solución 4: Procesar Grupos en Paralelo

```python
from concurrent.futures import ThreadPoolExecutor

def get_all_collections_parallel(self):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for collection in collections:
            future = executor.submit(
                self.get_check_type_collection_details, 
                collection['id']
            )
            futures.append(future)
        
        results = [f.result() for f in futures]
```

### Solución 5: Optimizar Procesamiento de Datos

```python
# Pre-calcular índices para búsquedas O(1)
entry_index = {entry['id']: idx for idx, entry in enumerate(entries)}

# Cachear fechas parseadas
parsed_dates_cache = {}

def parse_date_cached(date_str):
    if date_str not in parsed_dates_cache:
        parsed_dates_cache[date_str] = datetime.fromisoformat(date_str)
    return parsed_dates_cache[date_str]
```

## 🎯 Implementación Recomendada

### Fase 1 (Impacto Inmediato - 70% mejora):
1. ✅ Implementar caché de grupos en memoria/sesión
2. ✅ Aumentar timeouts a (30, 120)
3. ✅ Aumentar límite de paginación a 500

### Fase 2 (Mejoras Adicionales - 20% mejora):
1. ⏳ Procesamiento paralelo de grupos
2. ⏳ Optimizar búsquedas con índices
3. ⏳ Caché de fechas parseadas

### Fase 3 (Optimizaciones Avanzadas - 10% mejora):
1. ⏳ Implementar caché Redis para datos compartidos
2. ⏳ Pre-cargar grupos al iniciar sesión
3. ⏳ Procesamiento asíncrono con Celery

## 📈 Resultados Esperados

Con las optimizaciones de Fase 1:
- **Tiempo actual**: 50-60 segundos
- **Tiempo optimizado**: 10-15 segundos
- **Mejora**: 70-75% reducción en tiempo

## 🔧 Monitoreo Recomendado

Agregar logging detallado para medir:
```python
import time

start = time.time()
# operación
elapsed = time.time() - start
logger.info(f"Operación X tomó {elapsed:.2f} segundos")
```

## 📝 Notas Adicionales

1. La API de Sesame parece tener rate limiting no documentado
2. Los timeouts de red pueden variar según la ubicación del servidor
3. El procesamiento de pausas es complejo pero no es el principal cuello de botella
4. La generación del Excel/CSV es rápida (< 1s), no requiere optimización