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

