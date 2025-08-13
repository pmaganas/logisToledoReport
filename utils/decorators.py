"""
Decoradores para funcionalidad común
"""
import time
import logging
import functools
from typing import Callable, Any, Optional, Type, Union, List
from flask import jsonify, request, flash, redirect, url_for

from exceptions import (
    AppError, APIError, APIConnectionError, APITimeoutError, 
    ValidationError, TokenNotFoundError
)
from models import SesameToken


def retry(
    max_attempts: int = 3, 
    backoff_factor: float = 0.5,
    exceptions: tuple = (Exception,)
):
    """
    Decorador para reintentar operaciones que fallen
    
    Args:
        max_attempts: Número máximo de intentos
        backoff_factor: Factor de backoff exponencial
        exceptions: Tupla de excepciones a reintentar
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        # Último intento, propagar la excepción
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {wait_time:.2f}s: {str(e)}"
                    )
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """
    Decorador para loggear el tiempo de ejecución de funciones
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    
    return wrapper


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorador para manejar errores de API de manera consistente
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIConnectionError as e:
            return jsonify({
                'status': 'error',
                'message': 'Error de conexión con la API de Sesame',
                'error_code': e.error_code,
                'details': e.details
            }), 503
        except APITimeoutError as e:
            return jsonify({
                'status': 'error',
                'message': 'Timeout en la conexión con la API',
                'error_code': e.error_code,
                'details': e.details
            }), 408
        except APIError as e:
            return jsonify({
                'status': 'error',
                'message': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 400
        except ValidationError as e:
            return jsonify({
                'status': 'error',
                'message': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 422
        except AppError as e:
            return jsonify({
                'status': 'error',
                'message': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 400
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Error interno del servidor',
                'error_code': 'INTERNAL_SERVER_ERROR'
            }), 500
    
    return wrapper


def handle_form_errors(redirect_route: str = 'main.index'):
    """
    Decorador para manejar errores en formularios con flash messages
    
    Args:
        redirect_route: Ruta a la que redirigir en caso de error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                flash(e.message, 'error')
                return redirect(url_for(redirect_route))
            except AppError as e:
                flash(e.message, 'error')
                return redirect(url_for(redirect_route))
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
                flash('Error interno del servidor', 'error')
                return redirect(url_for(redirect_route))
        
        return wrapper
    return decorator


def requires_active_token(func: Callable) -> Callable:
    """
    Decorador para verificar que existe un token activo
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            active_token = SesameToken.get_active_token()
            if not active_token:
                if request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'No hay token de API configurado',
                        'error_code': 'TOKEN_NOT_FOUND_ERROR'
                    }), 400
                else:
                    flash('Debes configurar un token de API antes de continuar', 'warning')
                    return redirect(url_for('main.connection'))
            
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"Error checking active token in {func.__name__}: {str(e)}")
            
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Error al verificar token de API',
                    'error_code': 'TOKEN_CHECK_ERROR'
                }), 500
            else:
                flash('Error al verificar token de API', 'error')
                return redirect(url_for('main.connection'))
    
    return wrapper


def validate_request_data(*validators):
    """
    Decorador para validar datos de request usando validadores
    
    Args:
        *validators: Lista de funciones validadoras
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Aplicar validadores
                for validator in validators:
                    validator(request)
                
                return func(*args, **kwargs)
            except ValidationError as e:
                if request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': e.message,
                        'error_code': e.error_code,
                        'details': e.details
                    }), 422
                else:
                    flash(e.message, 'error')
                    return redirect(request.referrer or url_for('main.index'))
        
        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 300):
    """
    Decorador simple para cachear resultados en memoria
    
    Args:
        ttl_seconds: Tiempo de vida del cache en segundos
    """
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Crear clave de cache simple
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            # Verificar si existe en cache y no ha expirado
            if cache_key in cache:
                cached_time, cached_result = cache[cache_key]
                if current_time - cached_time < ttl_seconds:
                    return cached_result
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache[cache_key] = (current_time, result)
            
            # Limpiar cache expirado (simple cleanup)
            expired_keys = [
                key for key, (cached_time, _) in cache.items()
                if current_time - cached_time >= ttl_seconds
            ]
            for key in expired_keys:
                del cache[key]
            
            return result
        
        return wrapper
    return decorator


def rate_limit(calls: int = 10, period: int = 60):
    """
    Decorador simple para rate limiting
    
    Args:
        calls: Número de llamadas permitidas
        period: Período en segundos
    """
    call_times = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            
            # Usar IP del cliente como identificador
            client_id = request.remote_addr if hasattr(request, 'remote_addr') else 'unknown'
            
            if client_id not in call_times:
                call_times[client_id] = []
            
            # Filtrar llamadas dentro del período
            call_times[client_id] = [
                call_time for call_time in call_times[client_id]
                if current_time - call_time < period
            ]
            
            # Verificar límite
            if len(call_times[client_id]) >= calls:
                if request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': f'Límite de {calls} llamadas por {period} segundos excedido',
                        'error_code': 'RATE_LIMIT_EXCEEDED'
                    }), 429
                else:
                    flash(f'Demasiadas solicitudes. Intenta de nuevo en {period} segundos.', 'warning')
                    return redirect(request.referrer or url_for('main.index'))
            
            # Registrar llamada actual
            call_times[client_id].append(current_time)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator