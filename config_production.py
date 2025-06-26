#!/usr/bin/env python3
"""
Configurações de Produção - GeRot Enterprise
"""

import os
from dotenv import load_dotenv

load_dotenv()

class ProductionConfig:
    """Configurações de produção"""
    
    # Flask
    FLASK_ENV = 'production'
    DEBUG = False
    TESTING = False
    
    # Segurança
    SECRET_KEY = os.getenv('SECRET_KEY', 'gerot-production-2025-super-secret')
    WTF_CSRF_ENABLED = True
    
    # Banco de Dados
    DATABASE_URL = os.getenv('DATABASE_URL', 'gerot_production.db')
    
    # OAuth Google
    GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
    
    # Push Notifications
    VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
    
    # Empresa
    COMPANY_NAME = 'Portoex Solutions'
    COMPANY_DOMAIN = 'portoex.com.br'
    ADMIN_EMAIL = 'admin@portoex.com.br'
    
    # Servidor
    PORT = int(os.getenv('PORT', 10000))
    HOST = '0.0.0.0'

class DevelopmentConfig:
    """Configurações de desenvolvimento"""
    
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = False
    SECRET_KEY = 'dev-secret-key'
    DATABASE_URL = 'gerot_dev.db'

# Configuração ativa
config = ProductionConfig if os.getenv('FLASK_ENV') == 'production' else DevelopmentConfig 