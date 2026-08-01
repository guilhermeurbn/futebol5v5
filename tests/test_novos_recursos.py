import json
import pytest
from app import criar_app
from services.comparador_service import ComparadorService
from services.presenca_service import PresencaService


@pytest.fixture
def app_instance(tmp_path):
    app = criar_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


def test_comparador_service(tmp_path):
    import uuid
    from services.jogador_service import JogadorService
    jog_service = JogadorService(arquivo=str(tmp_path / "jogadores.json"))
    
    n1 = f"Alfa {uuid.uuid4().hex[:6]}"
    n2 = f"Beta {uuid.uuid4().hex[:6]}"
    j1 = jog_service.criar(nome=n1, nivel=8.0)
    j2 = jog_service.criar(nome=n2, nivel=7.5)

    comp_service = ComparadorService(jogador_service=jog_service)
    res = comp_service.comparar(j1.id, j2.id)

    assert res["sucesso"] is True
    assert res["j1"]["jogador_nome"] == n1
    assert res["j2"]["jogador_nome"] == n2
    assert "confronto_direto" in res


def test_presenca_service(tmp_path):
    pres_file = str(tmp_path / "presencas.json")
    pres_service = PresencaService(data_file=pres_file)

    from services.auth_service import AuthService
    auth = AuthService(arquivo=str(tmp_path / "users.json"))
    user = auth.criar_usuario("teste_rsvp@example.com", "user_rsvp", "User RSVP", "pass12345")

    pres_service.auth_service = auth
    user_id = user.get("id") if isinstance(user, dict) else user.id
    res = pres_service.registrar_resposta(user_id, "confirmado")

    assert res["status"] == "confirmado"
    assert res["nome"] == "User RSVP"

    resumo = pres_service.obter_resumo()
    assert "confirmados" in resumo


def test_comparar_route(client):
    res = client.get("/comparar")
    assert res.status_code == 200
    assert b"Duelo X1" in res.data or b"Comparador" in res.data


def test_api_presenca_routes(client):
    # Acesso deslogado deve retornar 401
    res_unauth = client.post("/api/presenca/responder", json={"status": "confirmado"})
    assert res_unauth.status_code in [401, 302]

    # Login como usuário
    with client.session_transaction() as sess:
        sess["user_id"] = "user_test_id"
        sess["role"] = "usuario"

    res_resumo = client.get("/api/presenca/resumo")
    assert res_resumo.status_code == 200
    data = json.loads(res_resumo.data)
    assert data["sucesso"] is True


def test_duelo_x1_perfil_integration(client):
    import uuid
    from services.jogador_service import JogadorService
    jog_svc = JogadorService()
    unique_suffix = uuid.uuid4().hex[:6]
    j1 = jog_svc.criar(nome=f"DueloA_{unique_suffix}", nivel=8.0)
    j2 = jog_svc.criar(nome=f"DueloB_{unique_suffix}", nivel=7.5)

    with client.session_transaction() as sess:
        sess["user_id"] = "user_duelo_test"
        sess["role"] = "usuario"
        sess["nome"] = "Jogador Duelo"

    res_perfil = client.get("/perfil")
    assert res_perfil.status_code == 200
    assert b"id=\"dueloOponenteSelect\"" in res_perfil.data

    res_api = client.get(f"/api/comparar?j1={j1.id}&j2={j2.id}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["sucesso"] is True
    assert "confronto_direto" in data


