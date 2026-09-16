import pytest
from services.nivel_evolution_service import calcular_novo_nivel

def test_regra_1_votos_insuficientes():
    # 10 jogadores na partida -> precisa de no mínimo 4 votos (40% de 10)
    # Com 3 votos, não deve mudar
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=5.5,
        notas_recebidas=[4.0, 4.5, 5.0],
        total_jogadores_partida=10
    )
    assert nivel_novo == 5.5
    assert tendencia == "votos_insuficientes"

def test_regra_1_votos_suficientes():
    # 10 jogadores na partida -> precisa de 4 votos. Com 4 votos, deve calcular normalmente
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=5.5,
        notas_recebidas=[5.0, 5.0, 5.0, 5.0],
        total_jogadores_partida=10
    )
    assert tendencia != "votos_insuficientes"

def test_evolucao_dinamica_e_bonus_top5():
    # Desempenho excelente (notas 10 na escala 10): alteracao_base = +0.30
    # Com bônus de Top 1 (+0.08): 6.5 + 0.38 = 6.88
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=6.5,
        notas_recebidas=[10.0, 10.0, 10.0, 10.0],
        total_jogadores_partida=10,
        bonus_destaque=0.08
    )
    assert nivel_novo == 6.88
    assert tendencia == "subiu"

    # Desempenho excelente sem bônus: 6.5 + 0.30 = 6.80
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=6.5,
        notas_recebidas=[10.0, 10.0, 10.0, 10.0],
        total_jogadores_partida=10,
        bonus_destaque=0.0
    )
    assert nivel_novo == 6.80
    assert tendencia == "subiu"

    # Desempenho abaixo (notas 0.1): alteracao_base = -0.20
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=6.5,
        notas_recebidas=[0.1, 0.1, 0.1, 0.1],
        total_jogadores_partida=10
    )
    assert nivel_novo == 6.30
    assert tendencia == "desceu"

    # Desempenho moderado acima: 6.0 com notas 7.0 (dif = 0.50 -> +0.20)
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=6.0,
        notas_recebidas=[7.0, 7.0, 7.0, 7.0],
        total_jogadores_partida=10,
        bonus_destaque=0.05
    )
    assert nivel_novo == 6.25
    assert tendencia == "subiu"

def test_arredondamento_e_limite_global():
    # Limite global máximo (10.0)
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=10.0,
        notas_recebidas=[10.0, 10.0, 10.0, 10.0, 10.0],
        total_jogadores_partida=10
    )
    assert nivel_novo == 10.0
    assert tendencia == "manteve"

    # Limite global mínimo (1.0)
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=1.0,
        notas_recebidas=[0.5, 0.5, 0.5, 0.5, 0.5],
        total_jogadores_partida=10
    )
    assert nivel_novo == 1.0
    assert tendencia == "manteve"

def test_variacao_nivel_historico_partidas():
    from services.jogador_stats_service import JogadorStatsService
    svc = JogadorStatsService()
    stats = {
        "historico_partidas": [
            {"sorteio_id": 2, "nota_media": 8.5, "nota_partida": 8.5},
            {"sorteio_id": 1, "nota_media": 6.5, "nota_partida": 6.5},
        ]
    }
    svc._enriquecer_variacao_nivel(stats, "Test Player")
    for p in stats["historico_partidas"]:
        assert "variacao_nivel" in p
        assert "variacao_nivel_str" in p

