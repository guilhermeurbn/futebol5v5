"""
Módulos de Rotas - Exportação de Blueprints

7 módulos especializados:
- auth_routes.py: Autenticação e perfil
- jogador_crud_routes.py: Gerenciamento de jogadores
- partida_routes.py: Sorteios, partidas e favoritos
- votacao_routes.py: Sistema de votação
- admin_routes.py: Dashboard administrativo
- stats_routes.py: Estatísticas, rankings e exportação
- juiz_routes.py: Fluxo do juiz
"""

from .auth_routes import auth_bp
from .jogador_crud_routes import jogador_bp
from .partida_routes import partida_bp
from .votacao_routes import votacao_bp
from .admin_routes import admin_bp
from .juiz_routes import juiz_bp
from .stats_routes import stats_bp

__all__ = [
    'auth_bp',
    'jogador_bp',
    'partida_bp',
    'votacao_bp',
    'admin_bp',
    'juiz_bp',
    'stats_bp',
]
