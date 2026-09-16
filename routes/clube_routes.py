"""
Módulo de Rotas de Gestão de Clubes (NaTrave 5v5 Multi-Clube)
Oferece endpoints para onboarding, verificação de nome único e gerenciamento de clubes.
"""

from typing import Dict, Any, Optional
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, g
from services.clube_service import ClubeService, ClubeSchema
from services.auth_service import AuthService

clube_bp = Blueprint('clube', __name__)


@clube_bp.route('/criar-clube', methods=['GET'])
def criar_clube_page():
    """Página de Onboarding para novos organizadores criarem um clube."""
    return render_template('criar_clube.html')


@clube_bp.route('/api/clube/buscar', methods=['GET'])
def api_buscar_clubes():
    """
    Endpoint para buscar clubes por nome ou código de identificação (ex: "001", "NaTrave").
    """
    from services.clube_service import normalizar_texto
    query = str(request.args.get('q', '')).strip()
    todos = ClubeService.obter_todos_clubes()

    if not query:
        return jsonify({'clubes': todos[:10]}), 200

    q_norm = normalizar_texto(query)
    q_code = query.lstrip('0')

    resultados = []
    for c in todos:
        nome_norm = normalizar_texto(c.get('nome', ''))
        cod_fmt = c.get('codigo_formatado', '')
        cod_clean = cod_fmt.lstrip('0')
        slug = c.get('slug', '').lower()

        if (q_norm in nome_norm) or (q_norm in slug) or (query == cod_fmt) or (q_code and q_code == cod_clean):
            resultados.append(c)

    return jsonify({'clubes': resultados}), 200


@clube_bp.route('/api/clube/validar-nome', methods=['POST'])
def api_validar_nome_clube():
    """
    Endpoint AJAX para verificar em tempo real se o nome de um clube já existe.
    Retorna se o nome é válido e disponível.
    """
    data: Dict[str, Any] = request.get_json() or {}
    nome = str(data.get('nome', '')).strip()

    if not nome or len(nome) < 2:
        return jsonify({
            'valido': False,
            'mensagem': 'O nome do clube deve ter pelo menos 2 caracteres.'
        }), 400

    existe = ClubeService.verificar_nome_existente(nome)
    if existe:
        return jsonify({
            'valido': False,
            'disponivel': False,
            'mensagem': f"Já existe um clube cadastrado com o nome '{nome}'."
        }), 200

    return jsonify({
        'valido': True,
        'disponivel': True,
        'mensagem': 'Nome de clube disponível!'
    }), 200


@clube_bp.route('/api/clube/criar', methods=['POST'])
def api_criar_clube():
    """
    Endpoint para criar um novo clube com ID sequencial (001, 002...) e nome único.
    """
    data: Dict[str, Any] = request.get_json() or {}
    nome = str(data.get('nome', '')).strip()
    cor_tema = str(data.get('cor_tema', 'neon-green')).strip()

    try:
        clube = ClubeService.criar_clube(nome=nome, cor_tema=cor_tema)
        session['clube_slug'] = clube.get('slug')
        session['clube_codigo'] = clube.get('codigo_formatado')

        return jsonify({
            'sucesso': True,
            'clube': clube,
            'redirect_url': f"/clube/{clube.get('slug')}"
        }), 201
    except ValueError as err:
        return jsonify({'sucesso': False, 'mensagem': str(err)}), 400
    except Exception as err:
        return jsonify({'sucesso': False, 'mensagem': f"Erro ao criar clube: {str(err)}"}), 500


@clube_bp.route('/buscar-clube', methods=['GET'])
def buscar_clube_page():
    """Página de busca e onboarding em um clube existente."""
    return render_template('login.html', start_tab='join-club')


@clube_bp.route('/join/<clube_ref>', methods=['GET'])
def join_clube_direct(clube_ref: str):
    """Link direto para entrar em um clube especifico via codigo ou slug (ex: natrave.pt/join/002)."""
    clube = ClubeService.obter_clube_por_codigo(clube_ref) or ClubeService.obter_clube_por_slug(clube_ref)
    if not clube:
        return redirect(url_for('clube.buscar_clube_page'))
    return render_template('login.html', start_tab='join-club', target_clube=clube)


