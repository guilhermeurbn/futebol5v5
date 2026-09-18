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
