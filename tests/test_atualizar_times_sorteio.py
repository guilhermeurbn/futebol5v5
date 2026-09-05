import pytest
from app import app
from services.juiz_partida_service import JuizPartidaService
from services.historico_service import HistoricoService

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'juiz_teste'
            sess['role'] = 'juiz'
        yield c

def test_api_atualizar_times_rascunho(client):
    """Testa a atualização de times quando o sorteio é um rascunho"""
    juiz_svc = JuizPartidaService()
    times_fake = [
        {
            'numero': 1,
            'jogadores': [
                {'id': 101, 'nome': 'Jogador 1', 'nivel': 4.0, 'posicao': 'linha'},
                {'id': 102, 'nome': 'Jogador 2', 'nivel': 3.5, 'posicao': 'linha'}
            ]
        },
        {
            'numero': 2,
            'jogadores': [
                {'id': 103, 'nome': 'Jogador 3', 'nivel': 4.5, 'posicao': 'linha'},
                {'id': 104, 'nome': 'Jogador 4', 'nivel': 3.0, 'posicao': 'linha'}
            ]
        }
    ]
    juiz_svc.salvar_rascunho_sorteio(times_json=times_fake, somas=[7.5, 7.5], diferenca=0.0)

    # Payload trocando Jogador 1 (Time 1) por Jogador 3 (Time 2)
    payload = {
        'times': [
            {'numero': 1, 'jogadores': ['103', '102']},
            {'numero': 2, 'jogadores': ['101', '104']}
        ]
    }

    res = client.post('/api/sorteio/rascunho/times', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['sucesso'] is True

    # Verificar se o rascunho no serviço foi efetivamente atualizado
    rascunho = juiz_svc.obter_rascunho()
    assert rascunho is not None
    jogadores_time_1 = [str(j['id']) for j in rascunho['times'][0]['jogadores']]
    assert jogadores_time_1 == ['103', '102']

    juiz_svc.limpar_rascunho()

def test_api_atualizar_times_oficial(client, monkeypatch):
    """Testa a atualização de times de um sorteio oficial salvo no histórico"""
    from services.db import clear_db_cache
    from services.juiz_partida_service import JuizPartidaService
    clear_db_cache()
    JuizPartidaService().limpar_rascunho()

    with client.session_transaction() as sess:
        sess.clear()
        sess['user_id'] = 1
        sess['username'] = 'juiz_teste'
        sess['role'] = 'juiz'

    sorteio_id = 99991
    sorteio_mock = {
        'id': sorteio_id,
        'oficial': True,
        'num_times': 2,
        'times': [
            {
                'numero': 1,
                'jogadores': [
                    {'id': 201, 'nome': 'Jogador A', 'nivel': 4.0, 'posicao': 'linha'},
                    {'id': 202, 'nome': 'Jogador B', 'nivel': 3.5, 'posicao': 'linha'}
                ]
            },
            {
                'numero': 2,
                'jogadores': [
                    {'id': 203, 'nome': 'Jogador C', 'nivel': 4.5, 'posicao': 'linha'},
                    {'id': 204, 'nome': 'Jogador D', 'nivel': 3.0, 'posicao': 'linha'}
                ]
            }
        ]
    }

    from routes.partida_routes import historico_service
    monkeypatch.setattr(historico_service, 'obter_sorteio', lambda s_id: sorteio_mock if str(s_id) == str(sorteio_id) else None)
    monkeypatch.setattr(historico_service, 'atualizar_times_sorteio', lambda s_id, times: sorteio_mock)

    payload = {
        'times': [
            {'numero': 1, 'jogadores': ['202', '201']},
            {'numero': 2, 'jogadores': ['203', '204']}
        ]
    }

    res = client.post(f'/api/sorteio/{sorteio_id}/times', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['sucesso'] is True

