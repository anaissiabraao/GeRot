import logging
import os
from datetime import datetime
from functools import wraps
from flask import request, session

def setup_logging(log_level='INFO', log_file='logs/gerot.log'):
    """Configura o sistema de logging"""
    # Criar diretório de logs se não existir
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configurar logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger('GeRot')
    logger.info('Sistema de logging inicializado')
    return logger

def log_activity(action, description=None, user_id=None):
    """Decorator para registrar atividades automaticamente"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from .database import connect_db
            from models.log import ActivityLog
            
            # Executar a função
            result = f(*args, **kwargs)
            
            try:
                # Registrar atividade
                conn = connect_db()
                current_user_id = user_id or session.get('user_id')
                ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
                user_agent = request.headers.get('User-Agent')
                
                ActivityLog.log_activity(
                    user_id=current_user_id,
                    action=action,
                    description=description or f'Ação executada: {action}',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    conn=conn
                )
                conn.close()
            except Exception as e:
                logger = logging.getLogger('GeRot')
                logger.error(f'Erro ao registrar atividade: {e}')
            
            return result
        return decorated_function
    return decorator

class GeRotLogger:
    def __init__(self):
        self.logger = logging.getLogger('GeRot')
    
    def info(self, message, user_id=None):
        """Log de informação"""
        self._log('INFO', message, user_id)
    
    def warning(self, message, user_id=None):
        """Log de aviso"""
        self._log('WARNING', message, user_id)
    
    def error(self, message, user_id=None):
        """Log de erro"""
        self._log('ERROR', message, user_id)
    
    def debug(self, message, user_id=None):
        """Log de debug"""
        self._log('DEBUG', message, user_id)
    
    def _log(self, level, message, user_id=None):
        """Método interno para logging"""
        user_info = f"[User: {user_id}] " if user_id else ""
        formatted_message = f"{user_info}{message}"
        
        getattr(self.logger, level.lower())(formatted_message)

# Instância global do logger
gerot_logger = GeRotLogger() 