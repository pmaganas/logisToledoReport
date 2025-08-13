"""
Sistema de optimización de performance para procesamiento de reportes
"""
import asyncio
import aiohttp
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime
import time
import json
from dataclasses import dataclass
from queue import Queue
import threading

from config.settings import get_settings
from utils.logging_config import get_logger
from exceptions import APIError, ReportGenerationError


@dataclass
class PerformanceMetrics:
    """Métricas de performance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time: float = 0.0
    avg_response_time: float = 0.0
    requests_per_second: float = 0.0
    data_processed_mb: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def update_request(self, success: bool, response_time: float, data_size_bytes: int = 0):
        """Actualizar métricas de request"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_time += response_time
        self.avg_response_time = self.total_time / self.total_requests
        self.data_processed_mb += data_size_bytes / (1024 * 1024)
        
        if self.total_time > 0:
            self.requests_per_second = self.total_requests / self.total_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir métricas a diccionario"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            'total_time_seconds': round(self.total_time, 2),
            'avg_response_time_ms': round(self.avg_response_time * 1000, 2),
            'requests_per_second': round(self.requests_per_second, 2),
            'data_processed_mb': round(self.data_processed_mb, 2),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0
        }


class DataCache:
    """Cache inteligente para datos de API"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = threading.RLock()
        self.logger = get_logger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            # Verificar TTL
            if time.time() - self.access_times[key] > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            # Actualizar tiempo de acceso
            self.access_times[key] = time.time()
            return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Almacenar valor en cache"""
        with self.lock:
            # Limpiar cache si está lleno
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def _evict_oldest(self) -> None:
        """Eliminar el elemento más antiguo"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def clear(self) -> None:
        """Limpiar cache completamente"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'utilization': len(self.cache) / self.max_size * 100
            }