@clube_bp.route('/api/clube/entrar-com-conta-existente', methods=['POST'])
def api_entrar_conta_existente():
    """
    Etapa 3A: Autentica o usuario e solicita confirmacao antes de vincula-lo ao clube alvo.
    """
    from services.auth_service import AuthService
    from services.jogador_service import JogadorService

    data: Dict[str, Any] = request.get_json() or {}
    username = str(data.get('username', '')).strip()
    senha = str(data.get('senha', '')).strip()
    clube_codigo = str(data.get('clube_codigo', '')).strip()

    if not username or not senha:
        return jsonify({'sucesso': False, 'mensagem': 'Por favor, informe seu usuário e senha.'}), 400

    auth_svc = AuthService()
    user = auth_svc.autenticar(username, senha)

    if not user:
        return jsonify({'sucesso': False, 'mensagem': 'Usuário ou senha incorretos.'}), 401

    clube = ClubeService.obter_clube_por_codigo(clube_codigo) or ClubeService.obter_clube_por_slug(clube_codigo)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    # Retorna dados do usuario para confirmacao ("Identificamos sua conta Guilherme...")
    return jsonify({
        'sucesso': True,
        'requer_confirmacao': True,
        'user': {
            'id': user.get('id'),
            'nome': user.get('nome'),
            'username': user.get('username')
        },
        'clube': {
            'nome': clube.get('nome'),
            'codigo_formatado': clube.get('codigo_formatado'),
            'slug': clube.get('slug')
        }
    }), 200


@clube_bp.route('/api/clube/confirmar-entrada', methods=['POST'])
def api_confirmar_entrada_clube():
    """
    Confirma a vinculacao da conta autenticada ao clube e inicializa sua nota (5.5).
    """
    from services.jogador_service import JogadorService

    data: Dict[str, Any] = request.get_json() or {}
    user_id = str(data.get('user_id', '')).strip()
    clube_codigo = str(data.get('clube_codigo', '')).strip()

    if not user_id or not clube_codigo:
        return jsonify({'sucesso': False, 'mensagem': 'Dados incompletos para associação.'}), 400

    clube = ClubeService.obter_clube_por_codigo(clube_codigo) or ClubeService.obter_clube_por_slug(clube_codigo)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    auth_svc = AuthService()
    user = auth_svc.obter_por_id(user_id) or auth_svc.obter_por_username(user_id)

    # Se for uma conta administrativa (Admin/Organizador), estabelece a sessão do clube e conclui com sucesso
    if user and (user.get('role') in ['admin', 'organizador'] or user.get('username') == 'admin'):
        session['logged_in'] = True
        session['user_id'] = user.get('id')
        session['user_nome'] = user.get('nome') or 'Administrador'
        session['username'] = user.get('username') or 'admin'
        session['role'] = user.get('role', 'admin')
        session['clube_codigo'] = clube.get('codigo_formatado')
        session['clube_slug'] = clube.get('slug')
        auth_svc.salvar_ultimo_clube(user.get('id'), clube.get('codigo_formatado'), clube.get('slug'))

        return jsonify({
            'sucesso': True,
            'mensagem': f"Bem-vindo ao clube {clube.get('nome')}!",
            'redirect_url': f"/clube/{clube.get('slug')}"
        }), 200

    jog_svc = JogadorService()
    jogador = jog_svc.associar_jogador_ao_clube(user_id, clube.get('codigo_formatado'))

    if not jogador:
        return jsonify({'sucesso': False, 'mensagem': 'Não foi possível encontrar a conta do jogador.'}), 404

    # Estabelece sessao no clube alvo para atletas
    session['logged_in'] = True
    session['user_id'] = user_id
    session['user_nome'] = jogador.get('nome')
    session['username'] = jogador.get('username')
    session['role'] = 'usuario'
    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    auth_svc.salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

    return jsonify({
        'sucesso': True,
        'mensagem': f"Bem-vindo ao clube {clube.get('nome')}!",
        'redirect_url': f"/clube/{clube.get('slug')}"
    }), 200


