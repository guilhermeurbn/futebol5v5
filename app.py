"""
Aplicação Flask - NaTrave - Gerador de Times Equilibrados
"""
import os
import logging
from flask import Flask, send_file
from config import config_by_name
from routes.jogador_routes import jogador_bp
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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=port)
    