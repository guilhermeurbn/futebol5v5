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

def test_api_atualizar_times_oficial(client):
    """Testa a atualização de times de um sorteio oficial salvo no histórico"""
    hist_svc = HistoricoService()
    sorteios = hist_svc.listar_sorteios()
    if not sorteios:
        pytest.skip("Sem sorteio no histórico para testar")

    sorteio_alvo = sorteios[0]
    sorteio_id = sorteio_alvo['id']
    times_originais = sorteio_alvo.get('times', [])
    if len(times_originais) < 2:
        pytest.skip("Sorteio possui menos de 2 times")

    # Inverter a ordem dos jogadores no primeiro time para simular troca interna
    time1 = times_originais[0]
    jogadores1 = time1.get('jogadores', [])
    if len(jogadores1) < 2:
        pytest.skip("Time 1 tem menos de 2 jogadores")

    keys = []
    for j in jogadores1:
        if j.get('id'):
            keys.append(str(j['id']))
        else:
            keys.append(f"{j.get('nome')}|{j.get('nivel')}|{j.get('posicao')}")

    keys_invertidos = list(reversed(keys))
    payload = {
        'times': [
            {'numero': 1, 'jogadores': keys_invertidos}
        ] + [
            {'numero': t['numero'], 'jogadores': [
                (str(j['id']) if j.get('id') else f"{j.get('nome')}|{j.get('nivel')}|{j.get('posicao')}")
                for j in t.get('jogadores', [])
            ]} for t in times_originais[1:]
        ]
    }

    res = client.post(f'/api/sorteio/{sorteio_id}/times', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['sucesso'] is True
