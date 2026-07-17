import sys
from app import criar_app
from routes import partida_routes

app = criar_app('testing')
app.config['WTF_CSRF_ENABLED'] = False

# Mock data
sorteio = {
    'id': 7,
    'total_jogadores': 5,
    'num_times': 1,
    'pontuacoes': [25],
    'diferenca': 0,
    'times': [{
        'numero': 1,
        'jogadores': [{
            'nome': 'Jogador 1',
            'nivel': 5,
            'posicao': 'linha',
        }],
    }],
}

import pytest
from unittest.mock import MagicMock

with app.test_request_context():
    with app.test_client() as client:
        # Mock the session
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'juiz'
            sess['username'] = 'referee'

        # Patch services
        import routes.partida_routes as pr
        pr.historico_service.obter_sorteio = MagicMock(return_value=sorteio)
        pr.votacao_service.obter_por_sorteio = MagicMock(return_value=None)
        pr.partida_service.obter_partidas_sorteio = MagicMock(return_value=[])

        response = client.get('/sorteio/7')
        print("STATUS:", response.status_code)
        print("BODY LENGTH:", len(response.data))
        print("BODY:", response.get_data(as_text=True))
