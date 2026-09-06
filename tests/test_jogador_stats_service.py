import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.jogador_stats_service import JogadorStatsService


class FakeJogadorStatsService(JogadorStatsService):
    def __init__(self, partidas, historico):
        super().__init__()
        self._partidas_fake = partidas
        self._historico_fake = historico

    def _carregar_partidas(self):
        return self._partidas_fake

    def _carregar_historico(self):
        return self._historico_fake


def test_win_rate_zero_partidas():
    service = FakeJogadorStatsService(partidas=[], historico=[])
    stats = service.obter_stats_jogador("Carlos")

    assert stats["total_partidas"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["win_rate_valido"] is True


def test_win_rate_com_vitoria_derrota_empate():
    partidas = [
        {
            "id": "p1",
            "sorteio_id": "s1",
            "data": "2026-05-20T10:00:00",
            "jogadores_detalhes": [{"nome": "Carlos", "gols": 1, "assistencias": 0, "cartoes_amarelos": 0, "cartoes_vermelhos": 0, "time_numero": 1}],
            "times_desempenho": [{"time_numero": 1, "vitorias": 1, "derrotas": 0, "empates": 0}],
        },
        {
            "id": "p2",
            "sorteio_id": "s2",
            "data": "2026-05-19T10:00:00",
            "jogadores_detalhes": [{"nome": "Carlos", "gols": 0, "assistencias": 1, "cartoes_amarelos": 1, "cartoes_vermelhos": 0, "time_numero": 2}],
            "times_desempenho": [{"time_numero": 2, "vitorias": 0, "derrotas": 1, "empates": 0}],
        },
        {
            "id": "p3",
            "sorteio_id": "s3",
            "data": "2026-05-18T10:00:00",
            "jogadores_detalhes": [{"nome": "Carlos", "gols": 0, "assistencias": 0, "cartoes_amarelos": 0, "cartoes_vermelhos": 0, "time_numero": 3}],
            "times_desempenho": [{"time_numero": 3, "vitorias": 0, "derrotas": 0, "empates": 1}],
        },
    ]
    historico = [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]

    service = FakeJogadorStatsService(partidas=partidas, historico=historico)
    stats = service.obter_stats_jogador("Carlos")

    assert stats["total_partidas"] == 3
    assert stats["vitórias"] == 1
    assert stats["derrotas"] == 1
    assert stats["empates"] == 1
    assert stats["win_rate"] == 33.3
    assert stats["win_rate_valido"] is True
    assert stats["vitorias"] == stats["vitórias"]

    assert "efficiency" in stats
    assert "discipline" in stats
    assert "ultimos_resultados" in stats
    assert "mini_dashboard" in stats
    assert "planilha_metricas" in stats
    assert len(stats["planilha_metricas"]) == 3


def test_busca_por_nome_normalizado_com_acento():
    partidas = [
        {
            "id": "p1",
            "sorteio_id": "s1",
            "data": "2026-05-21T10:00:00",
            "jogadores_detalhes": [{"nome": "João", "gols": 2, "assistencias": 1, "cartoes_amarelos": 0, "cartoes_vermelhos": 0, "time_numero": 1}],
            "times_desempenho": [{"time_numero": 1, "vitorias": 1, "derrotas": 0, "empates": 0}],
        }
    ]
    historico = [{"id": "s1"}]

    service = FakeJogadorStatsService(partidas=partidas, historico=historico)
    stats = service.obter_stats_jogador("joao")

    assert stats["total_partidas"] == 1
    assert stats["gols"] == 2
    assert stats["assistencias"] == 1


def test_cache_stats_e_invalidacao_global():
    partidas = [
        {
            "id": "p1",
            "sorteio_id": "s1",
            "data": "2026-05-21T10:00:00",
            "jogadores_detalhes": [{"nome": "Carlos", "gols": 1, "assistencias": 0, "cartoes_amarelos": 0, "cartoes_vermelhos": 0, "time_numero": 1}],
            "times_desempenho": [{"time_numero": 1, "vitorias": 1, "derrotas": 0, "empates": 0}],
        }
    ]
    historico = [{"id": "s1"}]
    service = FakeJogadorStatsService(partidas=partidas, historico=historico)

    JogadorStatsService.invalidar_cache_stats()
    _ = service.obter_stats_jogador("Carlos")
    assert len(JogadorStatsService._cache_stats) >= 1

    JogadorStatsService.invalidar_cache_stats()
    assert len(JogadorStatsService._cache_stats) == 0


def test_carregar_partidas_sorteio_id_priority(monkeypatch):
    """Garante que a união de partidas e votações prioriza sorteio_id quando partida.id != votacao.id"""
    partidas_mock = [
        {"id": 4, "sorteio_id": 5, "data": "2026-08-26T00:05:03"},
        {"id": 5, "sorteio_id": 6, "data": "2026-09-01T20:37:49"},
    ]
    votacoes_mock = {
        "partidas": [
            {"id": 5, "sorteio_id": 5, "data": "2026-08-26T01:00:00", "ranking": {"ranking_jogadores": []}},
            {"id": 6, "sorteio_id": 6, "data": "2026-09-02T14:01:41", "ranking": {"ranking_jogadores": []}},
        ]
    }

    def fake_load_json_data(chave, default=None):
        if chave == "partidas":
            return partidas_mock
        if chave == "votacoes_partidas":
            return votacoes_mock
        return default or []

    monkeypatch.setattr("services.jogador_stats_service.load_json_data", fake_load_json_data)
    
    service = JogadorStatsService()
    JogadorStatsService.invalidar_cache_stats()
    combinadas = service._carregar_partidas()

    assert len(combinadas) == 2
    # Partida id=5 (sorteio_id=6) deve ter vinculado com Votacao id=6 (sorteio_id=6), nao com Votacao id=5
    p_sorteio_6 = next((p for p in combinadas if str(p.get("sorteio_id")) == "6"), None)
    assert p_sorteio_6 is not None
    assert str(p_sorteio_6.get("id")) == "5"
    assert p_sorteio_6.get("data") == "2026-09-01T20:37:49"
    assert "ranking" in p_sorteio_6


