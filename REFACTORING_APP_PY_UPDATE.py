"""
REFATORAÇÃO COMPLETA - ATUALIZAR app.py

Este arquivo mostra as mudanças necessárias em app.py para registrar todos os blueprints

ANTES (monolítico):
===================
from routes.jogador_routes import jogador_bp
app.register_blueprint(jogador_bp)


DEPOIS (modularizado):
======================
"""

# No início de app.py, substitua:
#
# from routes.jogador_routes import jogador_bp
#
# Por:
#
# from routes import auth_bp, jogador_bp, partida_bp, votacao_bp, admin_bp, stats_bp, juiz_bp


# ============================================================
# IMPORT CORRETO (NOVO)
# ============================================================

from routes import auth_bp, jogador_bp, partida_bp, votacao_bp, admin_bp, stats_bp, juiz_bp


# ============================================================
# REGISTRO DE BLUEPRINTS (NOVO)
# ============================================================

def criar_app(config_name: str = None) -> Flask:
    """
    Factory para criar a aplicação Flask
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)
    
    # ... outras configurações ...
    
    # ============================================================
    # REGISTRAR TODOS OS BLUEPRINTS
    # ============================================================
    
    # Autenticação
    app.register_blueprint(auth_bp, url_prefix='')  # /login, /cadastro, /logout, /perfil
    
    # Gerenciamento de Jogadores
    app.register_blueprint(jogador_bp, url_prefix='')  # /api/jogadores, /selecionar, etc
    
    # Partidas, Sorteios e Favoritos
    app.register_blueprint(partida_bp, url_prefix='')  # /sortear, /historico, /favoritos, etc
    
    # Votação
    app.register_blueprint(votacao_bp, url_prefix='')  # /votacao, /admin/votacao, etc
    
    # Administração
    app.register_blueprint(admin_bp, url_prefix='')  # /admin, /admin/usuarios, etc
    
    # Estatísticas e Rankings
    app.register_blueprint(stats_bp, url_prefix='')  # /stats/*, /export/*, /ranking, etc
    
    # Fluxo do Juiz
    app.register_blueprint(juiz_bp, url_prefix='')  # /jogar, /jogar/criar-partida, etc
    
    # ... resto da função ...
    
    logger.info(f"Aplicação iniciada em modo: {config_name} com 7 blueprints modulares")
    
    return app


# ============================================================
# MAPEAMENTO DE ROTAS POR BLUEPRINT
# ============================================================

"""
auth_bp (Autenticação):
  ✓ /login GET/POST
  ✓ /cadastro GET/POST
  ✓ /logout POST
  ✓ /perfil GET
  ✓ /perfil/senha POST
  ✓ /jogadores/<id>/perfil GET

jogador_bp (Gerenciamento de Jogadores):
  ✓ / (index)
  ✓ /api/jogadores GET/POST
  ✓ /add POST
  ✓ /api/jogadores/<id> GET/PUT/DELETE
  ✓ /jogadores/<id>/editar GET/POST
  ✓ /delete/<id>
  ✓ /selecionar
  ✓ /api/presenca POST
  ✓ /api/presenca/limpar POST

partida_bp (Sorteios e Favoritos):
  ✓ /sortear
  ✓ /api/times
  ✓ /historico
  ✓ /sorteio/<id>
  ✓ /api/historico
  ✓ /resultado_partida/<id>
  ✓ /api/partida/registrar POST
  ✓ /campeonato
  ✓ /api/campeonato
  ✓ /api/favoritar-time POST
  ✓ /favoritos
  ✓ /api/favoritos
  ✓ /api/favorito/<id>/remover DELETE
  ✓ /api/favorito/<id>/renomear POST
  ✓ /api/favorito/<id>/usar POST
  ✓ /api/sorteio/undo POST
  ✓ /api/sorteio/redo POST
  ✓ /api/sorteio/status GET
  ✓ /api/sorteio/adicionar-stack POST
  ✓ /api/qrcode/sorteio/<id> GET
  ✓ /compartilhado GET
  ✓ /api/qrcode/link-compartilhamento/<id> GET

votacao_bp (Votação):
  ✓ /votacao GET
  ✓ /votacao/salvar POST
  ✓ /admin/votacao GET
  ✓ /admin/votacao/criar POST
  ✓ /admin/votacao/<id>/encerrar POST

admin_bp (Administração):
  ✓ /admin GET
  ✓ /admin/notificacoes/limpar POST
  ✓ /admin/usuarios POST
  ✓ /admin/usuarios/<id>/resetar-senha POST
  ✓ /admin/usuarios/<id>/ativo POST
  ✓ /admin/usuarios/<id>/deletar POST

stats_bp (Estatísticas e Rankings):
  ✓ /api/estatisticas
  ✓ /estatisticas, /stats (redir)
  ✓ /api/stats/players GET
  ✓ /api/stats/times GET
  ✓ /api/stats/geral GET
  ✓ /api/stats/combos GET
  ✓ /api/stats/comparacao/<p1>/<p2> GET
  ✓ /stats/players, /stats/times, /stats/combos, /charts (redir)
  ✓ /export/sorteio/csv GET
  ✓ /export/sorteio/txt GET
  ✓ /api/export/sorteio/txt GET
  ✓ /export/sorteio/pdf GET
  ✓ /export/historico/csv GET
  ✓ /export/estatisticas/csv GET
  ✓ /api/export/sorteio POST
  ✓ /api/sugestoes/nivel POST
  ✓ /api/sugestoes/diversidade POST
  ✓ /api/sugestoes/vencedores POST
  ✓ /api/sugestoes/duplas POST
  ✓ /api/sugestoes/combinadas POST
  ✓ /ranking
  ✓ /api/ranking/geral
  ✓ /api/ranking/periodo/<dias> (desativado)
  ✓ /api/ranking/stats (desativado)

juiz_bp (Fluxo do Juiz):
  ✓ /jogar GET
  ✓ /jogar/criar-partida POST
  ✓ /jogar/finalizar POST

"""


# ============================================================
# TESTES DE VALIDAÇÃO
# ============================================================

"""
Para validar que todos os blueprints foram registrados corretamente:

1. Verificar número total de rotas:
   $ python -c "from app import app; print(f'Total de rotas: {len([r for r in app.url_map.iter_rules()])}')"
   Esperado: ~85 rotas

2. Listar todas as rotas por blueprint:
   $ python -c "
   from app import app
   from collections import defaultdict
   routes_by_bp = defaultdict(list)
   for rule in app.url_map.iter_rules():
       routes_by_bp[rule.endpoint.split('.')[0]].append(str(rule))
   for bp, routes in sorted(routes_by_bp.items()):
       print(f'{bp}: {len(routes)} rotas')
   "

3. Testar endpoints críticos:
   - GET /login -> 200
   - GET /admin -> 403 (sem autenticação)
   - POST /api/jogadores -> 401 (sem autenticação)
   - GET /api/times -> erro ou sucesso com dados

"""
