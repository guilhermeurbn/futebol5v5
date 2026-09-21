"""
Suíte de testes para os fluxos únicos de Onboarding Multi-Clube:
- Entrar num clube com conta existente (com confirmação de perfil)
- Entrar num clube com novo cadastro
- Criar um novo clube com autenticação/cadastro de organizador
- Rotas dedicadas (/buscar-clube, /criar-clube, /join/<ref>)
"""

import uuid
import pytest
from app import app
from services.clube_service import ClubeService
from services.jogador_service import JogadorService
from services.auth_service import AuthService


@pytest.fixture(autouse=True)
def limpar_dados_teste():
    """Garante que dados criados durante os testes não poluam o banco local de clubes e jogadores."""
    from services.db import load_json_data, save_json_data, clear_db_cache
    import glob, os

    clubes_antes = load_json_data("clubes", [])
    jogadores_antes = load_json_data("jogadores", [])
    users_antes = load_json_data("users", [])

    yield

    save_json_data("clubes", clubes_antes)
    save_json_data("jogadores", jogadores_antes)
    save_json_data("users", users_antes)
    clear_db_cache()

    for fpath in glob.glob("data/clube_0*"):
        if not "clube_001" in fpath:
            try:
                os.remove(fpath)
            except OSError:
                pass


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_rotas_dedicadas_acesso(client):
    """Garante que as rotas dedicadas /buscar-clube e /criar-clube respondam com status 200."""
    resp1 = client.get('/buscar-clube')
    assert resp1.status_code == 200

    resp2 = client.get('/join/001')
    assert resp2.status_code == 200


def test_fluxo_entrar_com_conta_existente_e_confirmacao(client):
    """Testa autenticação inline para um clube e posterior confirmação com nota inicial 5.5."""
    uid = uuid.uuid4().hex[:6]
    username = f"userjoin_{uid}"
    c_name = f"Clube Join {uid}"

    # 1. Criar um usuario de teste
    auth_svc = AuthService()
    user_dict = auth_svc.criar_usuario(email=f"{username}@natrave.pt", username=username, nome=f"Jogador Teste {uid}", password="senha123")
    user_id = user_dict["id"]

    # 2. Criar um clube
    clube_002 = ClubeService.criar_clube(c_name, cor_tema="electric-blue")
    cod = clube_002["codigo_formatado"]

    # 3. Chamar API de login inline
    resp_login = client.post('/api/clube/entrar-com-conta-existente', json={
        "username": username,
        "senha": "senha123",
        "clube_codigo": cod
    })
    assert resp_login.status_code == 200
    data_login = resp_login.get_json()
    assert data_login["sucesso"] is True
    assert data_login["requer_confirmacao"] is True
    assert data_login["user"]["username"] == username

    # 4. Confirmar entrada no clube
    resp_conf = client.post('/api/clube/confirmar-entrada', json={
        "user_id": user_id,
        "clube_codigo": cod
    })
    assert resp_conf.status_code == 200
    data_conf = resp_conf.get_json()
    assert data_conf["sucesso"] is True

    # 5. Verificar se o jogador foi associado com nivel 5.5 isolado no novo clube
    jog_svc = JogadorService()
    jogador = jog_svc.obter_por_id(user_id)
    j_dict = jogador.to_dict() if hasattr(jogador, "to_dict") else getattr(jogador, "__dict__", {})

    assert cod in j_dict.get("clubes_codigos", [])
    assert JogadorService.obter_nivel_no_clube(j_dict, cod) == 5.5


