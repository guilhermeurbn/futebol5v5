"""
Rotas de Autenticação
- Login, logout, cadastro, perfil e alteração de senha
"""
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, flash
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
    user_id = session.get('user_id')
    u = auth_service.obter_por_id(user_id) if user_id else {}
    return {
        'id': user_id,
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(user_id),
        'foto_url': (u.get('foto_url') if isinstance(u, dict) else None) or session.get('foto_url')
    }


def _is_admin():
    return session.get('role') in ['admin']


def _is_juiz():
    return session.get('role') == 'juiz'


def _usuario_sem_email(user_id):
    if not user_id:
        return False
    u = auth_service.obter_por_id(user_id)
    if not u:
        return False
    email = (u.get('email') or '').strip()
    return not email or '@' not in email


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login_page'))
        if session.get('senha_temporaria_ativa') and request.endpoint not in {
            'auth.perfil_page',
            'auth.perfil_alterar_senha',
            'auth.logout',
        }:
            return redirect(url_for('auth.perfil_page'))
        if _usuario_sem_email(user_id) and request.endpoint not in {
            'auth.completar_email_page',
            'auth.completar_email_submit',
            'auth.logout',
        }:
            return redirect(url_for('auth.completar_email_page'))
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
    votacoes_data = load_json_data("votacoes_partidas", [])
    if isinstance(votacoes_data, dict):
        votacoes = votacoes_data.get("partidas", [])
    elif isinstance(votacoes_data, list):
        votacoes = votacoes_data
    else:
        votacoes = []

    notas_por_partida = {}
    total_nota = 0.0
    qtd_votos = 0
    nome_norm = (jogador.nome or "").strip().lower()
    
    for partida in votacoes:
        if not isinstance(partida, dict):
            continue
        if partida.get("status") in ["encerrada", "finalizada"]:
            ranking = partida.get("ranking") or {}
            ranking_jogadores = ranking.get("ranking_jogadores") or []
            for r in ranking_jogadores:
                r_nome = (r.get("jogador_nome") or "").strip().lower()
                if r_nome == nome_norm:
                    nota_media = float(r.get("nota_media", 0) or 0)
                    partida_id = partida.get("id")
                    notas_por_partida[partida_id] = nota_media
                    if nota_media > 0:
                        total_nota += nota_media
                        qtd_votos += 1
                    break
                    
    if qtd_votos > 0:
        nota_geral = round(total_nota / qtd_votos, 2)
    else:
        try:
            from services.votacao_service import VotacaoService
            vs = VotacaoService()
            ranking_geral = vs.obter_ranking_geral()
            nota_geral = 0.0
            for r in ranking_geral:
                if (r.get("jogador_nome") or "").strip().lower() == nome_norm:
                    nm = float(r.get("nota_media", 0) or 0)
                    if nm > 0:
                        nota_geral = round(nm, 2)
                        break
            if nota_geral <= 0:
                nota_geral = round(float(getattr(jogador, 'nivel', 7.0) or 7.0), 2)
        except Exception:
            nota_geral = round(float(getattr(jogador, 'nivel', 7.0) or 7.0), 2)

    stats_jogador["nota_media"] = nota_geral
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
        if session.get('role') in ['admin']:
            return redirect(url_for('jogador.index'))
        return redirect(url_for('auth.perfil_page'))
    
    sucesso = request.args.get('sucesso')
    erro = request.args.get('erro')
    # Se a pessoa não está logada, vê a apresentação primeiro na tela de login
    # Se houver aviso de erro ou sucesso (tentativa recente), foca direto no formulário
    show_onboarding = not bool(erro or sucesso)
    if request.args.get('onboarding') == '1' or request.args.get('show_onboarding') == '1':
        show_onboarding = True
    return render_template('login.html', sucesso=sucesso, erro=erro, show_onboarding=show_onboarding)


