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


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

FLASK_ENV = os.getenv('FLASK_ENV', 'development')