@clube_bp.route('/api/clube/cadastrar-e-entrar', methods=['POST'])
def api_cadastrar_e_entrar_clube():
    """
    Etapa 3B: Cria um novo cadastro com validação completa e associa ao clube escolhido com nota inicial 5.5.
    """
    import re
    from services.auth_service import AuthService
    from services.jogador_service import JogadorService

    data: Dict[str, Any] = request.get_json() or {}
    nome = str(data.get('nome', '')).strip()
    username = str(data.get('username', '')).strip().lower()
    posicao = str(data.get('posicao', 'Linha')).strip()
    senha = str(data.get('senha', '')).strip()
    clube_codigo = str(data.get('clube_codigo', '')).strip()

    nome_partes = [p for p in nome.split() if p]
    if not nome or len(nome_partes) < 2:
        return jsonify({'sucesso': False, 'mensagem': 'Por favor, digite seu nome e sobrenome (no mínimo 2 nomes).'}), 400

    if not username or len(username) < 3:
        return jsonify({'sucesso': False, 'mensagem': 'O nome de usuário deve ter no mínimo 3 caracteres.'}), 400

    if not re.match(r'^[a-z0-9._]{3,30}$', username):
        return jsonify({'sucesso': False, 'mensagem': 'O nome de usuário deve conter apenas letras, números, ponto ou underline (sem espaços).'}), 400

    if not senha or len(senha) < 6:
        return jsonify({'sucesso': False, 'mensagem': 'A senha deve ter no mínimo 6 caracteres.'}), 400

    if not clube_codigo:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não especificado.'}), 400

    clube = ClubeService.obter_clube_por_codigo(clube_codigo) or ClubeService.obter_clube_por_slug(clube_codigo)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    auth_svc = AuthService()
    if auth_svc.obter_por_username(username):
        return jsonify({'sucesso': False, 'mensagem': f"O nome de usuário '@{username}' já está em uso por outro atleta."}), 400

    provided_email = str(data.get('email', '')).strip().lower()
    email = provided_email if provided_email else f"{username}@natrave.pt"
    if provided_email and auth_svc.obter_por_email(provided_email):
        return jsonify({'sucesso': False, 'mensagem': f"O e-mail '{provided_email}' já está em uso por outro atleta."}), 400

    novo_user = auth_svc.criar_usuario(
        email=email,
        username=username,
        nome=nome,
        password=senha,
        role='usuario'
    )

    jog_svc = JogadorService()
    jog_svc.associar_jogador_ao_clube(novo_user.get('id'), clube.get('codigo_formatado'))

    # Estabelece sessao no clube alvo
    session['logged_in'] = True
    session['user_id'] = novo_user.get('id')
    session['user_nome'] = novo_user.get('nome')
    session['username'] = novo_user.get('username')
    session['role'] = 'usuario'
    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    auth_svc.salvar_ultimo_clube(novo_user.get('id'), clube.get('codigo_formatado'), clube.get('slug'))

    return jsonify({
        'sucesso': True,
        'mensagem': f"Conta criada com sucesso! Bem-vindo ao clube {clube.get('nome')}!",
        'redirect_url': f"/clube/{clube.get('slug')}"
    }), 201


