"""
Supabase Connection Wrapper with Retry Logic and Error Handling
Handles Cloudflare 500 errors and rate limiting gracefully
"""

import time
import functools
from typing import Any, Callable
from services.logging_service import get_logger

logger = get_logger('supabase_wrapper')

def retry_on_error(max_retries=3, backoff_factor=2, retry_on_500=True):
    """
    Decorator to retry Supabase operations on failure
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (seconds)
        retry_on_500: Whether to retry on 500 errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    error_str = str(e)
                    
                    # Check if it's a retryable error
                    is_500_error = '500' in error_str
                    is_cloudflare_error = 'cloudflare' in error_str.lower()
                    is_rate_limit = '429' in error_str or 'rate limit' in error_str.lower()
                    
                    should_retry = (
                        (is_500_error and retry_on_500) or
                        is_cloudflare_error or
                        is_rate_limit
                    )
                    
                    if not should_retry or attempt == max_retries:
                        # Don't retry or max retries reached
                        logger.error(
                            f"Operation failed after {attempt + 1} attempts: {error_str}",
                            extra={'function': func.__name__}
                        )
                        raise last_exception
                    
                    # Calculate backoff time
                    wait_time = backoff_factor ** attempt
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed, "
                        f"retrying in {wait_time}s: {error_str[:100]}",
                        extra={'function': func.__name__}
                    )
                    
                    time.sleep(wait_time)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def safe_supabase_operation(operation_name: str, operation_func: Callable, 
                           default_return=None, log_errors=True):
    """
    Safely execute a Supabase operation with error handling
    
    Args:
        operation_name: Name of the operation for logging
        operation_func: Function to execute
        default_return: Value to return if operation fails
        log_errors: Whether to log errors
        
    Returns:
        Result of operation or default_return on failure
    """
    try:
        return operation_func()
    except Exception as e:
        if log_errors:
            error_str = str(e)
            if '500' in error_str and 'cloudflare' in error_str.lower():
                logger.error(
                    f"Supabase 500/Cloudflare error in {operation_name}. "
                    f"Check quota limits and service status.",
                    extra={'operation': operation_name}
                )
            else:
                logger.error(
                    f"Error in {operation_name}: {error_str}",
                    extra={'operation': operation_name}
                )
        return default_return


class SupabaseRateLimiter:
    """
    Rate limiter to prevent hitting Supabase API limits
    """
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.request_times = []
        
    def wait_if_needed(self):
        """Wait if we're about to exceed rate limit"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we need to wait
        if len(self.request_times) >= self.max_requests:
            oldest_request = min(self.request_times)
            wait_time = 60 - (now - oldest_request)
            
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached, waiting {wait_time:.2f}s",
                    extra={'requests_in_window': len(self.request_times)}
                )
                time.sleep(wait_time)
                
        # Record this request
        self.request_times.append(now)


# Global rate limiter instance
_rate_limiter = SupabaseRateLimiter(max_requests_per_minute=50)  # Conservative limit

def rate_limited(func: Callable) -> Callable:
    """Decorator to apply rate limiting to function"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _rate_limiter.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper


# Example usage in your code:
#
# from database.supabase_wrapper import retry_on_error, safe_supabase_operation, rate_limited
#
# @retry_on_error(max_retries=3)
# @rate_limited
# def save_interaction(user_id, project_id):
#     return supabase.table('user_interactions').insert({...}).execute()
#
# # Or use safe wrapper:
# result = safe_supabase_operation(
#     'save_interaction',
#     lambda: supabase.table('user_interactions').insert({...}).execute(),
#     default_return=None
# )
