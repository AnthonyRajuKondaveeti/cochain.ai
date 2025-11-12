# services/logging_service.py
"""
Centralized Logging Service for CoChain.ai
Provides structured logging with different levels and formatters
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
import json
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m'    # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset levelname for future use
        record.levelname = levelname
        
        return formatted


class LoggingService:
    """
    Centralized logging service with multiple handlers
    
    Features:
    - Console output with colors
    - Rotating file logs for general app logs
    - Separate error log file
    - JSON structured logs for analytics
    - Performance monitoring logs
    """
    
    def __init__(self, app_name='cochain', log_dir='logs'):
        self.app_name = app_name
        self.log_dir = Path(log_dir)
        self._setup_log_directory()
        
        # Main application logger
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate logs
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        self._setup_handlers()
    
    def _setup_log_directory(self):
        """Create log directory if it doesn't exist"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different log types
        (self.log_dir / 'app').mkdir(exist_ok=True)
        (self.log_dir / 'analytics').mkdir(exist_ok=True)
        (self.log_dir / 'performance').mkdir(exist_ok=True)
        (self.log_dir / 'errors').mkdir(exist_ok=True)
    
    def _setup_handlers(self):
        """Setup all log handlers"""
        
        # 1. Console Handler (colored, INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredConsoleFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 2. App Log File (rotating, DEBUG and above)
        app_log_file = self.log_dir / 'app' / 'cochain.log'
        app_file_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        app_file_handler.setLevel(logging.DEBUG)
        app_file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        app_file_handler.setFormatter(app_file_formatter)
        self.logger.addHandler(app_file_handler)
        
        # 3. Error Log File (ERROR and above only)
        error_log_file = self.log_dir / 'errors' / 'errors.log'
        error_file_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(app_file_formatter)
        self.logger.addHandler(error_file_handler)
        
        # 4. JSON Structured Logs (for analytics/parsing)
        json_log_file = self.log_dir / 'analytics' / 'structured.log'
        json_file_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=20*1024*1024,  # 20MB
            backupCount=10,
            encoding='utf-8'
        )
        json_file_handler.setLevel(logging.INFO)
        json_file_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(json_file_handler)
        
        # 5. Daily Performance Logs (time-based rotation)
        perf_log_file = self.log_dir / 'performance' / 'performance.log'
        perf_file_handler = TimedRotatingFileHandler(
            perf_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )
        perf_file_handler.setLevel(logging.INFO)
        perf_formatter = logging.Formatter(
            '%(asctime)s - PERF - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_file_handler.setFormatter(perf_formatter)
        
        # Create separate performance logger
        self.perf_logger = logging.getLogger(f'{self.app_name}.performance')
        self.perf_logger.setLevel(logging.INFO)
        self.perf_logger.addHandler(perf_file_handler)
        self.perf_logger.propagate = False
    
    def get_logger(self, name=None):
        """Get a logger instance"""
        if name:
            return logging.getLogger(f'{self.app_name}.{name}')
        return self.logger
    
    def log_performance(self, operation, duration_ms, **kwargs):
        """Log performance metrics"""
        perf_data = {
            'operation': operation,
            'duration_ms': duration_ms,
            **kwargs
        }
        self.perf_logger.info(json.dumps(perf_data))
    
    def log_user_action(self, action, user_id=None, session_id=None, **kwargs):
        """Log user action with context"""
        log_data = {
            'action': action,
            'user_id': user_id,
            'session_id': session_id,
            **kwargs
        }
        self.logger.info(f"USER_ACTION: {json.dumps(log_data)}", 
                        extra={'user_id': user_id, 'session_id': session_id})
    
    def log_recommendation(self, user_id, num_recommendations, cache_hit=False, **kwargs):
        """Log recommendation generation"""
        log_data = {
            'event': 'recommendation_generated',
            'user_id': user_id,
            'num_recommendations': num_recommendations,
            'cache_hit': cache_hit,
            **kwargs
        }
        self.logger.info(f"RECOMMENDATION: {json.dumps(log_data)}",
                        extra={'user_id': user_id})
    
    def log_error(self, error_type, error_message, user_id=None, **kwargs):
        """Log error with context"""
        log_data = {
            'error_type': error_type,
            'error_message': error_message,
            'user_id': user_id,
            **kwargs
        }
        self.logger.error(f"ERROR: {json.dumps(log_data)}",
                         extra={'user_id': user_id})
    
    def log_api_request(self, endpoint, method, status_code, duration_ms, 
                       user_id=None, ip_address=None, **kwargs):
        """Log API request"""
        log_data = {
            'event': 'api_request',
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': user_id,
            'ip_address': ip_address,
            **kwargs
        }
        self.logger.info(f"API_REQUEST: {json.dumps(log_data)}",
                        extra={
                            'user_id': user_id, 
                            'duration_ms': duration_ms,
                            'ip_address': ip_address
                        })


# Global logging service instance
_logging_service = None

def get_logging_service():
    """Get or create the global logging service instance"""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def get_logger(name=None):
    """Convenience function to get a logger"""
    service = get_logging_service()
    return service.get_logger(name)


# Example usage and testing
if __name__ == '__main__':
    # Initialize logging service
    log_service = get_logging_service()
    logger = log_service.get_logger('test')
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test user action logging
    log_service.log_user_action(
        action='login',
        user_id='user123',
        session_id='session456',
        ip_address='192.168.1.1'
    )
    
    # Test recommendation logging
    log_service.log_recommendation(
        user_id='user123',
        num_recommendations=10,
        cache_hit=True,
        similarity_threshold=0.7
    )
    
    # Test performance logging
    log_service.log_performance(
        operation='database_query',
        duration_ms=45.2,
        query_type='select',
        table='github_references'
    )
    
    # Test API request logging
    log_service.log_api_request(
        endpoint='/api/recommendations',
        method='POST',
        status_code=200,
        duration_ms=123.4,
        user_id='user123',
        ip_address='192.168.1.1'
    )
    
    print("\n✅ Logging service initialized successfully!")
    print(f"📁 Log files created in: {log_service.log_dir}")
    print("   - app/cochain.log (general application logs)")
    print("   - errors/errors.log (errors only)")
    print("   - analytics/structured.log (JSON structured logs)")
    print("   - performance/performance.log (performance metrics)")