@clube_bp.route('/api/clube/criar-com-autenticacao', methods=['POST'])
def api_criar_clube_com_autenticacao():
    """
    Cria um novo clube e associa o criador como organizador/admin, registrando a senha de juiz do clube.
    """
    from services.auth_service import AuthService
    from services.jogador_service import JogadorService

    data: Dict[str, Any] = request.get_json() or {}
    nome_clube = str(data.get('nome_clube', '')).strip()
    cor_tema = str(data.get('cor_tema', 'neon-green')).strip()
    modo_auth = str(data.get('modo_auth', 'existente')).strip()  # 'existente' ou 'novo'
    senha_juiz = str(data.get('senha_juiz') or '123456').strip()

    if not nome_clube or len(nome_clube) < 2:
        return jsonify({'sucesso': False, 'mensagem': 'O nome do clube deve ter pelo menos 2 caracteres.'}), 400

    if len(senha_juiz) < 4:
        return jsonify({'sucesso': False, 'mensagem': 'Defina uma senha de Juiz de pelo menos 4 caracteres para o clube.'}), 400

    try:
        user_id = session.get('user_id')
        user_data = None
        auth_svc = AuthService()

        if modo_auth == 'existente' and not user_id:
            username = str(data.get('username', '')).strip()
            senha = str(data.get('senha', '')).strip()
            user_data = auth_svc.autenticar(username, senha)
            if not user_data:
                return jsonify({'sucesso': False, 'mensagem': 'Usuário ou senha incorretos.'}), 401
            user_id = user_data.get('id')

            nome = str(data.get('nome', '')).strip() or "Administrador"
            username = str(data.get('username', '')).strip() or "admin"
            senha = str(data.get('senha', '')).strip()
            email_in = str(data.get('email', '')).strip().lower()

            if not senha or len(senha) < 4:
                return jsonify({'sucesso': False, 'mensagem': 'Informe uma senha de Admin de no mínimo 4 caracteres.'}), 400

            # 1. Se o e-mail já existe na base do site, autentica o usuário existente
            user_existente_email = auth_svc.obter_por_email(email_in) if email_in else None
            if user_existente_email:
                user_auth = auth_svc.autenticar(email_in, senha)
                if user_auth:
                    user_id = user_auth.get('id')
                    user_data = user_auth
                else:
                    return jsonify({
                        'sucesso': False,
                        'mensagem': 'Este e-mail já está cadastrado no NaTrave. Digite a senha correta da sua conta para continuar.'
                    }), 401
            else:
                user_existente = auth_svc.obter_por_username(username)
                if user_existente:
                    user_auth = auth_svc.autenticar(username, senha)
                    if user_auth:
                        user_id = user_auth.get('id')
                        user_data = user_auth
                    else:
                        from services.clube_service import gerar_slug
                        alt_username = f"admin_{gerar_slug(nome_clube)}"
                        user_existente_alt = auth_svc.obter_por_username(alt_username)
                        if user_existente_alt:
                            user_id = user_existente_alt.get('id')
                            user_data = user_existente_alt
                        else:
                            email = email_in if (email_in and '@' in email_in) else f"{alt_username}@natrave.pt"
                            user_data = auth_svc.criar_usuario(
                                email=email,
                                username=alt_username,
                                nome=nome,
                                password=senha,
                                role='organizador'
                            )
                            user_id = user_data.get('id')
                else:
                    email = email_in if (email_in and '@' in email_in) else f"{username}@natrave.pt"
                    user_data = auth_svc.criar_usuario(
                        email=email,
                        username=username,
                        nome=nome,
                        password=senha,
                        role='organizador'
                    )
                    user_id = user_data.get('id')

        if not user_id:
            return jsonify({'sucesso': False, 'mensagem': 'Você precisa estar autenticado para criar um clube.'}), 401

        clube = ClubeService.criar_clube(
            nome=nome_clube,
            cor_tema=cor_tema,
            admin_user_id=user_id,
            senha_juiz=senha_juiz
        )
        jog_svc = JogadorService()
        jog_svc.associar_jogador_ao_clube(user_id, clube.get('codigo_formatado'))

        session['logged_in'] = True
        session['user_id'] = user_id
        if user_data:
            session['user_nome'] = user_data.get('nome')
            session['username'] = user_data.get('username')
            session['role'] = user_data.get('role', 'organizador')
        else:
            u_info = auth_svc.obter_por_id(user_id)
            if u_info:
                session['user_nome'] = u_info.get('nome')
                session['username'] = u_info.get('username')
                session['role'] = u_info.get('role', 'organizador')

        session['clube_codigo'] = clube.get('codigo_formatado')
        session['clube_slug'] = clube.get('slug')
        session.modified = True
        auth_svc.salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

        return jsonify({
            'sucesso': True,
            'clube': clube,
            'redirect_url': f"/clube/{clube.get('slug')}"
        }), 201
    except ValueError as err:
        return jsonify({'sucesso': False, 'mensagem': str(err)}), 400
    except Exception as err:
        return jsonify({'sucesso': False, 'mensagem': f"Erro ao criar clube: {str(err)}"}), 500


