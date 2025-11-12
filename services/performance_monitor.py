# services/performance_monitor.py
"""
Performance Monitoring Service for CoChain.ai
Tracks API performance, database query times, and system metrics
"""
from functools import wraps
import time
from typing import Optional, Callable, Any
from .logging_service import get_logging_service
from datetime import datetime
import psutil
import threading

logger = get_logging_service().get_logger('performance')
perf_logger = get_logging_service().perf_logger


class PerformanceMonitor:
    """
    Monitor and track performance metrics across the platform
    
    Metrics tracked:
    - API endpoint response times
    - Database query execution times
    - Cache hit/miss rates
    - Memory usage
    - CPU usage
    - Concurrent user load
    """
    
    def __init__(self):
        self.logger = logger
        self.perf_logger = perf_logger
        
        # In-memory metrics (last 100 operations)
        self.recent_api_times = []
        self.recent_db_times = []
        self.recent_cache_stats = {'hits': 0, 'misses': 0}
        
        # Thresholds for alerts
        self.slow_api_threshold_ms = 1000  # 1 second
        self.slow_db_threshold_ms = 500    # 500ms
    
    def time_operation(self, operation_name: str, operation_type: str = 'general') -> Callable:
        """
        Decorator to time any operation
        
        Usage:
            @perf_monitor.time_operation('get_recommendations', 'api')
            def get_recommendations():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    
                    # Log performance
                    self.log_operation(
                        operation_name=operation_name,
                        operation_type=operation_type,
                        duration_ms=duration_ms,
                        success=success,
                        error=error
                    )
                
                return result
            
            return wrapper
        return decorator
    
    def log_operation(self, operation_name: str, operation_type: str,
                     duration_ms: float, success: bool = True,
                     error: Optional[str] = None, **kwargs):
        """Log operation performance"""
        try:
            perf_data = {
                'operation_name': operation_name,
                'operation_type': operation_type,
                'duration_ms': round(duration_ms, 2),
                'success': success,
                'timestamp': datetime.utcnow().isoformat(),
                **kwargs
            }
            
            if error:
                perf_data['error'] = error
            
            # Log to performance logger
            get_logging_service().log_performance(
                operation=operation_name,
                duration_ms=duration_ms,
                **kwargs
            )
            
            # Track in memory for recent stats
            if operation_type == 'api':
                self.recent_api_times.append(duration_ms)
                if len(self.recent_api_times) > 100:
                    self.recent_api_times.pop(0)
                
                # Alert if slow
                if duration_ms > self.slow_api_threshold_ms:
                    self.logger.warning(
                        f"⚠️ Slow API endpoint detected: {operation_name} took {duration_ms:.2f}ms"
                    )
            
            elif operation_type == 'database':
                self.recent_db_times.append(duration_ms)
                if len(self.recent_db_times) > 100:
                    self.recent_db_times.pop(0)
                
                # Alert if slow
                if duration_ms > self.slow_db_threshold_ms:
                    self.logger.warning(
                        f"⚠️ Slow database query detected: {operation_name} took {duration_ms:.2f}ms"
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to log performance metric: {str(e)}")
    
    def track_api_request(self, endpoint: str, method: str, status_code: int,
                         duration_ms: float, user_id: Optional[str] = None,
                         ip_address: Optional[str] = None, **kwargs):
        """Track API request performance"""
        get_logging_service().log_api_request(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            ip_address=ip_address,
            **kwargs
        )
        
        # Track in memory
        self.recent_api_times.append(duration_ms)
        if len(self.recent_api_times) > 100:
            self.recent_api_times.pop(0)
    
    def track_database_query(self, query_type: str, table: str, duration_ms: float,
                            rows_affected: Optional[int] = None, **kwargs):
        """Track database query performance"""
        self.log_operation(
            operation_name=f"db_{query_type}_{table}",
            operation_type='database',
            duration_ms=duration_ms,
            query_type=query_type,
            table=table,
            rows_affected=rows_affected,
            **kwargs
        )
    
    def track_cache_operation(self, cache_hit: bool, operation: str = 'read',
                             cache_key: Optional[str] = None):
        """Track cache hit/miss"""
        if cache_hit:
            self.recent_cache_stats['hits'] += 1
        else:
            self.recent_cache_stats['misses'] += 1
        
        self.logger.debug(
            f"Cache {'HIT' if cache_hit else 'MISS'}: {operation} - {cache_key}"
        )
    
    def track_recommendation_generation(self, user_id: str, num_recommendations: int,
                                      duration_ms: float, cache_hit: bool,
                                      similarity_calculations: int = 0,
                                      **kwargs):
        """Track recommendation generation performance"""
        self.log_operation(
            operation_name='generate_recommendations',
            operation_type='recommendation',
            duration_ms=duration_ms,
            user_id=user_id,
            num_recommendations=num_recommendations,
            cache_hit=cache_hit,
            similarity_calculations=similarity_calculations,
            **kwargs
        )
        
        # Track cache separately
        self.track_cache_operation(cache_hit, 'recommendation_read', user_id)
    
    def get_api_stats(self) -> dict:
        """Get recent API performance statistics"""
        if not self.recent_api_times:
            return {
                'count': 0,
                'avg_ms': 0,
                'min_ms': 0,
                'max_ms': 0,
                'p50_ms': 0,
                'p95_ms': 0,
                'p99_ms': 0
            }
        
        sorted_times = sorted(self.recent_api_times)
        count = len(sorted_times)
        
        return {
            'count': count,
            'avg_ms': round(sum(sorted_times) / count, 2),
            'min_ms': round(sorted_times[0], 2),
            'max_ms': round(sorted_times[-1], 2),
            'p50_ms': round(sorted_times[int(count * 0.5)], 2),
            'p95_ms': round(sorted_times[int(count * 0.95)], 2),
            'p99_ms': round(sorted_times[int(count * 0.99)], 2)
        }
    
    def get_database_stats(self) -> dict:
        """Get recent database performance statistics"""
        if not self.recent_db_times:
            return {
                'count': 0,
                'avg_ms': 0,
                'min_ms': 0,
                'max_ms': 0
            }
        
        return {
            'count': len(self.recent_db_times),
            'avg_ms': round(sum(self.recent_db_times) / len(self.recent_db_times), 2),
            'min_ms': round(min(self.recent_db_times), 2),
            'max_ms': round(max(self.recent_db_times), 2)
        }
    
    def get_cache_stats(self) -> dict:
        """Get cache hit rate statistics"""
        total = self.recent_cache_stats['hits'] + self.recent_cache_stats['misses']
        hit_rate = (self.recent_cache_stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'hits': self.recent_cache_stats['hits'],
            'misses': self.recent_cache_stats['misses'],
            'total': total,
            'hit_rate_percent': round(hit_rate, 2)
        }
    
    def get_system_metrics(self) -> dict:
        """Get system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory.percent, 2),
                'memory_used_mb': round(memory.used / 1024 / 1024, 2),
                'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                'disk_percent': round(disk.percent, 2),
                'disk_used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2)
            }
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {str(e)}")
            return {}
    
    def get_performance_summary(self) -> dict:
        """Get comprehensive performance summary"""
        return {
            'api_stats': self.get_api_stats(),
            'database_stats': self.get_database_stats(),
            'cache_stats': self.get_cache_stats(),
            'system_metrics': self.get_system_metrics(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def reset_stats(self):
        """Reset in-memory statistics"""
        self.recent_api_times = []
        self.recent_db_times = []
        self.recent_cache_stats = {'hits': 0, 'misses': 0}
        self.logger.info("Performance statistics reset")


class RequestTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, perf_monitor: PerformanceMonitor,
                 operation_type: str = 'general', **kwargs):
        self.operation_name = operation_name
        self.perf_monitor = perf_monitor
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        self.perf_monitor.log_operation(
            operation_name=self.operation_name,
            operation_type=self.operation_type,
            duration_ms=duration_ms,
            success=exc_type is None,
            error=str(exc_val) if exc_val else None,
            **self.kwargs
        )
        
        return False  # Don't suppress exceptions


# Global performance monitor instance
_perf_monitor = None

def get_performance_monitor():
    """Get or create the global performance monitor instance"""
    global _perf_monitor
    if _perf_monitor is None:
        _perf_monitor = PerformanceMonitor()
    return _perf_monitor


# Convenience decorator
def track_performance(operation_name: str, operation_type: str = 'general'):
    """Convenience decorator for tracking performance"""
    monitor = get_performance_monitor()
    return monitor.time_operation(operation_name, operation_type)


# Example usage
if __name__ == '__main__':
    perf_monitor = get_performance_monitor()
    
    print("Testing Performance Monitor...")
    
    # Test with decorator
    @track_performance('test_function', 'test')
    def slow_function():
        time.sleep(0.1)
        return "Done"
    
    result = slow_function()
    print(f"Result: {result}")
    
    # Test with context manager
    with RequestTimer('database_query', perf_monitor, 'database', table='users'):
        time.sleep(0.05)
    
    # Track cache operations
    perf_monitor.track_cache_operation(cache_hit=True, operation='read', cache_key='user123')
    perf_monitor.track_cache_operation(cache_hit=False, operation='read', cache_key='user456')
    perf_monitor.track_cache_operation(cache_hit=True, operation='read', cache_key='user789')
    
    # Track API request
    perf_monitor.track_api_request(
        endpoint='/api/recommendations',
        method='POST',
        status_code=200,
        duration_ms=123.45,
        user_id='user123'
    )
    
    # Get statistics
    print("\n📊 Performance Summary:")
    summary = perf_monitor.get_performance_summary()
    
    print(f"\nAPI Stats:")
    for key, value in summary['api_stats'].items():
        print(f"  {key}: {value}")
    
    print(f"\nCache Stats:")
    for key, value in summary['cache_stats'].items():
        print(f"  {key}: {value}")
    
    print(f"\nSystem Metrics:")
    for key, value in summary['system_metrics'].items():
        print(f"  {key}: {value}")
    
    print("\n✅ Performance monitoring tests completed!")