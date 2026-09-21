"""
Módulo de Rotas de Gestão de Clubes (NaTrave 5v5 Multi-Clube)
Oferece endpoints para onboarding, verificação de nome único e gerenciamento de clubes.
"""

from typing import Dict, Any, Optional
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, g
from services.clube_service import ClubeService, ClubeSchema, formatar_id_clube, gerar_slug
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

    if query:
        q_norm = normalizar_texto(query)
        q_code = query.lstrip('0')
        lista_retorno = []
        for c in todos:
            nome_norm = normalizar_texto(c.get('nome', ''))
            cod_fmt = c.get('codigo_formatado', '')
            cod_clean = cod_fmt.lstrip('0')
            slug = c.get('slug', '').lower()

            if (q_norm in nome_norm) or (q_norm in slug) or (query == cod_fmt) or (q_code and q_code == cod_clean):
                lista_retorno.append(c)
    else:
        lista_retorno = todos[:10]

    from services.jogador_service import JogadorService
    jog_svc = JogadorService()
    for c in lista_retorno:
        cod_fmt = c.get('codigo_formatado', '001')
        try:
            c['total_jogadores'] = len(jog_svc.listar(clube_codigo=cod_fmt))
        except Exception:
            c['total_jogadores'] = 0

    return jsonify({'clubes': lista_retorno}), 200


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

    frequencia_jogos = str(data.get('frequencia_jogos') or 'Semanal').strip()
    foto_url = data.get('foto_url')
    escudo_id = str(data.get('escudo_id') or 'classico').strip()

    try:
        clube = ClubeService.criar_clube(
            nome=nome,
            cor_tema=cor_tema,
            frequencia_jogos=frequencia_jogos,
            foto_url=foto_url,
            escudo_id=escudo_id
        )
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


