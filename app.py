"""
Aplicação Flask - NaTrave - Gerador de Times Equilibrados
"""
import os
import logging
import socket
import uuid
from urllib.parse import quote, urlparse

from flask import Flask, send_file, request, session, url_for, redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
try:
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import CSRFError, generate_csrf
except Exception:
    CSRFProtect = None
    CSRFError = None
    generate_csrf = None

try:
    from flask_talisman import Talisman
except Exception:
    Talisman = None
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config_by_name
from routes import (
    admin_bp,
    auth_bp,
    jogador_bp,
    juiz_bp,
    partida_bp,
    stats_bp,
    votacao_bp,
)
from services.notificacao_service import NotificacaoService
from services.db import auto_seed_on_init
# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
notificacao_service = NotificacaoService()


def _registrar_aliases_jogador(app: Flask) -> None:
    """Mantem compatibilidade com templates que ainda usam url_for('jogador.*')."""
    for rule in list(app.url_map.iter_rules()):
        if rule.endpoint == "static" or "." not in rule.endpoint:
            continue

        endpoint_name = rule.endpoint.rsplit(".", 1)[1]
        alias_endpoint = f"jogador.{endpoint_name}"
        if alias_endpoint in app.view_functions:
            continue

        methods = rule.methods - {"HEAD", "OPTIONS"}
        app.add_url_rule(
            rule.rule,
            endpoint=alias_endpoint,
            view_func=app.view_functions[rule.endpoint],
            methods=methods,
            defaults=rule.defaults,
        )


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

    # Preserve the original scheme/host when deployed behind a reverse proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # Rate limiting setup
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    logger.info("Rate limiter initialized")
    
    # Configurar secret key para sessions
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        if config_name == 'production':
            raise RuntimeError('SECRET_KEY obrigatoria em producao')
        # Gerar UUID aleatório mesmo em dev (mais seguro que hardcoded)
        secret_key = str(uuid.uuid4())
        logger.warning(f"SECRET_KEY gerada dinamicamente (dev): {secret_key[:8]}...")
    app.secret_key = secret_key
    # Initialize security middleware
    if Talisman is not None:
        try:
            # Set up HTTP security headers (HSTS, X-Frame-Options, etc.)
            Talisman(
                app,
                content_security_policy=None,
                force_https=(config_name == 'production'),
            )
        except Exception as e:
            logger.warning(f"Falha ao iniciar Talisman: {e}")
    else:
        logger.warning("flask-talisman nao instalado; headers de seguranca extras desativados")

    # Enable CSRF protection for mutating requests
    if CSRFProtect is None or generate_csrf is None:
        logger.error("CRÍTICO: Flask-WTF não instalado; CSRF não protegido!")
        raise RuntimeError("Flask-WTF é obrigatório para CSRF protection")
    
    try:
        csrf = CSRFProtect()
        csrf.init_app(app)
        # Expor helper para templates que queiram ler o token diretamente
        app.jinja_env.globals['csrf_token'] = generate_csrf
        logger.info("CSRF protection ativado")
    except Exception as e:
        logger.error(f"Falha ao iniciar CSRFProtect: {e}")
        raise
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)
    
    # Apply rate limiting to auth endpoints (after blueprint registration)
    app.view_functions['auth.login_submit'] = limiter.limit("5/minute")(app.view_functions['auth.login_submit'])
    app.view_functions['auth.cadastro_submit'] = limiter.limit("3/hour")(app.view_functions['auth.cadastro_submit'])
    app.view_functions['auth.recuperar_senha_submit'] = limiter.limit("3/hour")(app.view_functions['auth.recuperar_senha_submit'])
    
    app.register_blueprint(jogador_bp)
    app.register_blueprint(partida_bp)
    app.register_blueprint(votacao_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(juiz_bp)
    app.register_blueprint(stats_bp)
    _registrar_aliases_jogador(app)

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

    @app.after_request
    def add_cache_headers(response):
        content_type = (response.headers.get('Content-Type') or '').lower()
        request_path = request.path if request else ''

        if 'text/html' in content_type or request_path in {'/', '/login', '/cadastro', '/recuperar-senha'}:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        if request_path in {'/manifest.json', '/static/service-worker.js'}:
            response.headers['Cache-Control'] = 'no-cache, max-age=0'

        if request_path in {'/static/style.css', '/static/offline-judge.js'}:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'

        return response

    if CSRFError is not None:
        @app.errorhandler(CSRFError)
        def handle_csrf_error(error):
            logger.warning('CSRF validation failed on %s: %s', request.path, error.description)

            fallback_path = url_for('votacao.votacao_admin_page')
            referrer = request.referrer or ''
            if referrer:
                referrer_url = urlparse(referrer)
                current_url = urlparse(request.host_url)
                if referrer_url.scheme in {'http', 'https'} and referrer_url.netloc == current_url.netloc:
                    fallback_path = referrer_url.path or fallback_path
                    if referrer_url.query:
                        fallback_path = f'{fallback_path}?{referrer_url.query}'

            separator = '&' if '?' in fallback_path else '?'
            mensagem = quote('Sua sessao expirou ou o formulario ficou desatualizado. Recarregue a pagina e tente novamente.')
            return redirect(f'{fallback_path}{separator}erro={mensagem}')
    
    logger.info(f"Aplicação iniciada em modo: {config_name}")

    # Filtros Jinja para formatação de datas no formato PT (DD/MM/YY)
    from datetime import datetime

    def _parse_iso_date(s: str):
        if not s:
            return None
        if isinstance(s, datetime):
            return s
        try:
            # normalize Z timezone
            s2 = s.replace('Z', '')
            # Try ISO format parsing (supports YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS(.micro))
            if 'T' in s2:
                try:
                    return datetime.fromisoformat(s2)
                except Exception:
                    # fallback to common slice
                    return datetime.strptime(s2[:19], '%Y-%m-%dT%H:%M:%S')
            if '-' in s2:
                # date only
                return datetime.strptime(s2[:10], '%Y-%m-%d')
        except Exception:
            return None

    def dt_pt(value):
        dt = _parse_iso_date(value)
        if not dt:
            return value
        return dt.strftime('%d/%m/%y')

    def dt_pt_hm(value):
        dt = _parse_iso_date(value)
        if not dt:
            return value
        return dt.strftime('%d/%m/%y às %H:%M')

    app.jinja_env.filters['dt_pt'] = dt_pt
    app.jinja_env.filters['dt_pt_hm'] = dt_pt_hm

    @app.context_processor
    def inject_notificacoes_globais():
        total_notificacoes = 0
        notificacoes_url = None
        try:
            if session.get('user_id') and session.get('role') in {'admin', 'super_admin'}:
                total_notificacoes = notificacao_service.contar_nao_lidas()
                notificacoes_url = url_for('admin.admin_notificacoes_page')
        except Exception:
            total_notificacoes = 0
            notificacoes_url = None

        return {
            'total_notificacoes': total_notificacoes,
            'notificacoes_url': notificacoes_url,
        }

    # Em desenvolvimento, garantir que mudanças em templates sejam recarregadas
    # automaticamente sem precisar reiniciar o servidor manualmente.
    try:
        if config_name == 'development' or app.config.get('DEBUG', False):
            app.config['TEMPLATES_AUTO_RELOAD'] = True
            app.jinja_env.auto_reload = True
            logger.info('Templates auto-reload habilitado (development/debug)')
    except Exception:
        # Segurança: não impedir startup se não for possível ajustar o Jinja env
        logger.debug('Não foi possível habilitar TEMPLATES_AUTO_RELOAD')
    
    return app


# Criar aplicação
app = criar_app()


def _porta_disponivel(preferida: int = 10000) -> int:
    """Escolhe porta livre para execucao local quando PORT nao estiver definida."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
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
    debug_enabled = (
        app.config['DEBUG']
        and os.getenv('FLASK_ENV', 'development') == 'development'
        and os.getenv('ENABLE_FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    )
    app.run(debug=debug_enabled, host='0.0.0.0', port=port)
    