class AsyncAPIClient:
    """Cliente API asíncrono para requests concurrentes"""
    
    def __init__(self, base_url: str, token: str, max_concurrent: int = 10):
        self.base_url = base_url
        self.token = token
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = get_logger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Entrada del context manager"""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Salida del context manager"""
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, endpoint: str, params: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Obtener una página de datos de forma asíncrona
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros de la request
            
        Returns:
            Tupla (page_number, response_data)
        """
        async with self.semaphore:
            start_time = time.time()
            page_number = params.get('page', 1)
            
            try:
                url = f"{self.base_url}{endpoint}"
                
                async with self.session.get(url, params=params) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Página {page_number} obtenida en {response_time:.3f}s")
                        return page_number, data
                    else:
                        self.logger.error(f"Error en página {page_number}: HTTP {response.status}")
                        return page_number, {'data': [], 'totalPages': 0}
                        
            except Exception as e:
                response_time = time.time() - start_time
                self.logger.error(f"Error obteniendo página {page_number}: {str(e)} ({response_time:.3f}s)")
                return page_number, {'data': [], 'totalPages': 0}


class ParallelDataProcessor:
    """Procesador paralelo de datos con optimizaciones"""
    
    def __init__(self, max_workers: int = None):
        self.settings = get_settings()
        self.max_workers = max_workers or min(32, (self.settings.api.pool_maxsize or 4) * 2)
        self.logger = get_logger(__name__)
        self.cache = DataCache(max_size=2000, ttl_seconds=600)  # 10 minutos de cache
        self.metrics = PerformanceMetrics()
    
    async def fetch_all_pages_async(
        self,
        api_client: AsyncAPIClient,
        endpoint: str,
        base_params: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener todas las páginas de forma asíncrona y paralela
        
        Args:
            api_client: Cliente API asíncrono
            endpoint: Endpoint de la API
            base_params: Parámetros base
            progress_callback: Callback de progreso
            
        Returns:
            Lista de todos los datos obtenidos
        """
        start_time = time.time()
        all_data = []
        
        # Primera request para obtener total de páginas
        first_params = {**base_params, 'page': 1}
        page_num, first_response = await api_client.fetch_page(endpoint, first_params)
        
        if not first_response or 'data' not in first_response:
            raise APIError("No se pudo obtener la primera página de datos")
        
        all_data.extend(first_response['data'])
        total_pages = first_response.get('totalPages', 1)
        total_records = first_response.get('totalItems', len(first_response['data']))
        
        self.logger.info(f"Procesando {total_pages} páginas con ~{total_records} registros total")
        
        if progress_callback:
            progress_callback(1, total_pages, len(all_data), total_records)
        
        if total_pages <= 1:
            return all_data
        
        # Crear tasks para las páginas restantes
        tasks = []
        for page in range(2, total_pages + 1):
            params = {**base_params, 'page': page}
            task = api_client.fetch_page(endpoint, params)
            tasks.append(task)
        
        # Ejecutar requests en paralelo con límite de concurrencia
        completed_pages = 1
        batch_size = min(self.max_workers, len(tasks))
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Error en batch: {str(result)}")
                    continue
                
                page_num, page_data = result
                if page_data and 'data' in page_data:
                    all_data.extend(page_data['data'])
                
                completed_pages += 1
                
                if progress_callback:
                    progress_callback(completed_pages, total_pages, len(all_data), total_records)
        
        processing_time = time.time() - start_time
        self.logger.info(
            f"Procesamiento completado: {len(all_data)} registros en {processing_time:.2f}s "
            f"({len(all_data)/processing_time:.1f} registros/s)"
        )
        
        return all_data
    
    def process_data_parallel(
        self,
        data_list: List[Dict[str, Any]],
        processor_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        chunk_size: int = None
    ) -> List[Dict[str, Any]]:
        """
        Procesar datos en paralelo usando ThreadPoolExecutor
        
        Args:
            data_list: Lista de datos a procesar
            processor_func: Función de procesamiento
            chunk_size: Tamaño de chunks para procesamiento
            
        Returns:
            Lista de datos procesados
        """
        if not data_list:
            return []
        
        chunk_size = chunk_size or max(1, len(data_list) // (self.max_workers * 2))
        start_time = time.time()
        
        self.logger.info(f"Procesando {len(data_list)} elementos en chunks de {chunk_size}")
        
        # Dividir datos en chunks
        chunks = [data_list[i:i + chunk_size] for i in range(0, len(data_list), chunk_size)]
        processed_data = []
        
        def process_chunk(chunk):
            """Procesar un chunk de datos"""
            return [processor_func(item) for item in chunk]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Enviar chunks para procesamiento paralelo
            future_to_chunk = {
                executor.submit(process_chunk, chunk): chunk 
                for chunk in chunks
            }
            
            # Recolectar resultados
            for future in as_completed(future_to_chunk):
                try:
                    chunk_result = future.result()
                    processed_data.extend(chunk_result)
                except Exception as e:
                    self.logger.error(f"Error procesando chunk: {str(e)}")
        
        processing_time = time.time() - start_time
        self.logger.info(
            f"Procesamiento paralelo completado: {len(processed_data)} elementos "
            f"en {processing_time:.2f}s ({len(processed_data)/processing_time:.1f} elementos/s)"
        )
        
        return processed_data
    
    def get_cached_or_fetch(
        self,
        cache_key: str,
        fetch_func: Callable[[], Any]
    ) -> Any:
        """
        Obtener datos del cache o ejecutar función de fetch
        
        Args:
            cache_key: Clave de cache
            fetch_func: Función para obtener datos si no están en cache
            
        Returns:
            Datos obtenidos
        """
        # Intentar obtener del cache
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            self.metrics.cache_hits += 1
            self.logger.debug(f"Cache hit para: {cache_key}")
            return cached_data
        
        # Fetch de datos y cache
        self.metrics.cache_misses += 1
        start_time = time.time()
        
        try:
            data = fetch_func()
            fetch_time = time.time() - start_time
            
            # Cachear resultado
            self.cache.set(cache_key, data)
            
            self.logger.debug(f"Cache miss para: {cache_key} (fetch en {fetch_time:.3f}s)")
            return data
            
        except Exception as e:
            fetch_time = time.time() - start_time
            self.logger.error(f"Error en fetch para cache key {cache_key}: {str(e)} ({fetch_time:.3f}s)")
            raise
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de performance"""
        return {
            'processor_metrics': self.metrics.to_dict(),
            'cache_stats': self.cache.get_stats(),
            'max_workers': self.max_workers
        }
    
    def clear_cache(self) -> None:
        """Limpiar cache de datos"""
        self.cache.clear()
        self.logger.info("Cache de datos limpiado")


# Instancia global del procesador paralelo
parallel_processor = ParallelDataProcessor()