@clube_bp.route('/api/clube/upload-foto', methods=['POST'])
def api_upload_foto_clube():
    """Endpoint para upload de foto/logo de clube."""
    from services.upload_service import UploadService, UploadError
    foto_file = request.files.get('foto')
    clube_id = request.form.get('clube_id') or 'temp'
    if not foto_file or not foto_file.filename:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado.'}), 400

    try:
        us = UploadService()
        url = us.processar_foto_clube(foto_file, clube_id=clube_id)
        return jsonify({'sucesso': True, 'foto_url': url}), 200
    except UploadError as err:
        return jsonify({'sucesso': False, 'mensagem': str(err)}), 400
    except Exception as err:
        logger.error(f"Erro no upload da foto do clube: {err}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro ao processar imagem.'}), 500


@clube_bp.route('/api/clube/atualizar', methods=['POST'])
def api_atualizar_clube():
    """Endpoint para atualizar dados do clube (foto, frequência de jogos, tema) pelo admin."""
    user_id = session.get('user_id')
    user_role = session.get('role')
    clube_cod = session.get('clube_codigo', '001')

    if not user_id or user_role != 'admin':
        return jsonify({'sucesso': False, 'mensagem': 'Acesso negado. Requer conta de Administrador.'}), 403

    data: Dict[str, Any] = request.get_json() or {}
    target_clube_ref = data.get('clube_ref') or clube_cod
    nome = data.get('nome')
    frequencia_jogos = data.get('frequencia_jogos')
    foto_url = data.get('foto_url')
    escudo_id = data.get('escudo_id')
    cor_tema = data.get('cor_tema')
    codigo_acesso = data.get('codigo_acesso')
    senha_juiz = data.get('senha_juiz')

    clube = ClubeService.atualizar_clube(
        identificador=target_clube_ref,
        nome=nome,
        frequencia_jogos=frequencia_jogos,
        foto_url=foto_url,
        escudo_id=escudo_id,
        cor_tema=cor_tema,
        codigo_acesso=codigo_acesso,
        senha_juiz=senha_juiz
    )

    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    # Sincronizar nome na sessão caso seja o clube ativo
    if clube.get('codigo_formatado') == session.get('clube_codigo'):
        session['clube_nome'] = clube.get('nome')
        session.modified = True

    return jsonify({'sucesso': True, 'clube': clube, 'mensagem': 'Dados do clube atualizados com sucesso!'}), 200


@clube_bp.route('/buscar-clube', methods=['GET'])
def buscar_clube_page():
    """Página de busca e onboarding em um clube existente."""
    return render_template('login.html', start_tab='join-club')


@clube_bp.route('/join/<clube_ref>', methods=['GET'])
def join_clube_direct(clube_ref: str):
    """
    Link direto para entrar em um clube específico via código ou slug.
    Aceita token criptografado (?convite=XXXX, ?k=XXXX, ?token=XXXX) ou pin direto (?pin=XXXX).
    """
    clube = ClubeService.obter_clube_por_codigo(clube_ref) or ClubeService.obter_clube_por_slug(clube_ref)
    if not clube:
        return redirect(url_for('clube.buscar_clube_page'))

    clube_cod = clube.get('codigo_formatado', '')
    token_convite = (
        request.args.get('convite')
        or request.args.get('k')
        or request.args.get('token')
        or ''
    ).strip()

    target_pin = ''
    if token_convite:
        target_pin = ClubeService.decodificar_token_convite(clube_cod, token_convite) or ''

    if not target_pin:
        target_pin = request.args.get('pin', '').strip().upper()

    user_id = session.get('user_id')
    if user_id and target_pin and ClubeService.validar_pin_clube(clube_cod, target_pin):
        from services.jogador_service import JogadorService
        jog_svc = JogadorService()
        jog_svc.associar_jogador_ao_clube(user_id, clube_cod)
        session['clube_codigo'] = clube_cod
        session['clube_slug'] = clube.get('slug')
        session.modified = True
        from services.auth_service import AuthService
        AuthService().salvar_ultimo_clube(user_id, clube_cod, clube.get('slug'))
        return redirect(f"/clube/{clube.get('slug')}")

    return render_template('login.html', start_tab='join-club', target_clube=clube, target_pin=target_pin)


@clube_bp.route('/api/clube/validar-pin', methods=['POST'])
def api_validar_pin():
    """
    Endpoint para validar o PIN de 4 dígitos alfanuméricos de um clube.
    """
    data: Dict[str, Any] = request.get_json() or {}
    clube_ref = str(data.get('clube_ref') or data.get('clube_codigo') or '').strip()
    pin = str(data.get('pin') or '').strip().upper()

    if not clube_ref:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não especificado.'}), 400

    clube = ClubeService.obter_clube_por_codigo(clube_ref) or ClubeService.obter_clube_por_slug(clube_ref)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    valido = ClubeService.validar_pin_clube(clube_ref, pin)
    if not valido:
        return jsonify({'sucesso': False, 'mensagem': 'Senha incorreta para este clube.'}), 403

    return jsonify({
        'sucesso': True,
        'mensagem': 'Senha correta!',
        'clube_codigo': clube.get('codigo_formatado'),
        'clube_slug': clube.get('slug')
    }), 200


@clube_bp.route('/api/clube/regenerar-pin', methods=['POST'])
def api_regenerar_pin():
    """
    Regenera a senha de 4 dígitos do clube. Apenas administradores do clube podem regenerar.
    """
    user_id = session.get('user_id')
    user_role = session.get('role')
    clube_cod = session.get('clube_codigo', '001')

    if not user_id or user_role != 'admin':
        return jsonify({'sucesso': False, 'mensagem': 'Acesso negado. Requer conta de Administrador.'}), 403

    data: Dict[str, Any] = request.get_json() or {}
    target_clube_ref = str(data.get('clube_ref') or clube_cod).strip()

    admin_clubes = ClubeService.obter_clubes_onde_usuario_e_admin(user_id, session.get('username'))
    clube = ClubeService.obter_clube_por_codigo(target_clube_ref) or ClubeService.obter_clube_por_slug(target_clube_ref)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    clube_cod_fmt = clube.get('codigo_formatado')
    eh_admin_deste_clube = any(c.get('codigo_formatado') == clube_cod_fmt for c in admin_clubes) or (session.get('username') == 'admin' and clube_cod_fmt == '001')

    if not eh_admin_deste_clube:
        return jsonify({'sucesso': False, 'mensagem': 'Você não tem permissão para alterar a senha deste clube.'}), 403

    novo_pin = ClubeService.regenerar_pin_clube(clube_cod_fmt)
    if not novo_pin:
        return jsonify({'sucesso': False, 'mensagem': 'Erro ao regenerar senha do clube.'}), 500

    novo_token = ClubeService.gerar_token_convite(clube_cod_fmt, novo_pin)

    return jsonify({
        'sucesso': True,
        'novo_pin': novo_pin,
        'novo_token_convite': novo_token,
        'mensagem': f'Nova senha gerada com sucesso: {novo_pin}'
    }), 200


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

    clube = ClubeService.obter_clube_por_codigo(clube_codigo) or ClubeService.obter_clube_por_slug(clube_codigo)
    if not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Clube não encontrado.'}), 404

    # 1. Suporte inteligente para Juiz direto no campo de "Tenho conta"
    if username.lower() in ['juiz', 'juiz_clube', 'arbitro', 'árbitro']:
        valido, clube_juiz = ClubeService.validar_senha_juiz(clube_codigo, senha)
        if not valido or not clube_juiz:
            return jsonify({'sucesso': False, 'mensagem': 'Senha do Juiz incorreta para este clube.'}), 401
        session['logged_in'] = True
        session['role'] = 'juiz'
        session['clube_codigo'] = clube_juiz.get('codigo_formatado')
        session['clube_slug'] = clube_juiz.get('slug')
        session['user_id'] = f"juiz_{clube_juiz.get('codigo_formatado')}"
        session['username'] = 'juiz'
        session['user_nome'] = 'Juiz'
        session['nome'] = 'Juiz'
        session.modified = True
        return jsonify({
            'sucesso': True,
            'requer_confirmacao': False,
            'redirect_url': '/juiz'
        }), 200

    # 2. Suporte inteligente para Admin direto no campo de "Tenho conta"
    if username.lower() == 'admin':
        valido, clube_adm, adm_user = ClubeService.validar_senha_admin(clube_codigo, senha)
        if not valido or not clube_adm:
            return jsonify({'sucesso': False, 'mensagem': 'Senha de Administrador incorreta para este clube.'}), 401
        session['logged_in'] = True
        session['role'] = 'admin'
        session['clube_codigo'] = clube_adm.get('codigo_formatado')
        session['clube_slug'] = clube_adm.get('slug')
        session['user_id'] = (adm_user and adm_user.get('id')) or f"admin_{clube_adm.get('codigo_formatado')}"
        session['username'] = 'admin'
        session['user_nome'] = 'Admin'
        session['nome'] = 'Admin'
        session.modified = True
        AuthService().salvar_ultimo_clube(session['user_id'], clube_adm.get('codigo_formatado'), clube_adm.get('slug'))
        return jsonify({
            'sucesso': True,
            'requer_confirmacao': False,
            'redirect_url': f"/clube/{clube_adm.get('slug')}"
        }), 200

    auth_svc = AuthService()
    user = auth_svc.autenticar(username, senha, clube_codigo=clube_codigo)

    if not user:
        return jsonify({'sucesso': False, 'mensagem': 'Usuário ou senha incorretos.'}), 401

    user_id = user.get('id')
    u_role = user.get('role') or 'usuario'
    u_username = user.get('username')

    # 3. Se a conta for de Administrador/Organizador:
    # Direciona para o clube onde é admin (ou para o clube selecionado se for admin dele)
    admin_clubes = ClubeService.obter_clubes_onde_usuario_e_admin(user_id, u_username)
    if admin_clubes or u_role in ['admin', 'organizador']:
        clubes_codigos_admin = {c.get('codigo_formatado') for c in admin_clubes if c.get('codigo_formatado')}
        if not clubes_codigos_admin and u_username == 'admin':
            clubes_codigos_admin.add('001')

        clube_destino = clube
        if clube.get('codigo_formatado') not in clubes_codigos_admin and admin_clubes:
            clube_destino = admin_clubes[0]

        session['logged_in'] = True
        session['user_id'] = user.get('id')
        session['user_nome'] = 'Admin'
        session['nome'] = 'Admin'
        session['username'] = 'admin'
        session['role'] = 'admin'
        session['clube_codigo'] = clube_destino.get('codigo_formatado')
        session['clube_slug'] = clube_destino.get('slug')
        auth_svc.salvar_ultimo_clube(user.get('id'), clube_destino.get('codigo_formatado'), clube_destino.get('slug'))

        return jsonify({
            'sucesso': True,
            'requer_confirmacao': False,
            'redirect_url': f"/clube/{clube_destino.get('slug')}"
        }), 200

    # 4. Se a conta tiver role de Juiz:
    if u_role == 'juiz':
        session['logged_in'] = True
        session['role'] = 'juiz'
        session['clube_codigo'] = clube.get('codigo_formatado')
        session['clube_slug'] = clube.get('slug')
        session['user_id'] = user.get('id')
        session['username'] = user.get('username')
        session['user_nome'] = user.get('nome') or 'Juiz'
        session.modified = True
        return jsonify({
            'sucesso': True,
            'requer_confirmacao': False,
            'redirect_url': '/juiz'
        }), 200

    # 4. Retorna dados do usuario para confirmacao ("Identificamos sua conta...")
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

    if not user:
        return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

    # Se for admin, vincula e direciona para o seu clube correspondente
    admin_clubes = ClubeService.obter_clubes_onde_usuario_e_admin(user.get('id'), user.get('username'))
    clube_cod_fmt = clube.get('codigo_formatado')

    if admin_clubes or user.get('role') in ['admin', 'organizador'] or user.get('username') == 'admin':
        clubes_codigos_admin = {c.get('codigo_formatado') for c in admin_clubes if c.get('codigo_formatado')}
        if not clubes_codigos_admin and user.get('username') == 'admin':
            clubes_codigos_admin.add('001')

        clube_destino = clube
        if clube_cod_fmt not in clubes_codigos_admin:
            clube_destino = admin_clubes[0] if admin_clubes else clube

        session['logged_in'] = True
        session['user_id'] = user.get('id')
        session['user_nome'] = user.get('nome') or 'Administrador'
        session['username'] = user.get('username') or 'admin'
        session['role'] = user.get('role', 'admin')
        session['clube_codigo'] = clube_destino.get('codigo_formatado')
        session['clube_slug'] = clube_destino.get('slug')
        auth_svc.salvar_ultimo_clube(user.get('id'), clube_destino.get('codigo_formatado'), clube_destino.get('slug'))

        return jsonify({
            'sucesso': True,
            'mensagem': f"Bem-vindo ao clube {clube_destino.get('nome')}!",
            'redirect_url': f"/clube/{clube_destino.get('slug')}"
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
        clube_id_num = ClubeService.proximo_id_disponivel()
        clube_codigo_futuro = formatar_id_clube(clube_id_num)
        slug_clube = gerar_slug(nome_clube)

        user_id = session.get('user_id')
        user_data = None
        auth_svc = AuthService()

        if not user_id:
            email_in = str(data.get('email', '')).strip().lower()
            senha = str(data.get('senha', '')).strip()
            nome_in = str(data.get('nome', '')).strip()
            username_in = str(data.get('username', '')).strip()

            identificador = email_in or username_in
            if not identificador:
                return jsonify({'sucesso': False, 'mensagem': 'Por favor, informe o e-mail ou usuário do Administrador.'}), 400

            if not senha or len(senha) < 6:
                return jsonify({'sucesso': False, 'mensagem': 'A senha do Admin deve ter no mínimo 6 caracteres.'}), 400

            # 1. Se o e-mail ou username já existe na base de usuários, autentica a conta
            user_existente = (auth_svc.obter_por_email(identificador) if ('@' in identificador) else None) or auth_svc.obter_por_username(identificador)
            if user_existente:
                user_auth = auth_svc.autenticar(user_existente.get('email') or user_existente.get('username') or identificador, senha)
                if user_auth:
                    user_id = user_auth.get('id')
                    user_data = user_auth
                else:
                    return jsonify({
                        'sucesso': False,
                        'mensagem': 'Esta conta já está cadastrada no NaTrave. Digite a senha correta para continuar.'
                    }), 401
            else:
                # 2. Cria a nova conta de Administrador exclusiva deste clube
                # Admins assumem apenas 'admin' como username e 'Admin' como nome (nunca derivado do e-mail)
                email = email_in if (email_in and '@' in email_in) else f"admin_{clube_codigo_futuro}@natrave.pt"
                username = username_in if (username_in and username_in.strip().lower() != 'admin') else "admin"
                nome = "Admin"

                user_data = auth_svc.criar_usuario(
                    email=email,
                    username=username,
                    nome=nome,
                    password=senha,
                    role='admin',
                    clube_codigo=clube_codigo_futuro,
                    clube_slug=slug_clube
                )
                user_id = user_data.get('id')
        else:
            user_data = auth_svc.obter_por_id(user_id)

        if not user_id:
            return jsonify({'sucesso': False, 'mensagem': 'Não foi possível autenticar a conta do administrador.'}), 401

        frequencia_jogos = str(data.get('frequencia_jogos') or 'Semanal').strip()
        foto_url = data.get('foto_url')
        escudo_id = str(data.get('escudo_id') or 'classico').strip()

        clube = ClubeService.criar_clube(
            nome=nome_clube,
            cor_tema=cor_tema,
            admin_user_id=user_id,
            senha_juiz=senha_juiz,
            frequencia_jogos=frequencia_jogos,
            foto_url=foto_url,
            escudo_id=escudo_id
        )

        session['logged_in'] = True
        session['user_id'] = user_id
        session['user_nome'] = 'Admin'
        session['nome'] = 'Admin'
        session['username'] = 'admin'
        session['role'] = 'admin'
        session['clube_codigo'] = clube.get('codigo_formatado')
        session['clube_slug'] = clube.get('slug')
        session['boas_vindas_admin'] = True
        session.modified = True
        auth_svc.salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

        return jsonify({
            'sucesso': True,
            'clube': clube,
            'redirect_url': f"/clube/{clube.get('slug')}?boas_vindas=1"
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

    session['logged_in'] = True
    session['role'] = 'juiz'
    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    session['user_id'] = f"juiz_{clube.get('codigo_formatado')}"
    session['username'] = 'juiz'
    session['user_nome'] = 'Juiz'
    session['nome'] = 'Juiz'
    session.modified = True

    return jsonify({
        'sucesso': True,
        'mensagem': f"Acesso como Juiz autorizado no {clube.get('nome')}!",
        'redirect_url': '/juiz'
    }), 200


@clube_bp.route('/api/clube/entrar-como-admin', methods=['POST'])
def api_entrar_como_admin():
    """
    Autentica o usuário como Administrador de um clube específico após validar a senha do admin.
    """
    from services.auth_service import AuthService

    data: Dict[str, Any] = request.get_json() or {}
    clube_codigo = str(data.get('clube_codigo', '')).strip()
    senha_admin = str(data.get('senha_admin', '')).strip()

    if not clube_codigo or not senha_admin:
        return jsonify({'sucesso': False, 'mensagem': 'Por favor, informe a senha do administrador.'}), 400

    valido, clube, admin_user = ClubeService.validar_senha_admin(clube_codigo, senha_admin)
    if not valido or not clube:
        return jsonify({'sucesso': False, 'mensagem': 'Senha de Admin incorreta para este clube.'}), 401

    user_id = (admin_user and admin_user.get('id')) or f"admin_{clube.get('codigo_formatado')}"

    session['logged_in'] = True
    session['role'] = 'admin'
    session['clube_codigo'] = clube.get('codigo_formatado')
    session['clube_slug'] = clube.get('slug')
    session['user_id'] = user_id
    session['username'] = 'admin'
    session['user_nome'] = 'Admin'
    session['nome'] = 'Admin'
    session.modified = True

    AuthService().salvar_ultimo_clube(user_id, clube.get('codigo_formatado'), clube.get('slug'))

    return jsonify({
        'sucesso': True,
        'mensagem': f"Acesso como Administrador autorizado no {clube.get('nome')}!",
        'redirect_url': f"/clube/{clube.get('slug')}"
    }), 200


@clube_bp.route('/clube/<clube_slug>')
@clube_bp.route('/clube/<clube_slug>/')
def clube_home(clube_slug: Optional[str] = None):
    """Direciona para a home do clube específico pelo slug."""
    if session.get('role') == 'admin':
        clube_admin = ClubeService.obter_clube_do_admin(
            user_id=session.get('user_id'),
            username=session.get('username')
        )
        if clube_admin:
            admin_slug = clube_admin.get('slug')
            if clube_slug and clube_slug.strip().lower() != admin_slug.lower():
                return redirect(f"/clube/{admin_slug}")
            clube = clube_admin
        else:
            clube = ClubeService.garantir_clube_natrave_001()
    else:
        slug_alvo = clube_slug or getattr(g, 'clube_slug', None) or session.get('clube_slug') or 'natrave'
        clube = ClubeService.obter_clube_por_slug(slug_alvo) or ClubeService.obter_clube_por_codigo(slug_alvo)
        if not clube:
            return redirect(url_for('jogador.index'))

    session['clube_slug'] = clube.get('slug')
    session['clube_codigo'] = clube.get('codigo_formatado')
    if session.get('user_id'):
        from services.auth_service import AuthService
        AuthService().salvar_ultimo_clube(session.get('user_id'), clube.get('codigo_formatado'), clube.get('slug'))

    boas_vindas = request.args.get('boas_vindas')
    if boas_vindas:
        session['boas_vindas_admin'] = True
    return redirect(url_for('jogador.index', boas_vindas=1 if boas_vindas else None))


@clube_bp.route('/api/clube/trocar-clube', methods=['POST'])
def api_trocar_clube():
    """
    Alterna com segurança o clube ativo na sessão do usuário.
    Garante associação segura ao clube selecionado.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'sucesso': False, 'mensagem': 'Você precisa estar autenticado.'}), 401

    if session.get('role') == 'admin':
        clube_admin = ClubeService.obter_clube_do_admin(user_id=user_id, username=session.get('username'))
        slug = (clube_admin or {}).get('slug', 'natrave')
        return jsonify({
            'sucesso': False,
            'mensagem': 'Administradores possuem acesso exclusivo ao seu respectivo clube.',
            'redirect_url': f"/clube/{slug}"
        }), 403

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

    if session.get('role') == 'admin':
        clube_admin = ClubeService.obter_clube_do_admin(user_id=user_id, username=session.get('username'))
        slug = (clube_admin or {}).get('slug', 'natrave')
        return redirect(f"/clube/{slug}")

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
 
 
@clube_bp.route('/admin/modo-juiz', methods=['GET', 'POST'])
def alternar_para_modo_juiz():
    """
    Alterna instantaneamente o Administrador para o Modo Juiz do clube ativo.
    Guarda a origem do Admin na sessão para retorno com altíssimo desempenho.
    """
    user_id = session.get('user_id')
    user_role = session.get('role')

    if not user_id or user_role != 'admin':
        if user_role == 'juiz':
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'sucesso': True, 'redirect_url': url_for('juiz.jogar_page')})
            return redirect(url_for('juiz.jogar_page'))
        return jsonify({'sucesso': False, 'mensagem': 'Acesso negado. Requer conta de Administrador.'}), 403

    clube_cod = session.get('clube_codigo', '001')
    clube_slug = session.get('clube_slug', 'natrave')

    # Salvar origem para permitir voltar em 1 clique
    session['admin_origem_id'] = user_id
    session['admin_origem_username'] = session.get('username')
    session['admin_origem_nome'] = session.get('nome')
    session['admin_origem_role'] = 'admin'

    # Ativar Juiz na sessão
    session['role'] = 'juiz'
    session['user_id'] = f"juiz_{clube_cod}"
    session['username'] = f"juiz_{clube_slug}"
    session['user_nome'] = 'Juiz do Clube'
    session['nome'] = 'Juiz do Clube'
    session.modified = True

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'sucesso': True, 'redirect_url': url_for('juiz.jogar_page')})

    return redirect(url_for('juiz.jogar_page'))


@clube_bp.route('/juiz/voltar-admin', methods=['GET', 'POST'])
def voltar_para_modo_admin():
    """
    Restaura instantaneamente o Administrador original que alternou para o Modo Juiz.
    """
    admin_id = session.get('admin_origem_id')
    if not admin_id:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'sucesso': True, 'redirect_url': url_for('juiz.jogar_page')})
        return redirect(url_for('juiz.jogar_page'))

    session['role'] = 'admin'
    session['user_id'] = admin_id
    session['username'] = session.pop('admin_origem_username', 'admin')
    session['nome'] = session.pop('admin_origem_nome', 'Administrador')
    session['user_nome'] = session['nome']
    session.pop('admin_origem_id', None)
    session.pop('admin_origem_role', None)
    session.modified = True

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'sucesso': True, 'redirect_url': url_for('auth.perfil_page')})

    return redirect(url_for('auth.perfil_page'))
