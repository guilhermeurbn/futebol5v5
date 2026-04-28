"""
Aplicação Flask - NaTrave - Gerador de Times Equilibrados
"""
import os
import logging
import socket
from flask import Flask, send_file
from config import config_by_name
from routes.jogador_routes import jogador_bp
from services.db import auto_seed_on_init
# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



def criar_app(config_name: str = None) -> Flask:
    """
    Factory para criar a aplicação Flask
    
    Args:
        config_name: Nome da configuração (development, testing, production)
        
    Returns:
        Aplicação Flask configurada
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)
    
    # Configurar secret key para sessions
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        if config_name == 'production':
            raise RuntimeError('SECRET_KEY obrigatoria em producao')
        secret_key = 'dev-secret-key-change-in-production'
    app.secret_key = secret_key
    
    # Registrar blueprints
    app.register_blueprint(jogador_bp)
    
    # Auto-seed database se estiver vazio (Railway)
    try:
        auto_seed_on_init()
    except Exception as e:
        logger.warning(f"Erro ao fazer seed do banco: {e}")
    
    # PWA - Servir manifest.json
    @app.route('/manifest.json')
    def serve_manifest():
        """Servir manifest.json para PWA"""
        return send_file(
            os.path.join(os.path.dirname(__file__), 'manifest.json'),
            mimetype='application/manifest+json'
        )
    
    logger.info(f"Aplicação iniciada em modo: {config_name}")
    
    return app


# Criar aplicação
app = criar_app()


def _porta_disponivel(preferida: int = 10000) -> int:
    """Escolhe porta livre para execucao local quando PORT nao estiver definida."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', preferida))
            return preferida
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('0.0.0.0', 0))
        return sock.getsockname()[1]

if __name__ == '__main__':
    port_env = os.environ.get("PORT")
    if port_env:
        port = int(port_env)
    else:
        port = _porta_disponivel(10000)
        logger.info(f"PORT nao definida. Usando porta livre: {port}")
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=port)
    