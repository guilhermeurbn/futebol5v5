"""
Rotas de Autenticação
- Login, logout, cadastro, perfil e alteração de senha
"""
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from functools import wraps
import logging
import os
from services.auth_service import AuthService
from services.email_service import EmailService
from services.jogador_service import JogadorService
from services.jogador_stats_service import JogadorStatsService
from services.notificacao_service import NotificacaoService
from services.juiz_partida_service import JuizPartidaService

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

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
        if session.get('senha_temporaria_ativa') and request.endpoint not in {
            'auth.perfil_page',
            'auth.perfil_alterar_senha',
            'auth.logout',
        }:
            return redirect(url_for('auth.perfil_page'))
        return f(*args, **kwargs)
    return wrapper


def _is_request_local():
    remote_addr = request.remote_addr or ''
    return remote_addr in {'127.0.0.1', '::1', 'localhost'}


def _obter_notas_e_atributos_jogador(jogador, stats_jogador):
    if not jogador or not stats_jogador:
        return
        
    import hashlib
    from services.db import load_json_data
    
    # 1. Carrega notas das partidas do jogador a partir do histórico de votações
    votacoes = load_json_data("votacoes_partidas", [])
    notas_por_partida = {}
    total_nota = 0.0
    qtd_votos = 0
    
    for partida in votacoes:
        if partida.get("status") == "encerrada":
            ranking = partida.get("ranking") or {}
            ranking_jogadores = ranking.get("ranking_jogadores") or []
            for r in ranking_jogadores:
                if r.get("jogador_nome") == jogador.nome:
                    nota_media = r.get("nota_media", 0)
                    partida_id = partida.get("id")
                    notas_por_partida[partida_id] = nota_media
                    total_nota += nota_media
                    qtd_votos += 1
                    break
                    
    nota_geral = round(total_nota / qtd_votos, 2) if qtd_votos else 7.0
    stats_jogador["nota_media_geral"] = f"{nota_geral:.2f}"
    
    # Injeta a nota individual e placar real em cada partida no histórico
    for jogo in stats_jogador.get("historico_partidas", []):
        if not isinstance(jogo, dict):
            continue
        partida_id = jogo.get("partida_id")
        jogo["nota_partida"] = f"{notas_por_partida.get(partida_id, 0.0):.1f}"
        
        # Encontrar a partida correspondente no json para pegar os gols reais
        for partida in votacoes:
            if partida.get("id") == partida_id:
                resultado_partida = partida.get("resultado_partida") or {}
                gols_times = resultado_partida.get("gols_times") or [0, 0]
                jogo["gols_times"] = gols_times
                break
        else:
            jogo["gols_times"] = [0, 0]

    # 2. Calcula os 5 atributos para o gráfico de radar determinístico
    h = hashlib.md5(jogador.nome.encode("utf-8")).hexdigest()
    def get_seed_val(offset, min_val=6.0, max_val=9.5):
        val = int(h[offset:offset+2], 16) / 255.0
        return min_val + val * (max_val - min_val)

    posicao = getattr(jogador, 'posicao', 'linha') or 'linha'
    nivel = float(getattr(jogador, 'nivel', 7.0) or 7.0)
    
    # Ofensivo: Maior se for linha, aumenta com gols
    gols_por_jogo = float(stats_jogador.get("gols_por_partida", 0.0) or 0.0)
    assist_por_jogo = float(stats_jogador.get("assistencias_por_partida", 0.0) or 0.0)
    ofensivo_base = 8.0 if posicao == "linha" else 4.0
    ofensivo_bonus = min(2.0, gols_por_jogo * 1.5 + assist_por_jogo * 1.0)
    ofensivo = ofensivo_base + ofensivo_bonus
    ofensivo = ofensivo * 0.6 + get_seed_val(0, 5.0, 9.5) * 0.4

    # Defensivo: Maior se for goleiro
    defensivo_base = 9.0 if posicao == "goleiro" else 6.0
    defensivo = defensivo_base * 0.7 + get_seed_val(2, 5.0, 9.5) * 0.3

    # Técnica: Baseado em nível e nota geral
    tecnica_base = (nivel * 0.6 + nota_geral * 0.4)
    tecnica = tecnica_base * 0.8 + get_seed_val(4, 6.0, 9.5) * 0.2

    # Físico: Variação ao redor do nível
    fisico = get_seed_val(6, 6.0, 9.2)
    if posicao == "goleiro":
        fisico = fisico * 0.9 + 0.5
        
    # Comprometimento: Aumenta levemente com número de partidas jogadas
    total_jogos = int(stats_jogador.get("total_partidas", 0) or 0)
    comp_bonus = min(2.0, total_jogos * 0.2)
    comprometimento = 7.0 + comp_bonus
    comprometimento = comprometimento * 0.7 + get_seed_val(8, 7.0, 9.8) * 0.3

    stats_jogador["atributos"] = {
        "ofensivo": round(min(10.0, max(1.0, ofensivo)), 1),
        "defensivo": round(min(10.0, max(1.0, defensivo)), 1),
        "tecnica": round(min(10.0, max(1.0, tecnica)), 1),
        "fisico": round(min(10.0, max(1.0, fisico)), 1),
        "comprometimento": round(min(10.0, max(1.0, comprometimento)), 1)
    }


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
        if session.get('senha_temporaria_ativa'):
            return redirect(url_for('auth.perfil_page'))
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        if session.get('role') in ['admin', 'super_admin']:
            return redirect(url_for('jogador.index'))
        return redirect(url_for('auth.perfil_page'))
    
    sucesso = request.args.get('sucesso')
    erro = request.args.get('erro')
    return render_template('login.html', sucesso=sucesso, erro=erro)


