from pathlib import Path
from app import criar_app


ROOT = Path(__file__).resolve().parents[1]


def test_api_stats_players_uses_jogador_stats_service():
    """Test that /api/stats/players provides standardized keys indexed by player ID and name."""
    app = criar_app()
    with app.test_client() as test_client:
        with test_client.session_transaction() as sess:
            sess['user_id'] = 'test-user-id'

        response = test_client.get('/api/stats/players')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

        if data:
            first_entry = next(iter(data.values()))
            for required_key in ('matches', 'wins', 'win_rate', 'total_partidas', 'vitórias', 'approval'):
                assert required_key in first_entry, f"Missing key '{required_key}' in player stats API payload"


def test_app_shell_has_correct_stat_element_indices():
    """Test that app-shell.js maps index 0 to matches, index 1 to wins, and index 2 to winRate."""
    app_shell_content = (ROOT / "static" / "app-shell.js").read_text(encoding="utf-8")

    assert "statValues[0].textContent = String(matches);" in app_shell_content
    assert "statValues[1].textContent = String(wins);" in app_shell_content
    assert "statValues[2].textContent = `${Math.round(Number(winRate) || 0)}%`;" in app_shell_content


def test_gols_informados_na_votacao_soma_nos_stats(monkeypatch):
    """Testa se gols informados durante votação são contabilizados nos stats do jogador."""
    from services.jogador_stats_service import JogadorStatsService
    svc = JogadorStatsService()
    svc.invalidar_cache_stats()

    partidas_mock = [{
        "id": 9991,
        "sorteio_id": 9991,
        "data": "2026-08-24T12:00:00",
        "participantes": [
            {"user_id": "u-test-gols-1", "jogador_nome": "Jogador Gols Teste", "time_numero": 1, "gols": 3}
        ],
        "votos": [
            {"user_id": "u-test-gols-1", "gols_marcados": 3, "votos": []}
        ]
    }]

    monkeypatch.setattr(svc, '_carregar_partidas', lambda: partidas_mock)
    monkeypatch.setattr(svc, '_carregar_historico', lambda: [])

    stats = svc.obter_stats_jogador("Jogador Gols Teste", user_id="u-test-gols-1")
    assert stats["gols"] == 3
    assert stats["total_partidas"] == 1

