"""
Funções e decoradores compartilhados para todas as rotas.
"""
from flask import session, request, jsonify, redirect, url_for
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# ============================================================
# VERIFICADORES DE ROLE
# ============================================================

def _is_admin():
    """Verifica se usuário é admin"""
    return session.get('role') in ['super_admin', 'admin']


def _is_juiz():
    """Verifica se usuário é juiz"""
    return session.get('role') == 'juiz'


def _usuario_logado():
    """Retorna dados do usuário logado"""
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(session.get('user_id'))
    }


# ============================================================
# RESPOSTAS PADRÃO
# ============================================================

def _resposta_nao_autenticado():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Autenticacao obrigatoria'}), 401
    return redirect(url_for('auth.login_page'))


def _resposta_sem_permissao():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Acesso restrito ao administrador'}), 403
    return redirect(url_for('jogador.index'))


def _resposta_somente_leitura():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Usuario com acesso somente leitura'}), 403
    return redirect(url_for('jogador.index'))


def _resposta_voto_somente_usuario():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Apenas usuarios podem votar'}), 403
    return redirect(url_for('jogador.index'))


def _resposta_votacao_pendente(partida):
    mensagem = 'Voce precisa votar nesta rodada antes de continuar'
    if request.path.startswith('/api/'):
        return jsonify({
            'sucesso': False,
            'erro': mensagem,
            'votacao_pendente': True,
            'partida_id': (partida or {}).get('id'),
            'sorteio_id': (partida or {}).get('sorteio_id'),
        }), 409
    return redirect(url_for('votacao.votacao_page'))


# ============================================================
# DECORADORES
# ============================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return _resposta_nao_autenticado()
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return _resposta_nao_autenticado()
        if not _is_admin():
            return _resposta_sem_permissao()
        return f(*args, **kwargs)
    return wrapper


def admin_or_juiz_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return _resposta_nao_autenticado()
        if not (_is_admin() or _is_juiz()):
            return _resposta_sem_permissao()
        return f(*args, **kwargs)
    return wrapper