@auth_bp.route('/login', methods=['POST'])
def login_submit():
    """Handler para submit de login"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    remember_me = request.form.get('remember_me') in {'1', 'on', 'true', 'yes'}
    
    try:
        usuario = auth_service.autenticar(username, password)
        if not usuario:
            return render_template('login.html', erro='Usuario ou senha invalidos'), 401

        session.permanent = remember_me
        if remember_me:
            session['remember_me'] = True
        else:
            session.pop('remember_me', None)
        session['user_id'] = usuario['id']
        session['username'] = usuario['username']
        session['nome'] = usuario['nome']
        session['role'] = usuario['role']
        session['senha_temporaria_ativa'] = bool(usuario.get('senha_temporaria_ativa'))
        session.modified = True
        if session['senha_temporaria_ativa']:
            return redirect(url_for('auth.perfil_page'))
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        if session.get('role') in ['admin', 'super_admin']:
            return redirect(url_for('jogador.index'))
        return redirect(url_for('auth.perfil_page'))
    except ValueError as e:
        return render_template('login.html', erro=str(e)), 400
    except Exception as e:
        return render_template('login.html', erro='Erro ao autenticar usuario'), 500


@auth_bp.route('/cadastro', methods=['GET'])
def cadastro_page():
    """Página de cadastro de novo usuário"""
    if session.get('user_id'):
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        return redirect(url_for('auth.perfil_page'))
    return render_template('cadastro.html')


@auth_bp.route('/cadastro', methods=['POST'])
def cadastro_submit():
    """Handler para submit de cadastro"""
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    username = request.form.get('username', '').strip()
    senha = request.form.get('password', '')
    confirmar = request.form.get('confirmar_password', '')
    nivel = request.form.get('nivel', '5.5')
    tipo = request.form.get('tipo', 'avulso')
    posicao = request.form.get('posicao', 'linha')

    if not email or '@' not in email:
        return render_template('cadastro.html', erro='Informe um email valido'), 400
    if senha != confirmar:
        return render_template('cadastro.html', erro='A confirmacao de senha nao confere'), 400

    if not nome or len(nome) < 2:
        return render_template('cadastro.html', erro='Nome deve ter ao menos 2 caracteres'), 400
    nome_partes = [p for p in nome.split() if p]
    if len(nome_partes) < 2:
        return render_template('cadastro.html', erro='Por favor, digite seu nome e sobrenome.'), 400

    try:
        usuario = auth_service.criar_usuario(
            email=email,
            username=username,
            nome=nome,
            password=senha,
            role='usuario'
        )

        try:
            nivel_val = float(nivel)
        except (ValueError, TypeError):
            nivel_val = 5.5

        # Cada usuário novo já nasce com seu próprio jogador.
        # Se essa etapa falhar, desfazemos o usuário para evitar conta órfã.
        try:
            jogador_service.criar(
                nome=nome,
                nivel=nivel_val,
                tipo=tipo,
                posicao=posicao,
                owner_user_id=usuario.get('id')
            )
        except Exception as exc:
            try:
                auth_service.deletar_usuario(usuario.get('id'))
            except Exception as rollback_exc:
                logger.error(
                    'Falha ao desfazer usuario %s apos erro ao criar jogador: %s',
                    usuario.get('username'),
                    rollback_exc,
                )
            logger.error('Erro ao criar perfil de jogador para %s: %s', usuario.get('username'), exc)
            raise RuntimeError('Erro ao criar perfil de jogador') from exc

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
        msg = str(e)
        if msg == "Username ja existe":
            msg = "Este nome de usuário já está em uso. Por favor, escolha outro."
        elif msg == "Email ja existe":
            msg = "Este e-mail já está em uso. Por favor, escolha outro."
        return render_template('cadastro.html', erro=msg), 400
    except Exception as e:
        return render_template('cadastro.html', erro='Erro ao criar usuario'), 500


@auth_bp.route('/recuperar-senha', methods=['GET'])
def recuperar_senha_page():
    if session.get('user_id'):
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        return redirect(url_for('auth.perfil_page'))
    return render_template('recuperar_senha.html')


@auth_bp.route('/recuperar-senha', methods=['POST'])
def recuperar_senha_submit():
    email = request.form.get('email', '').strip().lower()
    mensagem = 'Se o email existir na base, enviamos um link de redefinicao de senha.'

    if not email or '@' not in email:
        return render_template('recuperar_senha.html', erro='Informe um email valido'), 400

    usuario = auth_service.obter_por_email(email)
    if not usuario:
        return render_template('recuperar_senha.html', sucesso=mensagem)

    try:
        token = auth_service.gerar_token_reset(usuario.get('id'))
        base_url = (os.getenv('APP_BASE_URL') or request.url_root).rstrip('/')
        reset_url = f"{base_url}{url_for('auth.definir_senha_page', token=token)}"
        resultado_email = email_service.send_password_reset_email(
            to_email=usuario.get('email') or email,
            nome=usuario.get('nome') or usuario.get('username') or 'usuario',
            reset_url=reset_url,
        )
        if not resultado_email.ok:
            logger.warning('Falha ao enviar email de recuperacao para %s: %s', email, resultado_email.error)
    except Exception as exc:
        logger.warning('Erro ao processar recuperacao de senha para %s: %s', email, exc)

    return render_template('recuperar_senha.html', sucesso=mensagem)


@auth_bp.route('/definir-senha', methods=['GET'])
def definir_senha_page():
    if session.get('user_id'):
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        return redirect(url_for('auth.perfil_page'))

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
                
                # Calcular e injetar notas e atributos determinísticos
                _obter_notas_e_atributos_jogador(jogador_proprio, stats_jogador)
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
        if jogador.owner_user_id == session.get('user_id'):
            return redirect(url_for('auth.perfil_page'))

        stats_jogador = None
        try:
            stats_jogador = jogador_stats_service.obter_stats_jogador(jogador.nome)
            stats_jogador.setdefault('efficiency', {})
            stats_jogador.setdefault('discipline', {})
            stats_jogador.setdefault('ultimos_resultados', {'forma': [], 'pontos': 0, 'partidas': []})
            stats_jogador.setdefault('mini_dashboard', {'kpis': {}, 'series_ultimos_5': []})
            stats_jogador.setdefault('planilha_metricas', [])
            
            # Calcular e injetar notas e atributos determinísticos
            _obter_notas_e_atributos_jogador(jogador, stats_jogador)
        except Exception as e:
            # Se houver qualquer erro ao obter stats, logar e continuar sem elas
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao carregar estatísticas do perfil público: {str(e)}")
            pass

        owner_user = None
        if jogador.owner_user_id:
            owner_user = auth_service.obter_por_id(jogador.owner_user_id)

        return render_template(
            'perfil_jogador.html',
            jogador=jogador,
            stats_jogador=stats_jogador,
            usuario=_usuario_logado(),
            owner_user=owner_user
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
    senha_temporaria = bool(session.get('senha_temporaria_ativa'))

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
            nova_senha=nova_senha,
            senha_temporaria=senha_temporaria,
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


# ============================================================
# ROTA DE TESTE: Enviar senha temporária por email (DEV ONLY)
# ============================================================


@auth_bp.route('/teste-email', methods=['POST', 'GET'])
@login_required
def teste_email_route():
    """Endpoint de teste para enviar uma senha temporaria a um usuario.

    Aceita `email` ou `username` via query string ou form data.
    Só funciona quando FLASK_ENV != 'production'.
    """
    if os.getenv('FLASK_ENV', 'development') == 'production' or not _is_request_local() or not _is_admin():
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
        senha_teste = auth_service.gerar_senha_temporaria()
        result = email_service.send_temporary_password_email(
            to_email=usuario.get('email') or email,
            nome=usuario.get('nome') or usuario.get('username') or 'usuario',
            username=usuario.get('username') or '',
            senha_temporaria=senha_teste,
        )
        if not result.ok:
            return jsonify({'ok': False, 'error': result.error or 'Falha ao enviar email'}), 500

        return jsonify({'ok': True, 'sent': result.ok, 'message_id': result.message_id})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Erro interno'}), 500

# Rota simples de teste de email (envio genérico)
@auth_bp.route('/teste-email/simple', methods=['GET'])
@login_required
def teste_email_simples():
    """Envio rápido para checar se Resend funciona.

    Use `?email=destinatario@example.com` para alterar o destinatário.
    Desabilitado em `production`.
    """
    if os.getenv('FLASK_ENV', 'development') == 'production' or not _is_request_local() or not _is_admin():
        return "Endpoint desativado em production", 403

    destinatario = request.args.get('email', 'teuemail@gmail.com').strip()
    if not destinatario or '@' not in destinatario:
        return "Informe um email valido via ?email=...", 400

    try:
        resultado = email_service.send_email(
            to_email=destinatario,
            subject='Teste NaTrave',
            html='<h1>Email funcionando 🚀</h1>'
        )
        if resultado.ok:
            return f"Email enviado! id={resultado.message_id}", 200
        return f"Falha ao enviar: {resultado.error}", 500
    except Exception as e:
        return f"Erro interno: {e}", 500


@auth_bp.route('/perfil/apagar-conta', methods=['POST'])
@login_required
def apagar_conta():
    """Apaga a conta do usuário logado após validação de palavra-chave e senha"""
    confirmar_palavra = request.form.get('confirmar_palavra', '').strip().upper()
    senha = request.form.get('senha', '')
    user_id = session.get('user_id')

    # 1. Validar a palavra-chave
    if confirmar_palavra != 'APAGAR':
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=(jogador_service.listar_por_usuario(user_id) or [None])[0],
            erro_deletar='Você deve digitar a palavra APAGAR para confirmar.'
        ), 400

    try:
        # 2. Validar a senha atual
        user = auth_service.obter_por_id(user_id)
        if not user:
            return redirect(url_for('auth.logout'))

        from werkzeug.security import check_password_hash
        if not check_password_hash(user.get('password_hash', ''), senha):
            return render_template(
                'perfil.html',
                usuario=_usuario_logado(),
                jogador_proprio=(jogador_service.listar_por_usuario(user_id) or [None])[0],
                erro_deletar='Senha atual incorreta. Confirmação falhou.'
            ), 400

        # 3. Executar deleção (passando executor_id=None para evitar a restrição de self-deletion no painel admin)
        auth_service.deletar_usuario(user_id, executor_id=None)

        # 4. Limpar a sessão
        session.clear()
        
        # Redirecionar para login com mensagem de sucesso
        return redirect(url_for('auth.login_page', sucesso='Sua conta foi excluída permanentemente.'))

    except ValueError as e:
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=(jogador_service.listar_por_usuario(user_id) or [None])[0],
            erro_deletar=str(e)
        ), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao apagar conta: {str(e)}")
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=(jogador_service.listar_por_usuario(user_id) or [None])[0],
            erro_deletar='Ocorreu um erro ao processar a exclusão da sua conta.'
        ), 500


@auth_bp.route('/api/auth/check-email', methods=['GET'])
def check_email():
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'exists': False, 'valid': False, 'mensagem': 'E-mail vazio.'})
    if '@' not in email:
        return jsonify({'exists': False, 'valid': False, 'mensagem': 'E-mail inválido.'})
    
    try:
        usuarios = auth_service.listar_usuarios()
        exists = any((u.get('email') or '').strip().lower() == email for u in usuarios)
        return jsonify({
            'exists': exists,
            'valid': True,
            'mensagem': 'Este e-mail já está em uso.' if exists else 'E-mail disponível.'
        })
    except Exception as e:
        return jsonify({'exists': False, 'valid': False, 'mensagem': 'Erro ao verificar e-mail.'}), 500


@auth_bp.route('/api/auth/check-username', methods=['GET'])
def check_username():
    username = request.args.get('username', '').strip().lower()
    if not username:
        return jsonify({'exists': False, 'valid': False, 'mensagem': 'Nome de usuário vazio.'})
    if len(username) < 3:
        return jsonify({'exists': False, 'valid': False, 'mensagem': 'O nome de usuário deve ter ao menos 3 caracteres.'})
    
    try:
        usuarios = auth_service.listar_usuarios()
        exists = any((u.get('username') or '').strip().lower() == username for u in usuarios)
        return jsonify({
            'exists': exists,
            'valid': True,
            'mensagem': 'Este nome de usuário já está em uso. Por favor, escolha outro.' if exists else 'Nome de usuário disponível.'
        })
    except Exception as e:
        return jsonify({'exists': False, 'valid': False, 'mensagem': 'Erro ao verificar usuário.'}), 500