@clube_bp.route('/api/clube/entrar-como-juiz', methods=['POST'])
def api_entrar_como_juiz():
    """
    Autentica o usuário como Juiz de um clube específico após validar a senha do juiz.
    """
    from services.auth_service import AuthService

    data: Dict[str, Any] = request.get_json() or {}
    clube_codigo = str(data.get('clube_codigo', '')).strip()
    senha_juiz = str(data.get('senha_juiz', '')).strip()

    if not clube_codigo or not senha_juiz:
        return jsonify({'sucesso': False, 'mensagem': 'Por favor, informe a senha do juiz.'}), 400

    valido, clube = ClubeService.validar_senha_juiz(clube_codigo, senha_juiz)
    if not valido or not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Senha do Juiz incorreta para este clube.'}), 401

    user_id = session.get('user_id') or f"juiz_{clube.get('codigo_formatado')}"

    session['logged_in'] = True
    session['user_id'] = user_id
    session['user_nome'] = session.get('user_nome') or f"Juiz ({clube.get('nome')})"
    session['role'] = 'juiz'
    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    session.modified = True

    AuthService().salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

    return jsonify({
        'sucesso': True,
        'mensagem': f"Acesso concedido como Juiz do clube {clube.get('nome')}!",
        'redirect_url': '/juiz'
    }), 200


@clube_bp.route('/clube/<clube_slug>')
@clube_bp.route('/clube/<clube_slug>/')
def clube_home(clube_slug: Optional[str] = None):
    """Direciona para a home do clube específico pelo slug."""
    slug_alvo = clube_slug or getattr(g, 'clube_slug', None) or session.get('clube_slug') or 'natrave'
    clube = ClubeService.obter_clube_por_slug(slug_alvo) or ClubeService.obter_clube_por_codigo(slug_alvo)
    if not clube:
        return redirect(url_for('auth.perfil_page'))

    session['clube_slug'] = clube.get('slug')
    session['clube_codigo'] = clube.get('codigo_formatado')
    if session.get('user_id'):
        from services.auth_service import AuthService
        AuthService().salvar_ultimo_clube(session.get('user_id'), clube.get('codigo_formatado'), clube.get('slug'))
    return redirect(url_for('auth.perfil_page'))


@clube_bp.route('/api/clube/trocar-clube', methods=['POST'])
def api_trocar_clube():
    """
    Alterna com segurança o clube ativo na sessão do usuário.
    Garante associação segura ao clube selecionado.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'sucesso': False, 'mensagem': 'Você precisa estar autenticado.'}), 401

    data: Dict[str, Any] = request.get_json() or {}
    clube_ref = str(data.get('clube_ref') or data.get('clube_codigo') or '').strip()
    if not clube_ref:
        return jsonify({'sucesso': False, 'mensagem': 'Informe o clube para o qual deseja mudar.'}), 400

    clube = ClubeService.obter_clube_por_codigo(clube_ref) or ClubeService.obter_clube_por_slug(clube_ref)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    # Garante a associação do jogador ao clube
    from services.jogador_service import JogadorService
    jog_svc = JogadorService()
    jog_svc.associar_jogador_ao_clube(user_id, clube.get('codigo_formatado'))

    # Atualiza sessão de forma segura
    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    session.modified = True
    from services.auth_service import AuthService
    AuthService().salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

    return jsonify({
        'sucesso': True,
        'mensagem': f"Ambiente alterado para o clube {clube.get('nome')}!",
        'redirect_url': f"/clube/{clube.get('slug')}"
    }), 200


@clube_bp.route('/clube/trocar/<clube_ref>', methods=['GET', 'POST'])
def trocar_clube_direto(clube_ref: str):
    """
    Rota direta GET/POST para alternar o clube ativo e redirecionar para a home do clube.
    """
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('clube.buscar_clube_page'))

    clube = ClubeService.obter_clube_por_codigo(clube_ref) or ClubeService.obter_clube_por_slug(clube_ref)
    if not clube:
        return redirect(url_for('auth.editar_perfil_page'))

    from services.jogador_service import JogadorService
    jog_svc = JogadorService()
    jog_svc.associar_jogador_ao_clube(user_id, clube.get('codigo_formatado'))

    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    session.modified = True
    from services.auth_service import AuthService
    AuthService().salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

    return redirect(f"/clube/{clube.get('slug')}")
