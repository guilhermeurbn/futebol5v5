import pytest
from app import criar_app

@pytest.fixture
def app_instance():
    app = criar_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app

@pytest.fixture
def client(app_instance):
    return app_instance.test_client()

def test_admin_editar_nota_jogador_unauthorized(client):
    """Testa que usuário comum não pode acessar o endpoint de edição de notas"""
    resp = client.post('/admin/partida/editar-nota-jogador', json={
        'partida_id': '1',
        'jogador_nome': 'Guilherme urbano',
        'nova_nota': 8.5
    })
    assert resp.status_code in [302, 403]

def test_admin_editar_nota_jogador_authorized(client):
    """Testa que o admin consegue alterar a nota de um jogador em uma partida"""
    with client.session_transaction() as sess:
        sess['user_id'] = 'admin_test_uid'
        sess['username'] = 'admin'
        sess['role'] = 'admin'

    resp = client.post('/admin/partida/editar-nota-jogador', json={
        'partida_id': '10',
        'jogador_nome': 'Guilherme urbano',
        'nova_nota': 9.2
    })
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['sucesso'] is True
    assert data['nova_nota'] == 9.2