@auth_bp.route('/login', methods=['POST'])
def login_submit():
    """Handler para submit de login"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    is_app_mode = (
        request.headers.get('X-Capacitor-Platform') or
        'Capacitor' in request.headers.get('User-Agent', '') or
        'NaTraveApp' in request.headers.get('User-Agent', '') or
        request.args.get('mode') == 'app'
    )
    remember_me = (request.form.get('remember_me') in {'1', 'on', 'true', 'yes'}) or bool(is_app_mode)
    
    try:
        usuario = auth_service.autenticar(username, password)
        if not usuario:
            return render_template('login.html', erro='Usuario ou senha invalidos', show_onboarding=False), 401

        session.permanent = True if (remember_me or is_app_mode) else False
        if remember_me or is_app_mode:
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
        if _usuario_sem_email(usuario['id']):
            return redirect(url_for('auth.completar_email_page'))
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        if session.get('role') in ['admin']:
            return redirect(url_for('jogador.index'))
        return redirect(url_for('auth.perfil_page'))
    except ValueError as e:
        return render_template('login.html', erro=str(e)), 400
    except Exception as e:
        return render_template('login.html', erro='Erro ao autenticar usuario'), 500


def _extrair_dados_apple_post():
    """Extrai email, nome e social_id do payload da Apple ID (POST form, JSON ou GET query args)"""
    import base64
    import json

    data = request.get_json(silent=True) or request.form
    id_token = data.get('id_token') or request.args.get('id_token') or ''
    user_json_str = data.get('user') or request.args.get('user') or ''
    
    email = (data.get('email') or request.args.get('email') or '').strip().lower()
    social_id = (data.get('social_id') or request.args.get('social_id') or '').strip()
    nome = (data.get('nome') or request.args.get('nome') or '').strip() or 'Atleta Apple'

    if id_token and '.' in id_token:
        try:
            parts = id_token.split('.')
            if len(parts) >= 2:
                payload_b64 = parts[1]
                payload_b64 += '=' * (-len(payload_b64) % 4)
                decoded = base64.urlsafe_b64decode(payload_b64)
                claims = json.loads(decoded)
                if not email:
                    email = (claims.get('email') or '').strip().lower()
                if not social_id:
                    social_id = claims.get('sub', '')
        except Exception as e:
            logger.warning(f"Erro ao decodificar id_token JWT da Apple: {e}")

    if user_json_str and isinstance(user_json_str, str):
        try:
            user_data = json.loads(user_json_str)
            if isinstance(user_data, dict):
                user_email = (user_data.get('email') or '').strip().lower()
                if user_email and not email:
                    email = user_email
                name_obj = user_data.get('name') or {}
                if isinstance(name_obj, dict):
                    first = name_obj.get('firstName') or ''
                    last = name_obj.get('lastName') or ''
                    full_name = f"{first} {last}".strip()
                    if full_name and nome == 'Atleta Apple':
                        nome = full_name
        except Exception:
            pass

    return email, nome, social_id


@auth_bp.route('/social-login', methods=['GET', 'POST'])
def social_login():
    """Handler para login/cadastro via Google e Apple"""
    has_apple_params = (
        'id_token' in request.form or 
        'id_token' in request.args or 
        'code' in request.args or
        (request.is_json and 'id_token' in (request.get_json(silent=True) or {}))
    )

    if request.method == 'GET' and not has_apple_params:
        return redirect(url_for('auth.login_page'))

    data = request.get_json(silent=True) or request.form
    provider = (data.get('provider') or request.args.get('provider') or ('apple' if has_apple_params else 'google')).strip().lower()

    email = (data.get('email') or request.args.get('email') or '').strip().lower()
    nome = (data.get('nome') or request.args.get('nome') or '').strip()
    social_id = (data.get('social_id') or request.args.get('social_id') or '').strip()

    # Se parâmetros id_token da Apple estiverem presentes:
    if has_apple_params:
        apple_email, apple_nome, apple_id = _extrair_dados_apple_post()
        if apple_email:
            email = apple_email
        if apple_nome and apple_nome != 'Atleta Apple':
            nome = apple_nome
        if apple_id:
            social_id = apple_id

    # 1. Tenta buscar usuário por social_id (apple_id / google_id) OU por e-mail
    usuarios = auth_service._carregar()
    usuario = None

    if social_id:
        usuario = next(
            (
                u for u in usuarios
                if (
                    (u.get('apple_id') or '') == social_id or
                    (u.get('google_id') or '') == social_id or
                    (u.get(f'{provider}_id') or '') == social_id
                )
            ),
            None
        )

    if not usuario and email:
        email_clean = email.strip().lower()
        usuario = next(
            (
                u for u in usuarios
                if (
                    (u.get('email') or '').strip().lower() == email_clean or
                    (u.get('google_email') or '').strip().lower() == email_clean or
                    (u.get('apple_email') or '').strip().lower() == email_clean
                )
            ),
            None
        )

    if usuario:
        # Vincula a conta social se ainda não estiver vinculada
        try:
            auth_service.vincular_conta_social(user_id=usuario['id'], provider=provider, email=email or usuario.get('email', ''), social_id=social_id)
        except Exception:
            pass

        # Usuário existe! Efetua login imediatamente
        session.permanent = True
        session['remember_me'] = True
        session['user_id'] = usuario['id']
        session['username'] = usuario['username']
        session['nome'] = usuario['nome']
        session['role'] = usuario.get('role', 'usuario')
        session.modified = True

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({
                'success': True,
                'status': 'logged_in',
                'redirect_url': url_for('auth.perfil_page')
            })
        return redirect(url_for('auth.perfil_page'))

    # Se o usuário NÃO existe e o e-mail não veio (ex: conta não registrada e sem e-mail)
    if not email or '@' not in email:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'error': 'E-mail não fornecido pela conta Apple. Tente entrar novamente.'}), 400
        return render_template('login.html', erro='E-mail não fornecido pela conta Apple. Tente entrar novamente.'), 400

    # 2. Usuário novo: solicita a escolha do nome de usuário (username)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    if is_ajax:
        return jsonify({
            'success': True,
            'status': 'need_username',
            'email': email,
            'nome': nome or email.split('@')[0],
            'social_id': social_id,
            'provider': provider
        })
    return render_template('login.html', social_email=email, social_nome=nome or email.split('@')[0], social_provider=provider, social_id=social_id)


@auth_bp.route('/checar-username', methods=['GET'])
def checar_username():
    """Verifica instantaneamente a disponibilidade de um nome de usuário (@username)"""
    username = request.args.get('username', '').strip().lower()
    if not username:
        return jsonify({'available': False, 'message': 'Digite um nome de usuário'}), 400
    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Mínimo de 3 caracteres'}), 400
    if len(username) > 30:
        return jsonify({'available': False, 'message': 'Máximo de 30 caracteres'}), 400
    import re
    if not re.match(r'^[a-zA-Z0-9_.]+$', username):
        return jsonify({'available': False, 'message': 'Use apenas letras, números, _ ou .'}), 400

    usuarios = auth_service._carregar()
    existe = any((u.get('username') or '').strip().lower() == username for u in usuarios)
    if existe:
        return jsonify({'available': False, 'message': '✗ Este username já está em uso. Escolha outro.'})
    return jsonify({'available': True, 'message': f'✓ @{username} está disponível!'})


@auth_bp.route('/checar-email', methods=['GET'])
def checar_email():
    """Verifica instantaneamente a disponibilidade e validade de um e-mail no cadastro"""
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'available': False, 'message': 'Digite um e-mail'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'available': False, 'message': 'E-mail em formato inválido'}), 400
    
    usuarios = auth_service._carregar()
    existe = any((u.get('email') or '').strip().lower() == email for u in usuarios)
    if existe:
        return jsonify({'available': False, 'message': '✗ Este e-mail já está cadastrado em outra conta.'})
    return jsonify({'available': True, 'message': '✓ E-mail disponível!'})


@auth_bp.route('/sugerir-username', methods=['GET'])
def sugerir_username():
    """Gera uma sugestão limpa e disponível de username a partir do nome do usuário"""
    nome = request.args.get('nome', '').strip()
    if not nome:
        return jsonify({'suggestion': '', 'available': False, 'message': 'Nome não informado'}), 400

    import unicodedata
    import re

    # Normalizar removendo acentos e caracteres especiais
    nome_nfkd = unicodedata.normalize('NFKD', nome)
    slug = "".join([c for c in nome_nfkd if not unicodedata.combining(c)])
    slug = slug.lower().strip()
    partes = [re.sub(r'[^a-z0-9]', '', p) for p in slug.split() if p]

    if not partes:
        base_user = "jogador"
    elif len(partes) == 1:
        base_user = partes[0]
    else:
        base_user = f"{partes[0]}_{partes[-1]}"

    if len(base_user) < 3:
        base_user = f"{base_user}_fc"

    usuarios = auth_service._carregar()
    existing_usernames = {(u.get('username') or '').strip().lower() for u in usuarios if u.get('username')}

    candidate = base_user
    counter = 1
    while candidate in existing_usernames and counter < 100:
        candidate = f"{base_user}{counter}"
        counter += 1

    available = candidate not in existing_usernames
    return jsonify({
        'suggestion': candidate,
        'available': available,
        'message': f"✓ Sugestão livre: @{candidate}" if available else "✗ Username em uso"
    })


@auth_bp.route('/vincular-social', methods=['POST'])
def vincular_social():
    """Endpoint para vincular conta Google ou Apple ao perfil do usuário logado"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Você precisa estar logado'}), 401
    
    data = request.get_json(silent=True) or request.form
    provider = (data.get('provider') or 'google').strip().lower()
    email = data.get('email', '').strip().lower()
    social_id = data.get('social_id', '').strip()

    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'E-mail social inválido'}), 400

    try:
        usuario = auth_service.vincular_conta_social(user_id=user_id, provider=provider, email=email, social_id=social_id)
        return jsonify({
            'success': True,
            'message': f'Conta {provider.title()} ({email}) vinculada com sucesso!',
            'user': {
                'google_email': usuario.get('google_email'),
                'apple_email': usuario.get('apple_email')
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao vincular conta social'}), 500


@auth_bp.route('/desvincular-social', methods=['POST'])
def desvincular_social():
    """Endpoint para desvincular conta Google ou Apple do perfil do usuário logado"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Você precisa estar logado'}), 401
    
    data = request.get_json(silent=True) or request.form
    provider = (data.get('provider') or 'google').strip().lower()

    try:
        usuario = auth_service.desvincular_conta_social(user_id=user_id, provider=provider)
        return jsonify({
            'success': True,
            'message': f'Conta {provider.title()} desvinculada com sucesso!'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao desvincular conta social'}), 500


@auth_bp.route('/social-complete-username', methods=['POST'])
def social_complete_username():
    """Handler para finalizar cadastro social com o username escolhido"""
    data = request.get_json(silent=True) or request.form
    provider = (data.get('provider') or 'google').strip().lower()
    email = data.get('email', '').strip().lower()
    nome = data.get('nome', '').strip()
    username = data.get('username', '').strip()
    posicao = (data.get('posicao') or 'linha').strip().lower()
    posicao = 'goleiro' if posicao == 'goleiro' else 'linha'
    social_id = data.get('social_id', '').strip()

    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'E-mail inválido'}), 400
    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': 'Nome de usuário deve ter ao menos 3 caracteres'}), 400
    if not nome:
        nome = username

    try:
        import uuid
        random_pwd = str(uuid.uuid4())
        usuario = auth_service.criar_usuario(
            email=email,
            username=username,
            nome=nome,
            password=random_pwd,
            role='usuario'
        )
        try:
            auth_service.vincular_conta_social(user_id=usuario['id'], provider=provider, email=email, social_id=social_id)
        except Exception:
            pass

        try:
            jogador_service.criar(
                nome=nome,
                nivel=5.5,
                tipo='avulso',
                posicao=posicao,
                owner_user_id=usuario.get('id')
            )
        except Exception as exc:
            logger.warning(f"Erro ao criar perfil de jogador automático: {exc}")

        session.permanent = True
        session['remember_me'] = True
        session['user_id'] = usuario['id']
        session['username'] = usuario['username']
        session['nome'] = usuario['nome']
        session['role'] = usuario.get('role', 'usuario')
        session.modified = True

        return jsonify({
            'success': True,
            'status': 'logged_in',
            'redirect_url': url_for('auth.perfil_page')
        })
    except ValueError as val_err:
        return jsonify({'success': False, 'error': str(val_err)}), 400
    except Exception as err:
        logger.error(f"Erro ao concluir cadastro social: {err}")
        return jsonify({'success': False, 'error': 'Erro ao criar conta social'}), 500


@auth_bp.route('/completar-email', methods=['GET'])
def completar_email_page():
    """Página para preenchimento obrigatório de e-mail"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login_page'))
    if not _usuario_sem_email(user_id):
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        if session.get('role') in ['admin']:
            return redirect(url_for('jogador_crud.index'))
        return redirect(url_for('auth.perfil_page'))
    return render_template('completar_email.html')


@auth_bp.route('/completar-email', methods=['POST'])
def completar_email_submit():
    """Handler para submissão do e-mail obrigatório"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login_page'))

    email = request.form.get('email', '').strip().lower()
    if not email or '@' not in email:
        return render_template('completar_email.html', erro='Por favor, informe um e-mail válido com @.'), 400

    try:
        auth_service.atualizar_email(user_id=user_id, email=email)
        try:
            email_service.notify_admin_novo_cadastro(
                nome=session.get('nome', 'Jogador'),
                username=session.get('username', 'usuario'),
                email=email
            )
        except Exception:
            pass
        flash('E-mail cadastrado com sucesso!', 'sucesso')
        if session.get('role') == 'juiz':
            return redirect(url_for('juiz.jogar_page'))
        if session.get('role') in ['admin']:
            return redirect(url_for('jogador_crud.index'))
        return redirect(url_for('auth.perfil_page'))
    except ValueError as exc:
        msg = str(exc)
        if msg == "Email ja existe":
            msg = "Este e-mail já está cadastrado em outra conta. Informe outro e-mail."
        return render_template('completar_email.html', erro=msg), 400
    except Exception as exc:
        logger.error(f"Erro ao salvar e-mail obrigatorio para usuario {user_id}: {exc}")
        return render_template('completar_email.html', erro='Erro ao salvar e-mail. Tente novamente.'), 500
@auth_bp.route('/privacidade', methods=['GET'])
def privacidade_page():
    """Página pública de Política de Privacidade (Exigência Apple App Store)"""
    return render_template('privacidade.html')



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
    is_json = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json'
    data = request.get_json(silent=True) if request.is_json else request.form

    nome = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    senha = data.get('password') or ''
    confirmar = data.get('confirmar_password') or senha
    nivel = data.get('nivel', '5.5')
    tipo = data.get('tipo', 'avulso')
    posicao = data.get('posicao', 'linha')

    if not email or '@' not in email:
        if is_json:
            return jsonify({'success': False, 'error': 'Informe um e-mail válido'}), 400
        return render_template('cadastro.html', erro='Informe um email valido'), 400
    if senha != confirmar:
        if is_json:
            return jsonify({'success': False, 'error': 'A confirmação de senha não confere'}), 400
        return render_template('cadastro.html', erro='A confirmacao de senha nao confere'), 400

    if not nome or len(nome) < 2:
        if is_json:
            return jsonify({'success': False, 'error': 'Nome deve ter ao menos 2 caracteres'}), 400
        return render_template('cadastro.html', erro='Nome deve ter ao menos 2 caracteres'), 400
    nome_partes = [p for p in nome.split() if p]
    if len(nome_partes) < 2:
        if is_json:
            return jsonify({'success': False, 'error': 'Por favor, digite seu nome e sobrenome.'}), 400
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

        if is_json or request.args.get('auto_login') == '1':
            session.permanent = True
            session['remember_me'] = True
            session['user_id'] = usuario['id']
            session['username'] = usuario['username']
            session['nome'] = usuario['nome']
            session['role'] = usuario.get('role', 'usuario')
            session.modified = True

            return jsonify({
                'success': True,
                'status': 'logged_in',
                'message': 'Cadastro realizado com sucesso!',
                'redirect_url': url_for('auth.perfil_page')
            })

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
        if is_json:
            return jsonify({'success': False, 'error': msg}), 400
        return render_template('cadastro.html', erro=msg), 400
    except Exception as e:
        if is_json:
            return jsonify({'success': False, 'error': 'Erro ao criar conta'}), 500
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
    mensagem = 'Se o email existir na base, enviamos um link de redefinição de senha.'
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if not email or '@' not in email:
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'Informe um e-mail válido'}), 400
        return render_template('recuperar_senha.html', erro='Informe um email valido'), 400

    usuario = auth_service.obter_por_email(email)
    if not usuario:
        if is_ajax:
            return jsonify({'ok': True, 'sucesso': mensagem})
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

    if is_ajax:
        return jsonify({'ok': True, 'sucesso': mensagem})
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
        try:
            email_service.notify_admin_solicitacao_senha(
                nome=usuario.get('nome', 'Jogador'),
                username=usuario.get('username', ''),
                email=usuario.get('email', ''),
                tipo_acao="Senha Redefinida com Sucesso"
            )
        except Exception:
            pass
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

def _obter_variacao_rodada(jogador) -> dict:
    """Calcula a variação do nível do jogador na última rodada com base no histórico."""
    if not jogador:
        return {'variacao': 0.0, 'direcao': 'neutro', 'texto': ''}
        
    hist = getattr(jogador, 'historico_nivel', None) or []
    if not isinstance(hist, list) and isinstance(jogador, dict):
        hist = jogador.get('historico_nivel', []) or []
        
    if hist:
        ultimo = hist[-1]
        ant = float(ultimo.get('nivel_anterior', 0) or 0)
        nov = float(ultimo.get('nivel_novo', 0) or 0)
        
        if nov == 0:
            nov = float(getattr(jogador, 'nivel', 0) or (jogador.get('nivel', 0) if isinstance(jogador, dict) else 0))
            
        diff = round(nov - ant, 2)
        if diff > 0:
            formatted_diff = f"+{diff:.2f}".rstrip('0').rstrip('.')
            if formatted_diff == "+0":
                formatted_diff = "+0.0"
            return {'variacao': diff, 'direcao': 'subiu', 'texto': formatted_diff}
        elif diff < 0:
            formatted_diff = f"{diff:.2f}".rstrip('0').rstrip('.')
            if formatted_diff == "-0":
                formatted_diff = "-0.0"
            return {'variacao': diff, 'direcao': 'desceu', 'texto': formatted_diff}
        else:
            return {'variacao': 0.0, 'direcao': 'neutro', 'texto': '0.0'}

    return {'variacao': 0.0, 'direcao': 'sem_historico', 'texto': ''}


@auth_bp.route('/perfil', methods=['GET'])
@login_required
def perfil_page():
    """Página de perfil do usuário logado"""
    jogador_proprio = None
    stats_jogador = None
    partida_juiz_em_andamento = None
    
    try:
        current_uid = session.get('user_id')
        current_nome = session.get('nome')
        current_uname = session.get('username')

        meus = jogador_service.listar_por_usuario(current_uid) if current_uid else []
        if not meus and current_uid:
            j_by_id = jogador_service.obter_por_id(current_uid)
            j_by_nome = jogador_service.obter_por_nome(current_nome) if (current_nome and not j_by_id) else None
            j_by_uname = jogador_service.obter_por_nome(current_uname) if (current_uname and not j_by_id and not j_by_nome) else None
            j_found = j_by_id or j_by_nome or j_by_uname
            if j_found:
                meus = [j_found]

        jogador_proprio = meus[0] if meus else None
        
        # Obter estatísticas do jogador
        if jogador_proprio:
            stats_jogador = jogador_stats_service.obter_stats_jogador(
                jogador_proprio.nome,
                jogador_id=jogador_proprio.id,
                user_id=jogador_proprio.owner_user_id or current_uid
            )
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
    
    presenca_resumo = None
    presenca_usuario = None
    try:
        from services.presenca_service import PresencaService
        ps = PresencaService()
        presenca_resumo = ps.obter_resumo()
        if session.get('user_id'):
            presenca_usuario = ps.obter_resposta(session.get('user_id'))
    except Exception:
        pass

    todos_jogadores_duelo = []
    try:
        todos_jogadores_duelo = jogador_service.listar_para_dict() or []
    except Exception:
        pass

    mensagens_nao_lidas = []
    mensagens_lidas = []
    tem_mensagens_nao_lidas = False
    try:
        from services.mensagem_service import MensagemService
        msg_svc = MensagemService()
        current_uid = session.get('user_id')
        tem_mensagens_nao_lidas = msg_svc.tem_mensagens_nao_lidas(current_uid)
        mensagens_nao_lidas, mensagens_lidas = msg_svc.obter_mensagens_separadas(current_uid)
    except Exception:
        pass

    aba_ativa = request.args.get('tab', '').strip().lower()
    if aba_ativa not in ['mensagem', 'estatisticas', 'partidas', 'duelo', 'mais']:
        aba_ativa = 'partidas' if jogador_proprio else 'mensagem'

    variacao_rodada = _obter_variacao_rodada(jogador_proprio)

    return render_template(
        'perfil.html',
        usuario=_usuario_logado(),
        jogador_proprio=jogador_proprio,
        stats_jogador=stats_jogador,
        partida_juiz_em_andamento=partida_juiz_em_andamento,
        presenca_resumo=presenca_resumo,
        presenca_usuario=presenca_usuario,
        todos_jogadores_duelo=todos_jogadores_duelo,
        aba_ativa=aba_ativa,
        mensagens_diretas=mensagens_nao_lidas,
        mensagens_nao_lidas=mensagens_nao_lidas,
        mensagens_lidas=mensagens_lidas,
        tem_mensagens_nao_lidas=tem_mensagens_nao_lidas,
        variacao_rodada=variacao_rodada,
        is_self=True
    )


def _obter_perfil_publico_dados(identifier):
    """Auxiliar para carregar o modelo de jogador e usuario do perfil publico"""
    if not identifier:
        return None, None
    identifier_str = str(identifier).strip()
    identifier_clean = identifier_str.lower().removeprefix('perfil_').removeprefix('@')
    jogador = None
    owner_user = None

    # 1. Tentar buscar jogador por ID (inteiro ou string)
    try:
        if identifier_clean.isdigit():
            jogador = jogador_service.obter_por_id(int(identifier_clean))
        if not jogador:
            jogador = jogador_service.obter_por_id(identifier_str)
    except Exception:
        jogador = None

    # Se achou o jogador, tentar achar o usuario dono por id ou nome
    if jogador and not owner_user:
        u_id = getattr(jogador, 'user_id', None) or getattr(jogador, 'owner_user_id', None)
        if u_id:
            try:
                owner_user = auth_service.obter_por_id(u_id)
            except Exception:
                pass
        if not owner_user and jogador.nome:
            try:
                owner_user = auth_service.obter_por_nome(jogador.nome) or auth_service.obter_por_username(jogador.nome)
            except Exception:
                pass

    # 2. Tentar buscar usuario por username ou id
    if not owner_user:
        try:
            owner_user = auth_service.obter_por_username(identifier_clean)
            if not owner_user and identifier_clean.isdigit():
                owner_user = auth_service.obter_por_id(identifier_clean)
        except Exception:
            pass
        if owner_user and not jogador:
            meus = jogador_service.listar_por_usuario(owner_user.get('id'))
            jogador = meus[0] if meus else None

    # 3. Tentar por nome de jogador
    if not jogador:
        try:
            todos = jogador_service.listar_todos()
            for j in todos:
                j_nome = (j.nome or "").strip().lower()
                j_nome_slug = j_nome.replace(" ", "_")
                if j_nome == identifier_clean or j_nome_slug == identifier_clean:
                    jogador = j
                    u_id = getattr(j, 'user_id', None) or getattr(j, 'owner_user_id', None)
                    if u_id and not owner_user:
                        owner_user = auth_service.obter_por_id(u_id)
                    if not owner_user:
                        owner_user = auth_service.obter_por_nome(j.nome) or auth_service.obter_por_username(j.nome)
                    break
        except Exception:
            pass

    return jogador, owner_user


@auth_bp.route('/jogadores/<jogador_id>/perfil', methods=['GET'])
@auth_bp.route('/perfil_<jogador_id>', methods=['GET'])
@auth_bp.route('/perfil/<jogador_id>', methods=['GET'])
@login_required
def perfil_jogador_publico(jogador_id):
    """Visualiza perfil público de outro jogador de forma unificada e inteligente"""
    try:
        jogador, owner_user = _obter_perfil_publico_dados(jogador_id)
        if not jogador and not owner_user:
            return redirect(url_for('jogador.index'))

        current_user = _usuario_logado()
        current_user_id = session.get('user_id')

        target_user_id = owner_user.get('id') if owner_user else (jogador.owner_user_id if jogador else None)
        is_self = bool(current_user_id and target_user_id and str(current_user_id) == str(target_user_id))

        stats_jogador = None
        if jogador:
            try:
                stats_jogador = jogador_stats_service.obter_stats_jogador(
                    jogador.nome,
                    jogador_id=jogador.id,
                    user_id=target_user_id or jogador.owner_user_id
                )
                stats_jogador.setdefault('efficiency', {})
                stats_jogador.setdefault('discipline', {})
                stats_jogador.setdefault('ultimos_resultados', {'forma': [], 'pontos': 0, 'partidas': []})
                stats_jogador.setdefault('mini_dashboard', {'kpis': {}, 'series_ultimos_5': []})
                stats_jogador.setdefault('planilha_metricas', [])
                
                # Calcular e injetar notas e atributos determinísticos
                _obter_notas_e_atributos_jogador(jogador, stats_jogador)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao carregar estatísticas do perfil público: {str(e)}")

        presenca_resumo = None
        presenca_usuario = None
        try:
            from services.presenca_service import PresencaService
            ps = PresencaService()
            presenca_resumo = ps.obter_resumo()
            if session.get('user_id'):
                presenca_usuario = ps.obter_resposta(session.get('user_id'))
        except Exception:
            pass

        todos_jogadores_duelo = []
        try:
            todos_jogadores_duelo = jogador_service.listar_para_dict() or []
        except Exception:
            pass

        aba_ativa = request.args.get('tab', '').strip().lower()
        if aba_ativa not in ['mensagem', 'estatisticas', 'partidas', 'duelo', 'mais']:
            aba_ativa = 'partidas'

        mensagens_nao_lidas = []
        mensagens_lidas = []
        tem_mensagens_nao_lidas = False
        try:
            from services.mensagem_service import MensagemService
            msg_svc = MensagemService()
            tem_mensagens_nao_lidas = msg_svc.tem_mensagens_nao_lidas(current_user_id)

            if is_self:
                mensagens_nao_lidas, mensagens_lidas = msg_svc.obter_mensagens_separadas(current_user_id)
            elif target_user_id:
                mensagens_nao_lidas, mensagens_lidas = msg_svc.obter_mensagens_separadas(current_user_id)
        except Exception:
            pass

        variacao_rodada = _obter_variacao_rodada(jogador)

        return render_template(
            'perfil.html',
            jogador_proprio=jogador,
            stats_jogador=stats_jogador,
            usuario=current_user,
            target_user=owner_user,
            is_self=is_self,
            presenca_resumo=presenca_resumo,
            presenca_usuario=presenca_usuario,
            todos_jogadores_duelo=todos_jogadores_duelo,
            aba_ativa=aba_ativa,
            mensagens_diretas=mensagens_nao_lidas,
            mensagens_nao_lidas=mensagens_nao_lidas,
            mensagens_lidas=mensagens_lidas,
            tem_mensagens_nao_lidas=tem_mensagens_nao_lidas,
            variacao_rodada=variacao_rodada
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao carregar perfil público: {str(e)}")
        return redirect(url_for('jogador.index'))


@auth_bp.route('/perfil/enviar-mensagem', methods=['POST'])
@login_required
def perfil_enviar_mensagem():
    """Envia uma mensagem direta para um jogador através da aba de mensagens do perfil"""
    try:
        current_user = _usuario_logado()
        current_user_id = str(session.get('user_id'))
        remetente_nome = (current_user.get('nome') if current_user else None) or (current_user.get('username') if current_user else None) or "Atleta"

        destinatario_raw = request.form.get('destinatario_id', '').strip()
        destinatario_nome = request.form.get('destinatario_nome', '').strip()
        conteudo = request.form.get('conteudo', '').strip()

        if not destinatario_raw or not conteudo:
            flash('Por favor, digite uma mensagem válida.', 'erro')
            return redirect(request.referrer or url_for('auth.perfil_page'))

        # Normalizar destinatario_id para o user_id do jogador
        destinatario_id = destinatario_raw
        if destinatario_raw.isdigit():
            try:
                j = jogador_service.obter_por_id(int(destinatario_raw))
                if j and j.owner_user_id:
                    destinatario_id = str(j.owner_user_id)
                if j and not destinatario_nome:
                    destinatario_nome = j.nome
            except Exception:
                pass

        if not destinatario_nome:
            try:
                u = auth_service.obter_por_id(destinatario_id)
                if u:
                    destinatario_nome = u.get('nome') or u.get('username') or "Atleta"
            except Exception:
                destinatario_nome = "Atleta"

        from services.mensagem_service import MensagemService
        msg_svc = MensagemService()
        msg_svc.enviar_mensagem(
            remetente_id=current_user_id,
            remetente_nome=remetente_nome,
            destinatario_id=destinatario_id,
            destinatario_nome=destinatario_nome,
            conteudo=conteudo
        )

        # Ao responder a mensagem, marca automaticamente todas as mensagens pendentes recebidas deste atleta como lidas/arquivadas
        try:
            msg_svc.marcar_como_lidas(destinatario_id=current_user_id, remetente_id=destinatario_id)
        except Exception as exc:
            logger.warning(f"Erro ao marcar mensagens como lidas ao responder: {exc}")

        flash(f'Mensagem enviada para {destinatario_nome} com sucesso!', 'sucesso')
        
        # Redirecionar mantendo a aba mensagem ativa
        ref = request.referrer or url_for('auth.perfil_page')
        if 'tab=' not in ref:
            sep = '&' if '?' in ref else '?'
            ref = f"{ref}{sep}tab=mensagem"
        return redirect(ref)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao enviar mensagem direta no perfil: {str(e)}")
        flash('Erro ao enviar mensagem. Tente novamente.', 'erro')
        return redirect(request.referrer or url_for('auth.perfil_page'))


@auth_bp.route('/perfil/marcar-lida/<int:msg_id>', methods=['POST'])
@login_required
def perfil_marcar_mensagem_lida(msg_id):
    """Marca uma mensagem específica como lida e a move para a área de histórico de lidas"""
    try:
        current_user_id = session.get('user_id')
        from services.mensagem_service import MensagemService
        msg_svc = MensagemService()
        msg_svc.marcar_mensagem_individual_como_lida(msg_id, current_user_id)
        flash('Mensagem movida para as lidas!', 'sucesso')
    except Exception as e:
        logger.error(f"Erro ao marcar mensagem como lida: {str(e)}")
    
    ref = request.referrer or url_for('auth.perfil_page')
    if 'tab=' not in ref:
        sep = '&' if '?' in ref else '?'
        ref = f"{ref}{sep}tab=mensagem"
    return redirect(ref)


@auth_bp.route('/editar-perfil', methods=['GET'])
@login_required
def editar_perfil_page():
    """Página dedicada de edição de perfil e dados pessoais"""
    return render_template(
        'editar_perfil.html',
        usuario=_usuario_logado()
    )


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
            'editar_perfil.html',
            usuario=_usuario_logado(),
            erro_senha='A confirmação de senha não confere'
        ), 400

    try:
        auth_service.alterar_senha(
            user_id=session.get('user_id'),
            senha_atual=senha_atual,
            nova_senha=nova_senha,
            senha_temporaria=senha_temporaria,
        )
        try:
            email_service.notify_admin_solicitacao_senha(
                nome=session.get('nome', 'Jogador'),
                username=session.get('username', ''),
                email=session.get('email', ''),
                tipo_acao="Senha Alterada no Perfil"
            )
        except Exception:
            pass
        session['senha_temporaria_ativa'] = False
        session.modified = True
        return render_template(
            'editar_perfil.html',
            usuario=_usuario_logado(),
            sucesso_senha='Senha alterada com sucesso!'
        )
    except ValueError as e:
        return render_template(
            'editar_perfil.html',
            usuario=_usuario_logado(),
            erro_senha=str(e)
        ), 400
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao alterar senha: {str(e)}")
        return render_template(
            'editar_perfil.html',
            usuario=_usuario_logado(),
            erro_senha='Erro ao alterar senha'
        ), 500


@auth_bp.route('/perfil/editar', methods=['POST'])
@login_required
def perfil_editar_dados():
    """Edita e-mail, username, nome ou foto do usuário logado"""
    user_id = session.get('user_id')
    email = request.form.get('email')
    username = request.form.get('username')
    nome = request.form.get('nome')
    foto_file = request.files.get('foto')

    try:
        url_foto = None
        if foto_file and foto_file.filename:
            from services.upload_service import UploadService
            us = UploadService()
            u_atual = auth_service.obter_por_id(user_id) or {}
            url_foto = us.processar_foto_perfil(
                file_storage=foto_file,
                user_id=user_id,
                foto_antiga_url=u_atual.get('foto_url')
            )

        updated = auth_service.atualizar_perfil_usuario(
            user_id=user_id,
            email=email if email is not None and email.strip() else None,
            username=username if username is not None and username.strip() else None,
            nome=nome if nome is not None and nome.strip() else None,
            foto_url=url_foto if url_foto else None
        )
        if updated.get('username'):
            session['username'] = updated.get('username')
        if updated.get('nome'):
            session['nome'] = updated.get('nome')
        if updated.get('foto_url'):
            session['foto_url'] = updated.get('foto_url')
        session.modified = True

        return render_template(
            'editar_perfil.html',
            usuario=_usuario_logado(),
            sucesso_perfil='Dados do perfil atualizados com sucesso!'
        )
    except ValueError as e:
        return render_template(
            'editar_perfil.html',
            usuario=_usuario_logado(),
            erro_perfil=str(e)
        ), 400
    except Exception as e:
        from services.upload_service import UploadError
        if isinstance(e, UploadError):
            return render_template(
                'editar_perfil.html',
                usuario=_usuario_logado(),
                erro_perfil=str(e)
            ), 400
        logger.error(f"Erro ao editar perfil: {str(e)}")
        return render_template(
            'editar_perfil.html',
            usuario=_usuario_logado(),
            erro_perfil='Erro ao atualizar perfil'
        ), 500


@auth_bp.route('/perfil/foto/remover', methods=['POST'])
@login_required
def perfil_remover_foto():
    """Remove a foto de perfil do usuário e restaura as iniciais."""
    user_id = session.get('user_id')
    from services.upload_service import UploadService
    us = UploadService()
    u_atual = auth_service.obter_por_id(user_id) or {}
    foto_antiga = u_atual.get('foto_url')

    if foto_antiga:
        us.remover_foto(foto_antiga)
        auth_service.atualizar_perfil_usuario(user_id=user_id, foto_url="")
        session.pop('foto_url', None)
        session.modified = True

    return render_template(
        'editar_perfil.html',
        usuario=_usuario_logado(),
        sucesso_perfil='Foto removida com sucesso! O perfil voltou a exibir as iniciais.'
    )


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

        if user.get('role') in ['admin']:
            return render_template(
                'perfil.html',
                usuario=_usuario_logado(),
                jogador_proprio=(jogador_service.listar_por_usuario(user_id) or [None])[0],
                erro_deletar='Administradores não podem excluir sua própria conta.'
            ), 400

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


@auth_bp.route('/configuracoes')
def configuracoes_page():
    """Página dedicada de configurações, guia de funcionamento, termos de uso e privacidade."""
    return render_template('configuracoes.html', usuario=_usuario_logado())

