"""
Rotas de Autenticação
- Login, logout, cadastro, perfil e alteração de senha
"""
from flask import Blueprint, request, render_template, redirect, url_for, session
from functools import wraps
from services.auth_service import AuthService
from services.jogador_service import JogadorService
from services.jogador_stats_service import JogadorStatsService
from services.notificacao_service import NotificacaoService
from services.juiz_partida_service import JuizPartidaService

auth_bp = Blueprint('auth', __name__)

auth_service = AuthService()
jogador_service = JogadorService()
jogador_stats_service = JogadorStatsService()
notificacao_service = NotificacaoService()
juiz_partida_service = JuizPartidaService()


# ============================================================
# HELPERS
# ============================================================

def _usuario_logado():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(session.get('user_id'))
    }


def _is_admin():
    return session.get('role') in ['super_admin', 'admin']


def _is_juiz():
    return session.get('role') == 'juiz'


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# CONTEXT PROCESSORS
# ============================================================

@auth_bp.app_context_processor
def inject_auth_user():
    usuario = _usuario_logado()
    juiz_partida_ativa = False

    if usuario.get('role') == 'juiz' and usuario.get('autenticado'):
        try:
            estado = juiz_partida_service.obter_estado()
            juiz_partida_ativa = bool(estado.get('partida_atual')) and estado.get('status') != 'idle'
        except Exception:
            juiz_partida_ativa = False

    return {
        'auth_user': usuario,
        'juiz_partida_ativa': juiz_partida_ativa,
    }


# ============================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================

@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Página de login"""
    if session.get('user_id'):
        return redirect(url_for('jogador.index'))
    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login_submit():
    """Handler para submit de login"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    try:
        usuario = auth_service.autenticar(username, password)
        if not usuario:
            return render_template('login.html', erro='Usuario ou senha invalidos'), 401

        session['user_id'] = usuario['id']
        session['username'] = usuario['username']
        session['nome'] = usuario['nome']
        session['role'] = usuario['role']
        session['senha_temporaria_ativa'] = bool(usuario.get('senha_temporaria_ativa'))
        session.modified = True
        return redirect(url_for('jogador.index'))
    except ValueError as e:
        return render_template('login.html', erro=str(e)), 400
    except Exception as e:
        return render_template('login.html', erro='Erro ao autenticar usuario'), 500


@auth_bp.route('/cadastro', methods=['GET'])
def cadastro_page():
    """Página de cadastro de novo usuário"""
    if session.get('user_id'):
        return redirect(url_for('jogador.index'))
    return render_template('cadastro.html')


@auth_bp.route('/cadastro', methods=['POST'])
def cadastro_submit():
    """Handler para submit de cadastro"""
    nome = request.form.get('nome', '').strip()
    username = request.form.get('username', '').strip()
    senha = request.form.get('password', '')
    confirmar = request.form.get('confirmar_password', '')
    nivel = request.form.get('nivel', '5')
    tipo = request.form.get('tipo', 'avulso')
    posicao = request.form.get('posicao', 'linha')

    if senha != confirmar:
        return render_template('cadastro.html', erro='A confirmacao de senha nao confere'), 400

    try:
        usuario = auth_service.criar_usuario(
            username=username,
            nome=nome,
            password=senha,
            role='usuario'
        )

        # Cada usuário novo já nasce com seu próprio jogador
        jogador_service.criar(
            nome=nome,
            nivel=int(nivel),
            tipo=tipo,
            posicao=posicao,
            owner_user_id=usuario.get('id')
        )

        notificacao_service.criar_notificacao(
            titulo='Novo cadastro de usuario',
            mensagem=f'Usuario {usuario.get("username")} ({usuario.get("nome")}) acabou de se cadastrar.',
            tipo='cadastro'
        )

        return render_template(
            'login.html',
            sucesso='Cadastro realizado com sucesso! Entre com seu usuario e senha.'
        )
    except ValueError as e:
        return render_template('cadastro.html', erro=str(e)), 400
    except Exception as e:
        return render_template('cadastro.html', erro='Erro ao criar usuario'), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout do usuário"""
    session.clear()
    return redirect(url_for('auth.login_page'))


# ============================================================
# PERFIL E SENHA
# ============================================================

@auth_bp.route('/perfil', methods=['GET'])
@login_required
def perfil_page():
    """Página de perfil do usuário logado"""
    jogador_proprio = None
    stats_jogador = None
    partida_juiz_em_andamento = None
    
    try:
        if not _is_admin():
            meus = jogador_service.listar_por_usuario(session.get('user_id'))
            jogador_proprio = meus[0] if meus else None
            
            # Obter estatísticas do jogador
            if jogador_proprio:
                stats_jogador = jogador_stats_service.obter_stats_jogador(jogador_proprio.nome)
    except ValueError as e:
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            erro_stats=f'Erro ao carregar estatísticas: {str(e)}'
        ), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao obter stats do perfil: {str(e)}")

    if _is_juiz():
        estado_fluxo = juiz_partida_service.obter_estado()
        partida_juiz_em_andamento = estado_fluxo.get('partida_atual')
    
    return render_template(
        'perfil.html',
        usuario=_usuario_logado(),
        jogador_proprio=jogador_proprio,
        stats_jogador=stats_jogador,
        partida_juiz_em_andamento=partida_juiz_em_andamento
    )


@auth_bp.route('/jogadores/<jogador_id>/perfil', methods=['GET'])
@login_required
def perfil_jogador_publico(jogador_id):
    """Visualiza perfil público de outro jogador"""
    try:
        jogador = jogador_service.obter_por_id(jogador_id)
        if not jogador:
            return redirect(url_for('jogador.index'))

        stats_jogador = None
        try:
            stats_jogador = jogador_stats_service.obter_stats_jogador(jogador.nome)
        except ValueError:
            # Se houver erro ao obter stats, continuar sem elas
            pass

        return render_template(
            'perfil_jogador.html',
            jogador=jogador,
            stats_jogador=stats_jogador,
            usuario=_usuario_logado()
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao carregar perfil público: {str(e)}")
        return redirect(url_for('jogador.index'))


@auth_bp.route('/perfil/senha', methods=['POST'])
@login_required
def perfil_alterar_senha():
    """Altera a senha do usuário logado"""
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')

    if nova_senha != confirmar_senha:
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            erro_senha='A confirmacao de senha nao confere'
        ), 400

    try:
        auth_service.alterar_senha(
            user_id=session.get('user_id'),
            senha_atual=senha_atual,
            nova_senha=nova_senha
        )
        session['senha_temporaria_ativa'] = False
        session.modified = True
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=(jogador_service.listar_por_usuario(session.get('user_id')) or [None])[0],
            sucesso_senha='Senha alterada com sucesso!'
        )
    except ValueError as e:
        jogador_proprio = (jogador_service.listar_por_usuario(session.get('user_id')) or [None])[0]
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=jogador_proprio,
            erro_senha=str(e)
        ), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao alterar senha: {str(e)}")
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            erro_senha='Erro ao alterar senha'
        ), 500
