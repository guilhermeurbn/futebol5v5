import pytest
import os
import tempfile
from datetime import datetime
from services.temporada_service import TemporadaService
from services.votacao_service import VotacaoService


@pytest.fixture
def temp_temporada_service():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    service = TemporadaService(data_file=temp_path)
    yield service
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_temporada_service_initialization_and_metrics(temp_temporada_service):
    """Testa que a Temporada #1 e configurada corretamente com datas, contagem e duracao"""
    ativa = temp_temporada_service.obter_temporada_ativa()

    assert ativa["id"] == 1
    assert "Temporada #1" in ativa["nome"]
    assert ativa["data_inicio_fmt"] == "01/07/2026"
    assert ativa["data_fim_fmt"] == "04/10/2026"
    assert "1º Lugar" in ativa["descricao_premio"]


def test_ranking_jogadores_geral_date_filter(monkeypatch):
    """Testa que o ranking filtra corretamente partidas dentro do intervalo de datas da temporada"""
    service = VotacaoService(arquivo="data/votacoes_partidas.json")

    partidas_mock = [
        {
            "id": 1,
            "status": "encerrada",
            "data": "2026-07-15T12:00:00",  # Antes da temporada
            "participantes": [{"jogador_nome": "Alex", "time_numero": 1}],
            "votos": [{"user_id": "u1", "votos": [{"jogador_nome": "Alex", "nota": 10.0}]}]
        },
        {
            "id": 2,
            "status": "encerrada",
            "data": "2026-08-10T12:00:00",  # DENTRO da temporada (04/08 a 04/10)
            "participantes": [{"jogador_nome": "Bruno", "time_numero": 1}],
            "votos": [{"user_id": "u1", "votos": [{"jogador_nome": "Bruno", "nota": 9.0}]}]
        }
    ]

    monkeypatch.setattr(service, 'listar', lambda: partidas_mock)

    # Filtrar no periodo da temporada #1
    resultado_temporada = service.ranking_jogadores_geral(
        limite=50,
        data_inicio="2026-08-04T00:00:00",
        data_fim="2026-10-04T23:59:59"
    )

    # Apenas Bruno deve estar no ranking da temporada
    jogadores_temp = [j["jogador_nome"] for j in resultado_temporada["ranking"]]
    assert "Bruno" in jogadores_temp
    assert "Alex" not in jogadores_temp
    assert resultado_temporada["total_partidas"] == 1


def test_pagina_ranking_com_temporada(monkeypatch):
    """Testa renderizacao da pagina de ranking com parametro tipo=temporada e tipo=geral"""
    from app import app
    with app.test_client() as client:
        res_temp = client.get('/ranking?tipo=temporada')
        assert res_temp.status_code == 200
        body_temp = res_temp.get_data(as_text=True)
        assert 'COMPETIÇÃO OFICIAL DA TEMPORADA' in body_temp
        assert 'Temporada #1' in body_temp
        assert '01/07/2026' in body_temp
        assert '04/10/2026' in body_temp

        res_geral = client.get('/ranking?tipo=geral')
        assert res_geral.status_code == 200
        body_geral = res_geral.get_data(as_text=True)
        assert 'Ranking Histórico Geral' in body_geral