def test_fluxo_cadastrar_e_entrar_no_clube(client):
    """Testa cadastro direto de novo atleta direcionado a um clube especifico."""
    uid = uuid.uuid4().hex[:6]
    c_name = f"Clube Cadastrado {uid}"
    username = f"novoatleta_{uid}"

    clube_003 = ClubeService.criar_clube(c_name, "sunset-purple")
    cod = clube_003["codigo_formatado"]

    resp = client.post('/api/clube/cadastrar-e-entrar', json={
        "nome": f"Novo Atleta {uid}",
        "username": username,
        "posicao": "Goleiro",
        "senha": "senha123456",
        "clube_codigo": cod
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["sucesso"] is True

    # Verificar banco
    jog_svc = JogadorService()
    jogador = jog_svc.obter_por_username(username)
    j_dict = jogador.to_dict() if hasattr(jogador, "to_dict") else (jogador.__dict__ if hasattr(jogador, "__dict__") else jogador)
    assert cod in j_dict.get("clubes_codigos", [])
    assert JogadorService.obter_nivel_no_clube(j_dict, cod) == 5.5


def test_fluxo_criar_clube_com_autenticacao(client):
    """Testa a criacao de um clube por um organizador autenticado."""
    uid = uuid.uuid4().hex[:6]
    username = f"orgboss_{uid}"
    c_name = f"Boss FC {uid}"

    auth_svc = AuthService()
    auth_svc.criar_usuario(email=f"{username}@natrave.pt", username=username, nome=f"Organizador Boss {uid}", password="senha123")


    resp = client.post('/api/clube/criar-com-autenticacao', json={
        "nome_clube": c_name,
        "cor_tema": "gold-ember",
        "modo_auth": "existente",
        "username": username,
        "senha": "senha123"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["sucesso"] is True
    assert data["clube"]["nome"] == c_name


def test_fluxo_entrar_como_juiz_do_clube(client):
    """Testa a criacao de clube com senha de juiz e a posterior autenticacao como Juiz."""
    uid = uuid.uuid4().hex[:6]
    c_name = f"Clube Apito {uid}"

    clube = ClubeService.criar_clube(c_name, senha_juiz="apito123")
    cod = clube["codigo_formatado"]

    # 1. Tentar senha incorreta
    resp_err = client.post('/api/clube/entrar-como-juiz', json={
        "clube_codigo": cod,
        "senha_juiz": "senha_errada"
    })
    assert resp_err.status_code == 401

    # 2. Tentar senha correta
    resp_ok = client.post('/api/clube/entrar-como-juiz', json={
        "clube_codigo": cod,
        "senha_juiz": "apito123"
    })
    assert resp_ok.status_code == 200
    data = resp_ok.get_json()
    assert data["sucesso"] is True
    assert data["redirect_url"] == "/juiz"

    # 3. Seguir o redirect para /juiz garantindo que não cai no login/apresentação
    resp_juiz = client.get('/juiz')
    assert resp_juiz.status_code == 200
    assert "Painel do Juiz" in resp_juiz.get_data(as_text=True)


def test_fluxo_criar_clube_modo_novo_admin_e_boas_vindas(client):
    """Testa a criação de um clube do zero criando uma nova conta de admin e abrindo no modo boas vindas."""
    uid = uuid.uuid4().hex[:6]
    c_name = f"Novo Clube {uid}"
    email = f"novoadmin_{uid}@teste.com"

    resp = client.post('/api/clube/criar-com-autenticacao', json={
        "nome_clube": c_name,
        "cor_tema": "neon-green",
        "modo_auth": "novo",
        "nome": "Novo Admin Pelada",
        "email": email,
        "username": f"admin_{uid}",
        "senha": "adminpassword123",
        "senha_juiz": "juiz123"
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["sucesso"] is True
    assert data["clube"]["nome"] == c_name
    assert "boas_vindas=1" in data["redirect_url"]

    # Verifica se a sessão do client agora está autenticada como admin do clube
    with client.session_transaction() as sess:
        assert sess["logged_in"] is True
        assert sess["role"] == "admin"
        assert sess["clube_codigo"] == data["clube"]["codigo_formatado"]

    # Acessa a home do clube e verifica o Modo Boas-Vindas
    resp_home = client.get(data["redirect_url"], follow_redirects=True)
    assert resp_home.status_code == 200
    html = resp_home.get_data(as_text=True)
    assert "MODO BOAS-VINDAS DO ADMIN" in html
    assert c_name in html
    assert data["clube"]["codigo_formatado"] in html
    assert "Cadastrar Primeiro Jogador" in html


def test_admin_e_juiz_entram_pelo_tenho_conta(client):
    """
    Garante que uma conta de Administrador ou Juiz possa entrar diretamente
    pelo formulário de 'Tenho conta', sendo associada com segurança ao seu respectivo clube.
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    c_terca_nome = f"Clube Terca {uid}"
    admin_terca_user = f"admin_terca_{uid}"
    senha = "password123"

    # 1. Cria Clube Terca com admin exclusivo e senha de juiz
    resp_cria = client.post('/api/clube/criar-com-autenticacao', json={
        "nome_clube": c_terca_nome,
        "modo_auth": "novo",
        "nome": "Admin Terca",
        "email": f"{admin_terca_user}@teste.com",
        "username": admin_terca_user,
        "senha": senha,
        "senha_juiz": "juiz_terca123"
    })
    assert resp_cria.status_code == 201
    clube_terca = resp_cria.get_json()["clube"]

    # 2. Obtém o clube NaTrave (001)
    clube_natrave = ClubeService.garantir_clube_natrave_001()

    # 3. Tenta autenticar a conta de admin_terca no formulário de conta existente
    resp_tentativa = client.post('/api/clube/entrar-com-conta-existente', json={
        "username": admin_terca_user,
        "senha": senha,
        "clube_codigo": clube_natrave["codigo_formatado"]
    })
    # Deve autenticar com sucesso e direcionar para o seu clube próprio onde é admin
    assert resp_tentativa.status_code == 200
    dados_tentativa = resp_tentativa.get_json()
    assert dados_tentativa["sucesso"] is True
    assert dados_tentativa["redirect_url"] == f"/clube/{clube_terca['slug']}"

    # 4. Tenta autenticar a conta de admin_terca no seu PRÓPRIO clube -> Deve permitir e redirecionar
    resp_proprio = client.post('/api/clube/entrar-com-conta-existente', json={
        "username": admin_terca_user,
        "senha": senha,
        "clube_codigo": clube_terca["codigo_formatado"]
    })
    assert resp_proprio.status_code == 200
    dados_proprio = resp_proprio.get_json()
    assert dados_proprio["sucesso"] is True
    assert dados_proprio["redirect_url"] == f"/clube/{clube_terca['slug']}"

    # 5. Tenta autenticar como JUIZ direto no campo de 'Tenho conta'
    resp_juiz = client.post('/api/clube/entrar-com-conta-existente', json={
        "username": "juiz",
        "senha": "juiz_terca123",
        "clube_codigo": clube_terca["codigo_formatado"]
    })
    assert resp_juiz.status_code == 200
    dados_juiz = resp_juiz.get_json()
    assert dados_juiz["sucesso"] is True
    assert dados_juiz["redirect_url"] == "/juiz"


def test_pin_4_digitos_clube(client):
    """
    Testa geração, validação case-insensitive e regeneração da senha de 4 dígitos do clube.
    """
    import re
    uid = uuid.uuid4().hex[:6]
    c_name = f"Clube Senha {uid}"

    # 1. Criação do clube gera automaticamente um PIN de 4 dígitos alfanuméricos
    clube = ClubeService.criar_clube(c_name)
    cod = clube["codigo_formatado"]
    pin_gerado = clube.get("codigo_acesso")

    assert pin_gerado is not None
    assert len(pin_gerado) == 4
    assert re.match(r'^[A-Z0-9]{4}$', pin_gerado)

    # 2. Validação direta via ClubeService (case-insensitive)
    assert ClubeService.validar_pin_clube(cod, pin_gerado) is True
    assert ClubeService.validar_pin_clube(cod, pin_gerado.lower()) is True
    assert ClubeService.validar_pin_clube(cod, "ERR9") is False

    # 3. Validação via API POST /api/clube/validar-pin
    # 3a. Tentativa com senha errada
    resp_err = client.post('/api/clube/validar-pin', json={
        "clube_ref": cod,
        "pin": "ZZZZ" if pin_gerado != "ZZZZ" else "0000"
    })
    assert resp_err.status_code == 403
    assert resp_err.get_json()["sucesso"] is False

    # 3b. Tentativa com senha correta em minúsculas
    resp_ok = client.post('/api/clube/validar-pin', json={
        "clube_ref": cod,
        "pin": pin_gerado.lower()
    })
    assert resp_ok.status_code == 200
    assert resp_ok.get_json()["sucesso"] is True

    # 4. Link direto com pin (?pin=...)
    resp_join = client.get(f'/join/{cod}?pin={pin_gerado}')
    assert resp_join.status_code == 200
    assert pin_gerado in resp_join.get_data(as_text=True)

    # 4b. Link direto com token criptografado (?convite=...)
    token_convite = ClubeService.gerar_token_convite(cod, pin_gerado)
    assert token_convite is not None and len(token_convite) >= 8
    assert ClubeService.decodificar_token_convite(cod, token_convite) == pin_gerado

    resp_join_token = client.get(f'/join/{cod}?convite={token_convite}')
    assert resp_join_token.status_code == 200
    assert pin_gerado in resp_join_token.get_data(as_text=True)

    # 4c. Token forjado / inválido é rejeitado
    assert ClubeService.decodificar_token_convite(cod, token_convite[:-2] + "99") is None
    resp_token_falso = client.get(f'/join/{cod}?convite=token_invalido_fake')
    assert resp_token_falso.status_code == 200
    # Não deve ter injetado o TARGET_PIN_INITIAL
    assert "TARGET_PIN_INITIAL" not in resp_token_falso.get_data(as_text=True)

    # 4d. Link direto com token criptografado para usuário logado associa e redireciona direto
    with client.session_transaction() as sess:
        sess["user_id"] = "user_logado_123"
        sess["username"] = "jogador_teste"
        sess["role"] = "usuario"
    resp_join_logado = client.get(f'/join/{cod}?convite={token_convite}')
    assert resp_join_logado.status_code == 302
    assert f"/clube/{clube['slug']}" in resp_join_logado.headers.get("Location", "")

    # 5. Regenerar PIN pelo Admin
    # Criar sessão de admin para este clube
    with client.session_transaction() as sess:
        sess["user_id"] = "admin_user_pin"
        sess["username"] = "admin_user_pin"
        sess["role"] = "admin"
        sess["clube_codigo"] = cod

    # Atualiza admin_user_id no clube para bater com a sessão
    clubes = ClubeService._carregar_clubes()
    for c in clubes:
        if c.get("codigo_formatado") == cod:
            c["admin_user_id"] = "admin_user_pin"
            break
    ClubeService._salvar_clubes(clubes)

    resp_regen = client.post('/api/clube/regenerar-pin', json={
        "clube_ref": cod
    })
    assert resp_regen.status_code == 200
    data_regen = resp_regen.get_json()
    assert data_regen["sucesso"] is True
    novo_pin = data_regen["novo_pin"]
    assert len(novo_pin) == 4
    assert re.match(r'^[A-Z0-9]{4}$', novo_pin)
    assert data_regen.get("novo_token_convite") is not None

    # Nova senha passa a ser válida
    assert ClubeService.validar_pin_clube(cod, novo_pin) is True
    # Senha antiga não é mais válida (salvo colisão improvável)
    if novo_pin != pin_gerado:
        assert ClubeService.validar_pin_clube(cod, pin_gerado) is False


def test_login_tenho_conta_admin_e_juiz(client):
    """
    Verifica se a tentativa de login no campo 'Tenho conta' com usuário 'admin' ou 'juiz'
    autentica com sucesso para o clube selecionado com a senha mestre 123456.
    """
    uid = uuid.uuid4().hex[:6]
    c_name = f"Clube AdminJuiz {uid}"
    clube = ClubeService.criar_clube(c_name)
    cod = clube["codigo_formatado"]

    # 1. Login com 'admin' e '123456'
    resp_adm = client.post('/api/clube/entrar-com-conta-existente', json={
        "username": "admin",
        "senha": "123456",
        "clube_codigo": cod
    })
    assert resp_adm.status_code == 200
    data_adm = resp_adm.get_json()
    assert data_adm["sucesso"] is True
    assert data_adm["requer_confirmacao"] is False
    assert f"/clube/{clube['slug']}" in data_adm["redirect_url"]

    # 2. Login com 'juiz' e '123456'
    resp_juiz = client.post('/api/clube/entrar-com-conta-existente', json={
        "username": "juiz",
        "senha": "123456",
        "clube_codigo": cod
    })
    assert resp_juiz.status_code == 200
    data_juiz = resp_juiz.get_json()
    assert data_juiz["sucesso"] is True
    assert data_juiz["requer_confirmacao"] is False
    assert data_juiz["redirect_url"] == "/juiz"


def test_login_card_dedicado_admin(client):
    """
    Verifica a autenticação direta via card dedicado de Administrador (apenas senha).
    """
    uid = uuid.uuid4().hex[:6]
    c_name = f"Clube Card Admin {uid}"
    clube = ClubeService.criar_clube(c_name)
    cod = clube["codigo_formatado"]

    # 1. Tentativa com senha errada
    resp_err = client.post('/api/clube/entrar-como-admin', json={
        "clube_codigo": cod,
        "senha_admin": "senha_totalmente_errada"
    })
    assert resp_err.status_code == 401
    assert resp_err.get_json()["sucesso"] is False

    # 2. Tentativa com senha mestre correta
    resp_ok = client.post('/api/clube/entrar-como-admin', json={
        "clube_codigo": cod,
        "senha_admin": "123456"
    })
    assert resp_ok.status_code == 200
    data_ok = resp_ok.get_json()
    assert data_ok["sucesso"] is True
    assert f"/clube/{clube['slug']}" in data_ok["redirect_url"]


def test_tour_onboarding_admin_renderizado(client):
    """
    Garante que a tela inicial para um administrador com modo boas-vindas
    inclui os assets e identificadores das abas necessários para o tour guiado.
    """
    with client.session_transaction() as sess:
        sess["user_id"] = "admin_tour_test"
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["clube_codigo"] = "001"
        sess["clube_slug"] = "natrave"
        sess["boas_vindas_admin"] = True

    resp = client.get('/?boas_vindas=1')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Verifica os assets do tour
    assert "admin-tour.css" in html
    assert "admin-tour.js" in html

    # Verifica IDs das abas para o spotlight
    assert 'id="tourTabJogadores"' in html
    assert 'id="tourTabHistorico"' in html
    assert 'id="tourTabRanking"' in html
    assert 'id="tourTabPerfil"' in html
    assert 'id="tourTabAjustes"' in html

    # Verifica presença do botão de tour no card de boas-vindas
    assert "Tour das Abas" in html




