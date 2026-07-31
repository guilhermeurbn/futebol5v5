import pytest
import os
import tempfile
from services.voto_confiabilidade_service import VotoConfiabilidadeService
from services.votacao_service import VotacaoService


@pytest.fixture
def temp_confiabilidade_service():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    service = VotoConfiabilidadeService(data_file=temp_path)
    yield service
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_peer_deviation_factor_consensus(temp_confiabilidade_service):
    """Testa se votos em consenso recebem peso maximo (1.0)"""
    # 5 avaliadores dao nota 8.5 para o Alex
    outras_notas = [8.5, 8.0, 9.0, 8.5]
    fator = temp_confiabilidade_service.calcular_fator_desvio_pares(8.5, outras_notas)
    assert fator == 1.0


def test_peer_deviation_factor_outlier(temp_confiabilidade_service):
    """Testa se um voto isolado atípico (ex: 1.0 quando todos deram 8.5) recebe peso reduzido"""
    outras_notas = [8.5, 8.5, 9.0, 8.5]
    fator = temp_confiabilidade_service.calcular_fator_desvio_pares(1.0, outras_notas)
    assert fator < 0.30  # Peso reduzido significativamente


def test_distribution_anomaly_spike(temp_confiabilidade_service):
    """Testa anomalia de submissão com Spike (dar 1.0 para todos e 10.0 apenas para 1)"""
    votos_submissao = [
        {"jogador_nome": "Alex", "nota": 10.0},
        {"jogador_nome": "Bruno", "nota": 1.0},
        {"jogador_nome": "Carlos", "nota": 1.0},
        {"jogador_nome": "Daniel", "nota": 1.0},
        {"jogador_nome": "Eduardo", "nota": 1.0},
    ]
    f_dist = temp_confiabilidade_service.calcular_fator_distribuicao(votos_submissao)
    assert f_dist <= 0.25


def test_distribution_anomaly_flat(temp_confiabilidade_service):
    """Testa anomalia de voto flat (dar nota idêntica a todos)"""
    votos_submissao = [
        {"jogador_nome": "Alex", "nota": 10.0},
        {"jogador_nome": "Bruno", "nota": 10.0},
        {"jogador_nome": "Carlos", "nota": 10.0},
    ]
    f_dist = temp_confiabilidade_service.calcular_fator_distribuicao(votos_submissao)
    assert f_dist <= 0.35


def test_relationship_bias_decay(temp_confiabilidade_service):
    """Testa perseguição/favoritismo sistemático ao longo de múltiplas partidas"""
    service = temp_confiabilidade_service
    # Simular histórico onde o usuário 'u1' sempre deu notas +3.0 acima do consenso para 'Alex'
    service.dados["relationships"]["u1:Alex"] = {
        "match_count": 4,
        "cumulative_offset": 12.0  # Média de +3.0 por partida
    }

    f_rel = service.calcular_fator_relacionamento("u1", "Alex", desvio_atual=3.0)
    assert f_rel < 0.70


def test_target_player_baseline_and_peer_consensus(temp_confiabilidade_service):
    """
    Se o jogador tem histórico bom (8.5), mas NA PARTIDA ATUAL todos os colegas deram nota 2.0 (partida ruim),
    a nota 1.0 dada pelo avaliador NÃO é penalizada por baseline porque o consenso da partida apoia a nota baixa!
    """
    service = temp_confiabilidade_service
    service.dados["target_baselines"]["Alex"] = {
        "count": 5,
        "historical_avg": 8.5,
        "sum_scores": 42.5
    }

    # Todos os colegas na partida deram notas entre 1.5 e 2.5
    f_baseline = service.calcular_fator_baseline_jogador(nota=1.0, target_name="Alex", media_pares=2.0)
    assert f_baseline == 1.0


def test_votacao_service_weighted_average_calculation(monkeypatch):
    """Garante integração fim a fim no VotacaoService com médias ponderadas"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_votacoes_path = tf.name

    try:
        service = VotacaoService(arquivo=temp_votacoes_path)

        # Partida fictícia com 3 votos: 2 avaliadores honestos (dão 8.0) e 1 atacante isolado (dá 1.0)
        partida = {
            "id": 1,
            "status": "encerrada",
            "participantes": [
                {"nome": "Alex", "time_numero": 1},
                {"nome": "Bruno", "time_numero": 2},
            ],
            "votos": [
                {
                    "user_id": "u1",
                    "votos": [
                        {"jogador_nome": "Alex", "time_numero": 1, "nota": 8.0},
                        {"jogador_nome": "Bruno", "time_numero": 2, "nota": 7.0},
                    ]
                },
                {
                    "user_id": "u2",
                    "votos": [
                        {"jogador_nome": "Alex", "time_numero": 1, "nota": 8.0},
                        {"jogador_nome": "Bruno", "time_numero": 2, "nota": 7.0},
                    ]
                },
                {
                    "user_id": "u3_hater",
                    "votos": [
                        {"jogador_nome": "Alex", "time_numero": 1, "nota": 1.0},
                        {"jogador_nome": "Bruno", "time_numero": 2, "nota": 7.0},
                    ]
                }
            ]
        }

        ranking = service._apurar_ranking(partida)

        # Encontrar nota do Alex
        alex_stats = next(j for j in ranking["ranking_jogadores"] if j["jogador_nome"] == "Alex")

        # Sem a ponderação de confiabilidade, a média simples seria (8 + 8 + 1) / 3 = 5.67
        # Com a ponderação do sistema, o voto 1.0 tem peso bem menor (~0.15), mantendo a média em ~7.5+
        assert alex_stats["nota_media"] > 7.0
        assert alex_stats["confiabilidade_media"] < 1.0
    finally:
        if os.path.exists(temp_votacoes_path):
            os.remove(temp_votacoes_path)
