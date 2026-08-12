"""
Configurações da aplicação
"""
import os
from datetime import timedelta


def _env_flag(name: str, default: str = '0') -> bool:
    return os.getenv(name, default).strip().lower() in {'1', 'true', 'yes', 'on'}


class Config:
    """Configuração base"""
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=90)
    ENABLE_APP_SHELL = _env_flag('ENABLE_APP_SHELL', '1')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '87998320853-mfkte5ili1uuvud8jdq6pvcp0kmknhrs.apps.googleusercontent.com')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
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
