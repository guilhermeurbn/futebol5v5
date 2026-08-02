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
from markupsafe import Markup, escape
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
from services.votacao_service import VotacaoService
from services.db import auto_seed_on_init
# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
notificacao_service = NotificacaoService()
votacao_service = VotacaoService()


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


def _registrar_role_url_prefixes(app: Flask) -> None:
    """
    Registra URLs adicionais com os prefixos /admin, /juiz e /usuario
    para as páginas sem alterar os nomes de endpoints originais.
    """
    routes_to_prefix = [
        ('/ranking', 'stats.pagina_ranking'),
        ('/historico', 'partida.historico'),
        ('/perfil', 'auth.perfil_page'),
        ('/jogadores', 'jogador_crud.index'),
        ('/votacao', 'votacao.votacao_page'),
        ('/votacao/salvar', 'votacao.votacao_salvar'),
        ('/comparar', 'stats.pagina_comparar'),
    ]

    for role_prefix in ['admin', 'juiz', 'usuario']:
        for base_path, endpoint_name in routes_to_prefix:
            alias_path = f"/{role_prefix}{base_path}"
            existing_rules = [r.rule for r in app.url_map.iter_rules()]
            if alias_path not in existing_rules and endpoint_name in app.view_functions:
                app.add_url_rule(
                    alias_path,
                    endpoint=endpoint_name,
                    view_func=app.view_functions[endpoint_name],
                    methods=["GET", "POST"]
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
    
    # Limpar o cache do banco em memória para evitar poluição entre testes ou reinicializações
    try:
        from services.db import clear_db_cache
        clear_db_cache()
    except Exception:
        pass

    app = Flask(__name__)
    
    from flask.sessions import SecureCookieSessionInterface

    class CustomSessionInterface(SecureCookieSessionInterface):
        def get_expiration_time(self, app_obj, session_obj):
            if session_obj.permanent:
                from datetime import datetime as dt, timedelta as td, UTC
                if session_obj.get('remember_me'):
                    return dt.now(UTC) + td(days=30)
                return dt.now(UTC) + app_obj.permanent_session_lifetime
            return None

    app.session_interface = CustomSessionInterface()

    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)

    # Preserve the original scheme/host when deployed behind a reverse proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # Rate limiting setup
    # Keep strict protection on sensitive auth endpoints while avoiding
    # a restrictive global browsing limit for normal logged-in usage.
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[],
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
    app.view_functions['auth.login_submit'] = limiter.limit("10/hour")(app.view_functions['auth.login_submit'])
    app.view_functions['auth.cadastro_submit'] = limiter.limit("3/hour")(app.view_functions['auth.cadastro_submit'])
    app.view_functions['auth.recuperar_senha_submit'] = limiter.limit("3/hour")(app.view_functions['auth.recuperar_senha_submit'])
    
    app.register_blueprint(jogador_bp)
    app.register_blueprint(partida_bp)
    app.register_blueprint(votacao_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(juiz_bp)
    app.register_blueprint(stats_bp)
    _registrar_aliases_jogador(app)
    _registrar_role_url_prefixes(app)

    @app.before_request
    def auto_prefix_role_urls():
        # Em testes automatizados, desativado para garantir 100% de compatibilidade
        if app.testing:
            return

        path = request.path
        if (
            path.startswith('/static') or
            path.startswith('/api') or
            path.startswith('/site.') or
            path.startswith('/favicon') or
            path.startswith('/robots') or
            path.startswith('/perfil_') or
            path in ['/login', '/logout', '/cadastro', '/recuperar_senha', '/manifest.json']
        ):
            return

        role = session.get('role')
        if not role:
            return

        target_prefix = 'admin' if role in ['admin'] else ('juiz' if role == 'juiz' else 'usuario')

        if path.startswith(f"/{target_prefix}"):
            return

        if path in ['/ranking', '/historico', '/perfil', '/jogadores', '/votacao']:
            qs = ('?' + request.query_string.decode()) if request.query_string else ''
            return redirect(f"/{target_prefix}{path}{qs}")

    # Auto-seed database se estiver vazio (Railway)
    try:
        auto_seed_on_init()
        from services.db import executar_migracao_link_usuarios_jogadores
        executar_migracao_link_usuarios_jogadores()
    except Exception as e:
        logger.warning(f"Erro ao fazer seed ou migração do banco: {e}")
    
    # PWA - Servir manifest.json
    @app.route('/manifest.json')
    def serve_manifest():
        """Servir manifest.json para PWA"""
        return send_file(
            os.path.join(os.path.dirname(__file__), 'manifest.json'),
            mimetype='application/manifest+json'
        )

    # SEO - Servir Favicons, Manifest, Robots e Sitemap na raiz
    @app.route('/favicon.ico')
    @app.route('/favicon-16x16.png')
    @app.route('/favicon-32x32.png')
    @app.route('/apple-touch-icon.png')
    @app.route('/android-chrome-192x192.png')
    @app.route('/android-chrome-512x512.png')
    @app.route('/site.webmanifest')
    @app.route('/robots.txt')
    @app.route('/sitemap.xml')
    def serve_seo_files():
        filename = request.path.lstrip('/')
        mimetypes = {
            'ico': 'image/x-icon',
            'png': 'image/png',
            'webmanifest': 'application/manifest+json',
            'txt': 'text/plain',
            'xml': 'application/xml',
        }
        ext = filename.split('.')[-1]
        mimetype = mimetypes.get(ext, 'application/octet-stream')
        return send_file(
            os.path.join(os.path.dirname(__file__), filename),
            mimetype=mimetype
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

        # Caching para favicons e manifesto
        if request_path in {
            '/favicon.ico',
            '/favicon-16x16.png',
            '/favicon-32x32.png',
            '/apple-touch-icon.png',
            '/android-chrome-192x192.png',
            '/android-chrome-512x512.png',
            '/site.webmanifest'
        }:
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

        # Caching para robots.txt e sitemap.xml (24h)
        if request_path in {'/robots.txt', '/sitemap.xml'}:
            response.headers['Cache-Control'] = 'public, max-age=86400'

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

    # Filtros Jinja para datas: o HTML carrega o ISO e o navegador formata
    # no fuso local do usuário, sempre em relógio 24h.
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        SERVER_TIMEZONE = ZoneInfo(os.getenv('APP_TIMEZONE', 'Europe/Lisbon'))
    except Exception:
        SERVER_TIMEZONE = None

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

    def _normalizar_datetime_para_cliente(value):
        dt = _parse_iso_date(value)
        if not dt:
            return None
        if getattr(dt, 'tzinfo', None) is None and 'T' in str(value) and SERVER_TIMEZONE is not None:
            dt = dt.replace(tzinfo=SERVER_TIMEZONE)
        return dt

    def _time_local(value, incluir_hora: bool):
        dt = _normalizar_datetime_para_cliente(value)
        if not dt:
            return value

        iso_value = dt.isoformat()
        fallback = dt.strftime('%H:%M %d/%m') if incluir_hora else dt.strftime('%d/%m')
        data_attr = 'data-local-datetime' if incluir_hora else 'data-local-date'
        return Markup(
            f'<time datetime="{escape(iso_value)}" {data_attr}="{escape(iso_value)}">'
            f'{escape(fallback)}</time>'
        )

    def dt_pt(value):
        return _time_local(value, incluir_hora=False)

    def dt_pt_hm(value):
        return _time_local(value, incluir_hora=True)

    app.jinja_env.filters['dt_pt'] = dt_pt
    app.jinja_env.filters['dt_pt_hm'] = dt_pt_hm
    app.jinja_env.filters['parse_iso_date'] = _parse_iso_date
    app.jinja_env.filters['_parse_iso_date'] = _parse_iso_date

    from services.jogador_service import abreviar_nome

    def abreviar_nomes_lista(jogadores: list) -> str:
        nomes_abrev = []
        for j in jogadores:
            if isinstance(j, dict):
                nome = j.get('nome') or j.get('jogador_nome', '')
            elif isinstance(j, str):
                nome = j
            else:
                nome = getattr(j, 'nome', '')
            if nome:
                nomes_abrev.append(abreviar_nome(nome))
        return ", ".join(nomes_abrev)

    app.jinja_env.filters['abreviar_nome'] = abreviar_nome
    app.jinja_env.filters['abreviar_nomes_lista'] = abreviar_nomes_lista

    @app.context_processor
    def inject_notificacoes_globais():
        total_notificacoes = 0
        notificacoes_url = None
        votacao_pendente = None
        votacao_pendente_url = None
        presenca_pendente = False
        try:
            if session.get('user_id') and session.get('role') in {'admin'}:
                total_notificacoes = notificacao_service.contar_nao_lidas()
                notificacoes_url = url_for('admin.admin_notificacoes_page')
            elif session.get('user_id') and session.get('role') == 'usuario':
                votacao_pendente = votacao_service.obter_pendencia_usuario(session.get('user_id'))
                if votacao_pendente:
                    votacao_pendente_url = url_for('votacao.votacao_page')

            user_id = session.get('user_id')
            user_role = session.get('role')
            if user_id and user_role in {'usuario', 'jogador'}:
                from services.presenca_service import PresencaService
                ps = PresencaService()
                if ps.is_aberta():
                    resp = ps.obter_resposta(user_id)
                    if not resp or not resp.get('status') or resp.get('status') not in {'confirmado', 'ausente', 'duvida'}:
                        presenca_pendente = True
        except Exception:
            total_notificacoes = 0
            notificacoes_url = None
            votacao_pendente = None
            votacao_pendente_url = None
            presenca_pendente = False

        # Versão dinâmica do app
        version_str = "1.0.0"
        try:
            version_file = os.path.join(app.root_path, 'data', 'version.json')
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    vdata = json.load(f)
                    version_str = vdata.get('version', '1.0.0')
        except Exception:
            pass
        formatted_version = f"v{version_str}" if not version_str.startswith('v') else version_str

        return {
            'total_notificacoes': total_notificacoes,
            'notificacoes_url': notificacoes_url,
            'votacao_pendente': votacao_pendente,
            'votacao_pendente_url': votacao_pendente_url,
            'presenca_pendente': presenca_pendente,
            'app_version': formatted_version,
            'app_version_num': version_str,
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
    
