import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from services.partida_service import PartidaService
from services.jogador_stats_service import JogadorStatsService



def test_editar_resultado_partida_recalcula_campeao(monkeypatch):
    """
    Testa se ao editar o desempenho dos times de uma partida,
    o time campeão é recalculado corretamente.
    """
    partidas_mock = [
        {
            "id": 1,
            "sorteio_id": 100,
            "data": "2026-09-22T20:00:00",
            "time_vencedor": 3,
            "gols_times": [0, 0, 0],
            "times_desempenho": [
                {"time_numero": 1, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
                {"time_numero": 2, "vitorias": 2, "empates": 0, "derrotas": 0, "gols": 0},
                {"time_numero": 3, "vitorias": 4, "empates": 0, "derrotas": 0, "gols": 0},
            ]
        }
    ]

    salvas = []
    monkeypatch.setattr(PartidaService, "_carregar_raw", lambda self: partidas_mock)
    monkeypatch.setattr(PartidaService, "_salvar", lambda self, dados: salvas.append(dados))

    svc = PartidaService()

    # Admin corrige: Time 2 teve 4 vitórias e Time 3 teve 3
    novos_desempenhos = [
        {"time_numero": 1, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
        {"time_numero": 2, "vitorias": 4, "empates": 0, "derrotas": 0, "gols": 0},
        {"time_numero": 3, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
    ]

    resultado = svc.editar_resultado_partida(100, novos_desempenhos)

    assert resultado["time_vencedor"] == 2
    assert resultado["times_desempenho"][1]["vitorias"] == 4
    assert resultado["times_desempenho"][2]["vitorias"] == 3
    assert len(salvas) == 1


def test_edicao_resultado_atualiza_stats_jogadores():
    """
    Testa se a mudança de time campeão altera imediatamente
    as vitórias e derrotas calculadas para os jogadores de cada time.
    """
    partida_inicial = {
        "id": 1,
        "sorteio_id": 100,
        "data": "2026-09-22T20:00:00",
        "time_vencedor": 3,  # Inicialmente Time 3 campeão
        "gols_times": [0, 0, 0],
        "times_desempenho": [
            {"time_numero": 1, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 2, "vitorias": 2, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 3, "vitorias": 4, "empates": 0, "derrotas": 0, "gols": 0},
        ],
        "jogadores_detalhes": [
            {"nome": "Jogador Um", "time_numero": 1, "gols": 0},
            {"nome": "Jogador Dois", "time_numero": 2, "gols": 0},
            {"nome": "Jogador Tres", "time_numero": 3, "gols": 0},
        ]
    }

    class MockStatsService(JogadorStatsService):
        def __init__(self, partidas):
            super().__init__()
            self._mock_partidas = partidas

        def _carregar_partidas(self):
            return self._mock_partidas

        def _carregar_historico(self):
            return [{"id": 100}]

    stats_svc = MockStatsService([partida_inicial])
    JogadorStatsService.invalidar_cache_stats()

    # Com Time 3 campeão:
    stats_j2 = stats_svc.obter_stats_jogador("Jogador Dois")
    stats_j3 = stats_svc.obter_stats_jogador("Jogador Tres")

    assert stats_j3["vitórias"] == 1
    assert stats_j3["derrotas"] == 0
    assert stats_j2["vitórias"] == 0
    assert stats_j2["derrotas"] == 1

    # Agora simula a edição do resultado: Time 2 passa a ter 4 vitórias (campeão) e Time 3 passa a ter 3 vitórias
    partida_editada = {
        "id": 1,
        "sorteio_id": 100,
        "data": "2026-09-22T20:00:00",
        "time_vencedor": 2,  # Agora Time 2 é campeão!
        "gols_times": [0, 0, 0],
        "times_desempenho": [
            {"time_numero": 1, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 2, "vitorias": 4, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 3, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
        ],
        "jogadores_detalhes": [
            {"nome": "Jogador Um", "time_numero": 1, "gols": 0},
            {"nome": "Jogador Dois", "time_numero": 2, "gols": 0},
            {"nome": "Jogador Tres", "time_numero": 3, "gols": 0},
        ]
    }

    stats_svc._mock_partidas = [partida_editada]
    JogadorStatsService.invalidar_cache_stats()

    stats_j2_pos = stats_svc.obter_stats_jogador("Jogador Dois")
    stats_j3_pos = stats_svc.obter_stats_jogador("Jogador Tres")

    # Jogador Dois agora tem a vitória!
    assert stats_j2_pos["vitórias"] == 1
    assert stats_j2_pos["derrotas"] == 0
    # Jogador Tres agora tem a derrota!
    assert stats_j3_pos["vitórias"] == 0
    assert stats_j3_pos["derrotas"] == 1


def test_endpoint_editar_resultado_admin(monkeypatch):
    """
    Testa o endpoint POST /sorteio/<id>/editar-resultado com sessão de admin.
    """
    from app import app
    from services.partida_service import PartidaService

    partida_mock = {
        "id": 1,
        "sorteio_id": 99,
        "data": "2026-09-22T20:00:00",
        "time_vencedor": 3,
        "gols_times": [0, 0, 0],
        "times_desempenho": [
            {"time_numero": 1, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 2, "vitorias": 2, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 3, "vitorias": 4, "empates": 0, "derrotas": 0, "gols": 0},
        ]
    }

    monkeypatch.setattr(PartidaService, "_carregar_raw", lambda self: [dict(partida_mock)])
    monkeypatch.setattr(PartidaService, "_salvar", lambda self, dados: None)
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        # 1. Sem login/sem admin deve redirecionar para login
        res_anon = client.post('/sorteio/99/editar-resultado', json={'times': []})
        assert res_anon.status_code in [302, 401, 403]


        # 2. Com login de admin
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin-uuid-123'
            sess['role'] = 'admin'
            sess['is_admin'] = True

        novos_times = [
            {"time_numero": 1, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 2, "vitorias": 4, "empates": 0, "derrotas": 0, "gols": 0},
            {"time_numero": 3, "vitorias": 3, "empates": 0, "derrotas": 0, "gols": 0},
        ]

        res = client.post('/sorteio/99/editar-resultado', json={'times': novos_times})
        assert res.status_code == 200
        data = res.get_json()
        assert data['sucesso'] is True
        assert data['time_vencedor'] == 2

