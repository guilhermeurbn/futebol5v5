"""
Funções utilitárias da aplicação
"""
from functools import wraps
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def handle_api_error(f):
    """
    Decorator para tratamento de erros em endpoints API
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return jsonify({'sucesso': False, 'erro': 'Erro interno do servidor'}), 500
    return decorated_function


def formatar_lista_jogadores(jogadores: list) -> str:
    """Formata lista de jogadores para exibição"""
    return ", ".join([f"{j.nome} ({j.nivel})" for j in jogadores])
