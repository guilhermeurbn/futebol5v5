"""
Testes unitários para as rotas e resolução de contexto do Passo 2 (Multi-Clube e Roteamento).
"""

import pytest
from app import criar_app
from services.clube_service import ClubeService


@pytest.fixture
def app_client(monkeypatch):
    """Fixture que cria uma instância de testes do app Flask com armazenamento em memória limpo"""
    storage = {"clubes": []}

    def fake_load(namespace, default=None, *args, **kwargs):
        if namespace == "clubes":
            return storage["clubes"]
        return default

    def fake_save(namespace, payload, *args, **kwargs):
        if namespace == "clubes":
            storage["clubes"] = payload

    monkeypatch.setattr("services.clube_service.load_json_data", fake_load)
    monkeypatch.setattr("services.clube_service.save_json_data", fake_save)

    app = criar_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        with app.app_context():
            yield client, app


def test_criar_clube_pagina_renderizacao(app_client):
    """Garante que a página de criação de clubes responda com 200 OK"""
    client, app = app_client
    res = client.get("/criar-clube")
    assert res.status_code == 200


def test_api_validar_nome_clube(app_client):
    """Testa o endpoint AJAX de validação de nome de clube em tempo real"""
    client, app = app_client

    # Nome curto deve retornar 400
    res = client.post("/api/clube/validar-nome", json={"nome": "A"})
    assert res.status_code == 400

    # Nome válido e novo deve retornar disponível: True
    res = client.post("/api/clube/validar-nome", json={"nome": "Clube dos Campeões"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["disponivel"] is True

    # Criar um clube "Clube dos Campeões"
    ClubeService.criar_clube("Clube dos Campeões")

    # Tentar validar o mesmo nome deve indicar indisponível
    res2 = client.post("/api/clube/validar-nome", json={"nome": "clube dos campeoes"})
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["disponivel"] is False


def test_api_criar_clube_sucesso(app_client):
    """Testa a criação de um novo clube via API com retorno de ID 002 e redirect"""
    client, app = app_client

    res = client.post("/api/clube/criar", json={"nome": "Pelada dos Amigos"})
    assert res.status_code == 201
    data = res.get_json()
    assert data["sucesso"] is True
    assert data["clube"]["id_num"] == 2
    assert data["clube"]["codigo_formatado"] == "002"
    assert data["clube"]["slug"] == "pelada-dos-amigos"
    assert data["redirect_url"] == "/clube/pelada-dos-amigos"


def test_resolucao_contexto_clube_natrave_padrao(app_client):
    """Verifica se acessos às rotas padrões continuam resolvendo o Clube 001 (NaTrave) por padrão sem breaking changes"""
    client, app = app_client

    res = client.get("/")
    assert res.status_code in [200, 302]

    with client.session_transaction() as sess:
        assert sess.get("clube_slug") == "natrave"
        assert sess.get("clube_codigo") == "001"


def test_redirecionamento_clube_slug(app_client):
    """Verifica se o aceso à URL /clube/<slug> redireciona corretamente atualizando a sessão"""
    client, app = app_client
    ClubeService.criar_clube("Liga de Ouro", slug="liga-ouro")

    res = client.get("/clube/liga-ouro")
    assert res.status_code == 302

    with client.session_transaction() as sess:
        assert sess.get("clube_slug") == "liga-ouro"
        assert sess.get("clube_codigo") == "002"


def test_api_trocar_clube(app_client):
    """Testa a alternância de clube ativo via API com sessão de usuário autenticado"""
    client, app = app_client
    c = ClubeService.criar_clube("Clube Novo Teste", slug="clube-novo-teste")

    with client.session_transaction() as sess:
        sess["user_id"] = "user_test_123"

    res = client.post("/api/clube/trocar-clube", json={"clube_ref": c["codigo_formatado"]})
    assert res.status_code == 200
    data = res.get_json()
    assert data["sucesso"] is True
    assert data["redirect_url"] == f"/clube/{c['slug']}"

    with client.session_transaction() as sess:
        assert sess.get("clube_codigo") == c["codigo_formatado"]
        assert sess.get("clube_slug") == c["slug"]


def test_admin_bloqueado_de_trocar_clube(app_client):
    """Garante que um admin NÃO consegue alternar para outro clube via API ou GET direto"""
    client, app = app_client
    c_outro = ClubeService.criar_clube("Outro Clube Teste", slug="outro-clube-teste")

    with client.session_transaction() as sess:
        sess["user_id"] = "admin_user_001"
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["clube_codigo"] = "001"
        sess["clube_slug"] = "natrave"

    # 1. Tentativa via api/clube/trocar-clube deve retornar 403
    res_api = client.post("/api/clube/trocar-clube", json={"clube_ref": c_outro["codigo_formatado"]})
    assert res_api.status_code == 403
    data = res_api.get_json()
    assert data["sucesso"] is False

    # 2. Tentativa via trocar_clube_direto deve redirecionar de volta para o clube do admin
    res_get = client.get(f"/clube/trocar/{c_outro['codigo_formatado']}")
    assert res_get.status_code == 302
    assert "/clube/natrave" in res_get.headers.get("Location", "")

    # 3. Tentativa via /clube/<outro-slug> deve forçar retorno para /clube/natrave
    res_url = client.get(f"/clube/{c_outro['slug']}")
    assert res_url.status_code == 302
    assert "/clube/natrave" in res_url.headers.get("Location", "")


def test_admin_nao_ve_meus_clubes_em_editar_perfil(app_client):
    """Garante que a área 'Meus Clubes' e 'Buscar outro clube' não é renderizada para administradores"""
    client, app = app_client

    with client.session_transaction() as sess:
        sess["user_id"] = "admin_user_001"
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["clube_codigo"] = "001"
        sess["clube_slug"] = "natrave"

    res = client.get("/editar-perfil")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "cardItemClubes" not in html
    assert "+ Buscar outro clube" not in html

    # Usuário comum (atleta) deve continuar vendo a seção
    with client.session_transaction() as sess:
        sess["user_id"] = "user_comum_123"
        sess["username"] = "atleta"
        sess["role"] = "usuario"

    res_user = client.get("/editar-perfil")
    assert res_user.status_code == 200
    html_user = res_user.get_data(as_text=True)
    assert "cardItemClubes" in html_user
    assert "+ Buscar outro clube" in html_user
