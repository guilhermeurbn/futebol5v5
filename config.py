"""
Configurações da aplicação
"""
import os
from datetime import timedelta


class Config:
    """Configuração base"""
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    # Session / cookie security defaults (can be overridden per-environment)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = 'https'


class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Configuração de testes"""
    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    TESTING = False
    # Enforce secure cookies in production
    SESSION_COOKIE_SECURE = True


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

FLASK_ENV = os.getenv('FLASK_ENV', 'development')
