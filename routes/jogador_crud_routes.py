"""
Rotas de Gerenciamento de Jogadores
- Listar, criar, editar, deletar jogadores
- Presença e seleção para partidas
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session
from functools import wraps
import unicodedata
from routes.commons import login_required
from services.jogador_service import JogadorService
from services.jogador_stats_service import JogadorStatsService
from services.juiz_partida_service import JuizPartidaService

jogador_bp = Blueprint('jogador_crud', __name__)

jogador_service = JogadorService()
jogador_stats_service = JogadorStatsService()
juiz_partida_service = JuizPartidaService()


# ============================================================
# DECORATORS
# ============================================================

def _is_admin():
    return session.get('role') in ['admin']


def _is_juiz():
    return session.get('role') == 'juiz'


def _destino_partida_oficial_aberta(estado):
    partida_atual = (estado or {}).get('partida_atual') or {}
    status = (estado or {}).get('status') or 'idle'
    sorteio_id = partida_atual.get('sorteio_id')
    if status == 'selecionando' or not sorteio_id:
        return None
    if status in {'resultado_registrado', 'votacao_aberta'} or partida_atual.get('votacao_partida_id'):
        return url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id)
    return url_for('juiz.juiz_times_page', sorteio_id=sorteio_id)


def _usuario_logado():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(session.get('user_id'))
    }


def _jogador_publico(jogador):
    if not jogador:
        return None
    return {
        'id': jogador.id,
        'nome': jogador.nome,
        'nivel': jogador.nivel,
        'tipo': jogador.tipo,
        'posicao': jogador.posicao,
        'presente': jogador.presente,
        'criado_em': jogador.criado_em,
    }


def _nome_para_ordenacao(nome: str) -> str:
    """Normaliza nomes para uma ordenacao alfabetica previsivel."""
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    sem_acentos = "".join(char for char in texto if not unicodedata.combining(char))
    return sem_acentos.casefold().strip()


def _preparar_jogadores_para_lista(jogadores):
    """Remove o proprio jogador da lista publica e ordena por nome."""
    usuario_id = session.get('user_id')
    role = session.get('role')

    jogadores_filtrados = [
        jogador for jogador in jogadores
        if not (role == 'usuario' and usuario_id and jogador.get('owner_user_id') == usuario_id)
    ]

    return sorted(
        jogadores_filtrados,
        key=lambda jogador: _nome_para_ordenacao(jogador.get('nome', '')),
    )


def admin_or_juiz_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Autenticacao obrigatoria'}), 401
            return redirect(url_for('auth.login_page'))
        if not (_is_admin() or _is_juiz()):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Acesso restrito'}), 403
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Autenticacao obrigatoria'}), 401
            return redirect(url_for('auth.login_page'))
        if not _is_admin():
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Acesso restrito ao administrador'}), 403
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# PÁGINA INICIAL
# ============================================================

@jogador_bp.route('/')
def index():
    """Página inicial com lista de jogadores"""
    if not session.get('user_id'):
        return redirect(url_for('auth.login_page'))

    if session.get('senha_temporaria_ativa'):
        return redirect(url_for('auth.perfil_page'))

    if _is_juiz():
        return redirect(url_for('juiz.jogar_page'))

    try:
        jogadores = _preparar_jogadores_para_lista(jogador_service.listar_para_dict())
        jogadores_premium = []

        for jogador in jogadores:
            stats = jogador_stats_service.obter_stats_jogador(jogador.get('nome', ''))
            jogadores_premium.append({
                **jogador,
                'stats_card': {
                    'wins': stats.get('vitórias', stats.get('vitorias', 0)),
                    'matches': stats.get('total_partidas', 0),
                    'approval': stats.get('win_rate', 0.0),
                    'approval_valid': stats.get('win_rate_valido', True),
                }
            })

        return render_template(
            'index.html',
            jogadores=jogadores_premium,
            total_jogadores=len(jogadores_premium),
            usuario=_usuario_logado()
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao listar jogadores: {str(e)}")
        return render_template('index.html', erro='Erro ao carregar jogadores'), 500


# ============================================================
# API: LISTAR JOGADORES
# ============================================================

@jogador_bp.route('/api/jogadores', methods=['GET'])
@login_required
def listar_jogadores_api():
    """API: Lista todos os jogadores"""
    try:
        return jsonify([_jogador_publico(jogador) for jogador in jogador_service.listar()])
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao listar jogadores: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao listar jogadores'}), 500


# ============================================================
# API: CRIAR JOGADOR
# ============================================================

@jogador_bp.route('/api/jogadores', methods=['POST'])
@admin_or_juiz_required
def criar_jogador_api():
    """API: Cria novo jogador"""
    try:
        dados = request.get_json(silent=True) or {}
        nome = dados.get('nome', '').strip()
        if not nome or len(nome) < 2:
            raise ValueError('Nome deve ter ao menos 2 caracteres')
        nome_partes = [p for p in nome.split() if p]
        if len(nome_partes) < 2:
            raise ValueError('Por favor, insira o nome e sobrenome do jogador.')

        jogador = jogador_service.criar(
            nome=nome,
            nivel=float(dados.get('nivel', 5.5)),
            tipo=dados.get('tipo', 'avulso'),
            posicao=dados.get('posicao', 'linha')
        )
        return jsonify({
            'sucesso': True,
            'jogador': _jogador_publico(jogador),
            'mensagem': 'Jogador criado com sucesso'
        }), 201
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao criar jogador: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao criar jogador'}), 500


@jogador_bp.route('/add', methods=['POST'])
@admin_or_juiz_required
def adicionar_jogador():
    """Formulário: Adiciona novo jogador"""
    try:
        nome = request.form.get('nome', '').strip()
        if not nome or len(nome) < 2:
            raise ValueError('Nome deve ter ao menos 2 caracteres')
        nome_partes = [p for p in nome.split() if p]
        if len(nome_partes) < 2:
            raise ValueError('Por favor, insira o nome e sobrenome do jogador.')
        nivel = float(request.form.get('nivel', 5.5))
        tipo = request.form.get('tipo', '').strip()
        posicao = request.form.get('posicao', '').strip()

        if not tipo or not posicao:
            raise ValueError('Selecione o tipo e a posição do jogador')
        
        jogador_service.criar(nome, nivel, tipo, posicao)
        if _is_juiz():
            return redirect(url_for('juiz.jogar_page'))
        return redirect(url_for('jogador_crud.index'))
    except ValueError as e:
        return f"Erro de validação: {str(e)}", 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao adicionar jogador: {str(e)}")
        return "Erro ao adicionar jogador", 500


# ============================================================
# API: OBTER JOGADOR
# ============================================================

@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['GET'])
@login_required
def obter_jogador(jogador_id):
    """API: Obtém jogador por ID"""
    try:
        jogador = jogador_service.obter_por_id(jogador_id, None if _is_admin() else session.get('user_id'))
        if not jogador:
            return jsonify({'erro': 'Jogador não encontrado'}), 404
        return jsonify(_jogador_publico(jogador))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao obter jogador: {str(e)}")
        return jsonify({'erro': 'Erro ao obter jogador'}), 500


# ============================================================
# API: ATUALIZAR JOGADOR
# ============================================================

@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['PUT'])
@admin_required
def atualizar_jogador(jogador_id):
    """API: Atualiza jogador"""
    try:
        dados = request.get_json(silent=True) or {}
        jogador = jogador_service.atualizar(
            jogador_id,
            nome=dados.get('nome'),
            nivel=float(dados.get('nivel')) if dados.get('nivel') is not None else None,
            tipo=dados.get('tipo'),
            posicao=dados.get('posicao')
        )
        if not jogador:
            return jsonify({'erro': 'Jogador não encontrado'}), 404
        return jsonify({
            'sucesso': True,
            'jogador': jogador.para_dict(),
            'mensagem': 'Jogador atualizado com sucesso'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao atualizar jogador: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao atualizar jogador'}), 500


# ============================================================
# FORMULÁRIO: EDITAR JOGADOR
# ============================================================

@jogador_bp.route('/jogadores/<jogador_id>/editar', methods=['GET'])
@admin_required
def editar_jogador_page(jogador_id):
    """Página: Formulário de edição de jogador (admin)"""
    try:
        jogador = jogador_service.obter_por_id(jogador_id)
        if not jogador:
            return redirect(url_for('jogador_crud.index'))

        next_url = request.args.get('next', '')
        return render_template('editar_jogador.html', jogador=jogador, usuario=_usuario_logado(), next_url=next_url)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao carregar formulário de edição: {str(e)}")
        return redirect(url_for('jogador_crud.index'))


@jogador_bp.route('/jogadores/<jogador_id>/editar', methods=['POST'])
@admin_required
def editar_jogador_post(jogador_id):
    """Form handler: atualiza jogador via form (admin)"""
    nome = request.form.get('nome', '').strip()
    if not nome or len(nome) < 2:
        raise ValueError('Nome deve ter ao menos 2 caracteres')
    nome_partes = [p for p in nome.split() if p]
    if len(nome_partes) < 2:
        raise ValueError('Por favor, insira o nome e sobrenome do jogador.')
    nivel = request.form.get('nivel')
    tipo = request.form.get('tipo')
    posicao = request.form.get('posicao')
    next_url = request.form.get('next') or request.args.get('next', '')

    try:
        jogador = jogador_service.atualizar(
            jogador_id,
            nome=nome or None,
            nivel=float(nivel) if nivel else None,
            tipo=tipo or None,
            posicao=posicao or None
        )
        if not jogador:
            return "Jogador não encontrado", 404
        if next_url:
            return redirect(next_url)
        return redirect(url_for('auth.perfil_jogador_publico', jogador_id=jogador.id))
    except ValueError as e:
        jogador = jogador_service.obter_por_id(jogador_id)
        return render_template('editar_jogador.html', jogador=jogador, usuario=_usuario_logado(), erro=str(e), next_url=next_url), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao editar jogador: {str(e)}")
        return render_template('editar_jogador.html', jogador=None, usuario=_usuario_logado(), erro="Erro interno", next_url=next_url), 500


@jogador_bp.route('/perfil/<jogador_id>', methods=['GET'])
@jogador_bp.route('/jogadores/<jogador_id>/perfil', methods=['GET'])
@login_required
def perfil_jogador_publico(jogador_id):
    """Alias para visualização de perfil público de jogador"""
    from routes.auth_routes import perfil_jogador_publico as auth_perfil_publico
    return auth_perfil_publico(jogador_id)


# ============================================================
# API: DELETAR JOGADOR
# ============================================================

@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['DELETE'])
@admin_required
def deletar_jogador(jogador_id):
    """API: Deleta jogador"""
    try:
        sucesso = jogador_service.deletar(jogador_id)
        if not sucesso:
            return jsonify({'erro': 'Jogador não encontrado'}), 404
        return jsonify({'sucesso': True, 'mensagem': 'Jogador deletado com sucesso'})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao deletar jogador: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao deletar jogador'}), 500


@jogador_bp.route('/delete/<jogador_id>')
@admin_required
def deletar_jogador_form(jogador_id):
    """Formulário: Deleta jogador"""
    try:
        jogador_service.deletar(jogador_id)
        return redirect(url_for('jogador_crud.index'))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao deletar jogador: {str(e)}")
        return redirect(url_for('jogador_crud.index'))


# ============================================================
# PRESENÇA: SELEÇÃO DE JOGADORES
# ============================================================

@jogador_bp.route('/selecionar')
def selecionar_jogadores():
    """Página para selecionar jogadores para o jogo"""
    if _is_admin():
        return redirect(url_for('jogador_crud.index'))

    if _is_juiz():
        return redirect(url_for('juiz.jogar_page'))

    try:
        todos_jogadores = jogador_service.listar()
        fixos = [j for j in todos_jogadores if j.tipo == "fixo"]
        avulsos = [j for j in todos_jogadores if j.tipo == "avulso"]
        presentes = [j for j in todos_jogadores if j.presente]
        
        return render_template(
            'selecionar.html',
            todos_jogadores=todos_jogadores,
            fixos=fixos,
            avulsos=avulsos,
            presentes=presentes,
            total_presentes=len(presentes),
            total_jogadores=len(todos_jogadores),
            usuario=_usuario_logado()
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao carregar seleção: {str(e)}")
        return render_template('selecionar.html', erro='Erro ao carregar jogadores'), 500


@jogador_bp.route('/api/presenca', methods=['POST'])
@admin_or_juiz_required
def atualizar_presenca():
    """API: Marca jogadores como presentes"""
    try:
        if _is_juiz():
            estado = juiz_partida_service.obter_estado()
            if (estado.get('status') or 'idle') != 'selecionando':
                destino = _destino_partida_oficial_aberta(estado)
                if destino:
                    return jsonify({
                        'sucesso': False,
                        'erro': 'Ja existe uma partida aberta. Redirecionando para ela.',
                        'redirect_url': destino,
                    }), 409
                return jsonify({
                    'sucesso': False,
                    'erro': 'O fluxo do juiz nao esta na etapa de selecao',
                }), 409

        dados = request.get_json(silent=True) or {}
        jogador_ids = dados.get('jogador_ids', [])
        
        if len(jogador_ids) not in [10, 15, 20]:
            return jsonify({
                'sucesso': False,
                'erro': f'Selecione exatamente 10, 15 ou 20 jogadores. Selecionados: {len(jogador_ids)}'
            }), 400
        
        jogador_service.marcar_presenca(jogador_ids)
        if _is_juiz():
            juiz_partida_service.registrar_selecao(len(jogador_ids), jogador_ids)
        
        return jsonify({
            'sucesso': True,
            'total_presentes': len(jogador_ids),
            'mensagem': f'{len(jogador_ids)} jogadores selecionados com sucesso'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao atualizar presença: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao atualizar presença'}), 500


@jogador_bp.route('/api/presenca/limpar', methods=['POST'])
@admin_or_juiz_required
def limpar_presenca():
    """API: Limpa seleção de presença"""
    try:
        if _is_juiz():
            estado = juiz_partida_service.obter_estado()
            if (estado.get('status') or 'idle') not in {'selecionando', 'idle'}:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Nao e possivel limpar a selecao fora da etapa de selecao'
                }), 409

        jogador_service.limpar_presenca()
        return jsonify({
            'sucesso': True,
            'mensagem': 'Seleção limpa'
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao limpar presença: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao limpar seleção'}), 500
