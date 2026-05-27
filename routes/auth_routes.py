"""
Rotas de Autenticação
- Login, logout, cadastro, perfil e alteração de senha
"""
import csv
from io import StringIO

from flask import Blueprint, request, render_template, redirect, url_for, session, Response, jsonify
from functools import wraps
import os
from services.auth_service import AuthService
from services.email_service import EmailService
from services.jogador_service import JogadorService
from services.jogador_stats_service import JogadorStatsService
from services.notificacao_service import NotificacaoService
from services.juiz_partida_service import JuizPartidaService

auth_bp = Blueprint('auth', __name__)

auth_service = AuthService()
email_service = EmailService()
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
    email = request.form.get('email', '').strip().lower()
    username = request.form.get('username', '').strip()
    senha = request.form.get('password', '')
    confirmar = request.form.get('confirmar_password', '')
    nivel = request.form.get('nivel', '5')
    tipo = request.form.get('tipo', 'avulso')
    posicao = request.form.get('posicao', 'linha')

    if not email or '@' not in email:
        return render_template('cadastro.html', erro='Informe um email valido'), 400
    if senha != confirmar:
        return render_template('cadastro.html', erro='A confirmacao de senha nao confere'), 400

    try:
        usuario = auth_service.criar_usuario(
            email=email,
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

        try:
            email_service.send_welcome_email(
                to_email=email,
                nome=usuario.get('nome', nome),
                username=usuario.get('username', username)
            )
        except Exception:
            pass

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


@auth_bp.route('/recuperar-senha', methods=['GET'])
def recuperar_senha_page():
    if session.get('user_id'):
        return redirect(url_for('jogador.index'))
    return render_template('recuperar_senha.html')


@auth_bp.route('/recuperar-senha', methods=['POST'])
def recuperar_senha_submit():
    email = request.form.get('email', '').strip().lower()
    mensagem = 'Se o email existir na base, enviamos instrucoes para redefinir sua senha.'

    if not email or '@' not in email:
        return render_template('recuperar_senha.html', erro='Informe um email valido'), 400

    usuario = auth_service.obter_por_email(email)
    if usuario:
        try:
            token = auth_service.gerar_token_reset(usuario.get('id'))
            reset_url = f"{email_service.base_url}{url_for('auth.definir_senha_page')}?token={token}"
            email_service.send_password_reset_email(
                to_email=usuario.get('email') or email,
                nome=usuario.get('nome') or usuario.get('username') or 'usuario',
                reset_url=reset_url,
            )
        except Exception:
            pass

    return render_template('recuperar_senha.html', sucesso=mensagem)


@auth_bp.route('/definir-senha', methods=['GET'])
def definir_senha_page():
    if session.get('user_id'):
        return redirect(url_for('jogador.index'))

    token = request.args.get('token', '').strip()
    usuario = auth_service.validar_token_reset(token)
    if not usuario:
        return render_template('definir_senha.html', erro='Link invalido ou expirado'), 400

    return render_template('definir_senha.html', token=token, usuario=usuario)


@auth_bp.route('/definir-senha', methods=['POST'])
def definir_senha_submit():
    token = request.form.get('token', '').strip()
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')

    usuario = auth_service.validar_token_reset(token)
    if not usuario:
        return render_template('definir_senha.html', erro='Link invalido ou expirado'), 400

    if nova_senha != confirmar_senha:
        return render_template('definir_senha.html', token=token, usuario=usuario, erro='A confirmacao de senha nao confere'), 400

    try:
        auth_service.definir_nova_senha(usuario.get('id'), nova_senha)
        return render_template('login.html', sucesso='Senha redefinida com sucesso! Agora voce pode entrar.')
    except ValueError as e:
        return render_template('definir_senha.html', token=token, usuario=usuario, erro=str(e)), 400
    except Exception:
        return render_template('definir_senha.html', token=token, usuario=usuario, erro='Erro ao redefinir senha'), 500


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
                stats_jogador.setdefault('efficiency', {})
                stats_jogador.setdefault('discipline', {})
                stats_jogador.setdefault('ultimos_resultados', {'forma': [], 'pontos': 0, 'partidas': []})
                stats_jogador.setdefault('mini_dashboard', {'kpis': {}, 'series_ultimos_5': []})
                stats_jogador.setdefault('planilha_metricas', [])
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
            stats_jogador.setdefault('efficiency', {})
            stats_jogador.setdefault('discipline', {})
            stats_jogador.setdefault('ultimos_resultados', {'forma': [], 'pontos': 0, 'partidas': []})
            stats_jogador.setdefault('mini_dashboard', {'kpis': {}, 'series_ultimos_5': []})
            stats_jogador.setdefault('planilha_metricas', [])
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


@auth_bp.route('/api/perfil/dashboard', methods=['GET'])
@login_required
def perfil_dashboard_api():
    """Retorna payload de dashboard do jogador do usuário logado."""
    try:
        meus = jogador_service.listar_por_usuario(session.get('user_id'))
        jogador_proprio = meus[0] if meus else None
        if not jogador_proprio:
            return jsonify({'ok': True, 'dashboard': None, 'mensagem': 'Usuario sem jogador vinculado'})

        stats_jogador = jogador_stats_service.obter_stats_jogador(jogador_proprio.nome)
        return jsonify({'ok': True, 'dashboard': stats_jogador})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao carregar dashboard do perfil: {str(e)}")
        return jsonify({'ok': False, 'erro': 'Falha ao carregar dashboard'}), 500


# ============================================================
# ROTA DE TESTE: Enviar senha temporária por email (DEV ONLY)
# ============================================================


@auth_bp.route('/teste-email', methods=['POST', 'GET'])
def teste_email_route():
    """Endpoint de teste para enviar uma senha temporaria a um usuario.

    Aceita `email` ou `username` via query string ou form data.
    Só funciona quando FLASK_ENV != 'production'.
    """
    if os.getenv('FLASK_ENV', 'development') == 'production':
        return jsonify({'ok': False, 'error': 'Endpoint desativado em production'}), 403

    email = (request.values.get('email') or '').strip().lower()
    username = (request.values.get('username') or '').strip().lower()

    usuario = None
    if email:
        usuario = auth_service.obter_por_email(email)
    elif username:
        usuario = auth_service.obter_por_username(username)
    else:
        return jsonify({'ok': False, 'error': 'Informe email ou username'}), 400

    if not usuario:
        return jsonify({'ok': False, 'error': 'Usuario nao encontrado'}), 404

    try:
        dados = auth_service.resetar_senha_por_admin(user_id=usuario.get('id'))
        # tentar enviar email com a senha temporaria
        result = None
        try:
            result = email_service.send_temporary_password_email(
                to_email=dados.get('email') or usuario.get('email'),
                nome=dados.get('nome') or dados.get('username') or 'usuario',
                username=dados.get('username') or '',
                senha_temporaria=dados.get('senha_temporaria') or ''
            )
        except Exception:
            # swallow email errors but report
            return jsonify({'ok': False, 'error': 'Falha ao enviar email'}), 500

        return jsonify({'ok': True, 'sent': result.ok, 'message_id': result.message_id})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Erro interno'}), 500



@auth_bp.route('/perfil/planilha.csv', methods=['GET'])
@login_required
def perfil_planilha_csv():
    """Exporta métricas do perfil em CSV (formato planilha)."""
    meus = jogador_service.listar_por_usuario(session.get('user_id'))
    jogador_proprio = meus[0] if meus else None
    if not jogador_proprio:
        return redirect(url_for('auth.perfil_page'))

    stats = jogador_stats_service.obter_stats_jogador(jogador_proprio.nome)
    linhas = stats.get('planilha_metricas', [])

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Data',
        'Partida ID',
        'Time',
        'Resultado',
        'Pontos',
        'Gols',
        'Assistencias',
        'Cartoes Amarelos',
        'Cartoes Vermelhos',
    ])

    for linha in linhas:
        writer.writerow([
            linha.get('data', ''),
            linha.get('partida_id', ''),
            linha.get('time', ''),
            linha.get('resultado', ''),
            linha.get('pontos', 0),
            linha.get('gols', 0),
            linha.get('assistencias', 0),
            linha.get('cartoes_amarelos', 0),
            linha.get('cartoes_vermelhos', 0),
        ])

    csv_content = output.getvalue()
    output.close()

    response = Response(csv_content, mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename=perfil_metricas.csv'
    return response
