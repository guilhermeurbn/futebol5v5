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

def test_regra_5_tetos_assimetricos_opcao_1():
    # Faixa 1.0 a 3.0: subida máx +0.15 / queda máx -0.08
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=2.5, notas_recebidas=[5.0, 5.0, 5.0, 5.0], total_jogadores_partida=10)
    assert nivel_novo == 2.65
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=2.5, notas_recebidas=[0.1, 0.1, 0.1, 0.1], total_jogadores_partida=10)
    assert nivel_novo == 2.42

    # Faixa 3.1 a 5.0: subida máx +0.10 / queda máx -0.05
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=4.0, notas_recebidas=[5.0, 5.0, 5.0, 5.0], total_jogadores_partida=10)
    assert nivel_novo == 4.10
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=4.0, notas_recebidas=[0.1, 0.1, 0.1, 0.1], total_jogadores_partida=10)
    assert nivel_novo == 3.95

    # Faixa 5.1 a 7.0: subida máx +0.08 / queda máx -0.04
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=6.5, notas_recebidas=[5.0, 5.0, 5.0, 5.0], total_jogadores_partida=10)
    assert nivel_novo == 6.58
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=6.5, notas_recebidas=[0.1, 0.1, 0.1, 0.1], total_jogadores_partida=10)
    assert nivel_novo == 6.46

    # Faixa 7.1 a 8.5: subida máx +0.05 / queda máx -0.03
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=8.0, notas_recebidas=[5.0, 5.0, 5.0, 5.0], total_jogadores_partida=10)
    assert nivel_novo == 8.05
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=8.0, notas_recebidas=[0.1, 0.1, 0.1, 0.1], total_jogadores_partida=10)
    assert nivel_novo == 7.97

    # Faixa 8.6 a 10.0: subida máx +0.03 / queda máx -0.02
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=9.0, notas_recebidas=[5.0, 5.0, 5.0, 5.0], total_jogadores_partida=10)
    assert nivel_novo == 9.03
    nivel_novo, _ = calcular_novo_nivel(nivel_atual=9.0, notas_recebidas=[0.1, 0.1, 0.1, 0.1], total_jogadores_partida=10)
    assert nivel_novo == 8.98

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
