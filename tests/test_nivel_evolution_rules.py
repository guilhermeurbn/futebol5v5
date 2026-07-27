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

def test_exemplo_completo_do_usuario():
    # Exemplo fornecido no prompt:
    # Nível atual: 6.5
    # Notas recebidas: 5.0, 4.5, 4.0, 5.0, 4.5
    # Total de jogadores na partida: 10
    #
    # Média: (5+4.5+4+5+4.5) / 5 = 4.6
    # Como notas recebidas são <= 5.0, convertemos multiplicando por 2 -> 4.6 * 2 = 9.2
    # NovaNotaCalculada = (6.5 * 0.70) + (9.2 * 0.30) = 4.55 + 2.76 = 7.31
    # Diferença = 7.31 - 6.5 = 0.81 (>= 0.80 -> alteração tentativa: +0.2)
    # Faixa 3.1 até 7.0 -> alteração máxima: 0.10
    # Clamping da alteração: min(0.2, 0.10) = 0.10
    # Novo nível: 6.5 + 0.10 = 6.6
    
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=6.5,
        notas_recebidas=[5.0, 4.5, 4.0, 5.0, 4.5],
        total_jogadores_partida=10
    )
    assert nivel_novo == 6.6
    assert tendencia == "subiu"

def test_regra_4_e_5_velocidade_e_desaceleracao_experientes():
    # Jogador experiente na faixa 9.1 até 10.0 (máximo alteração permitida 0.02)
    # Nível atual: 9.5
    # Notas recebidas: 10.0, 10.0, 10.0, 10.0, 10.0 (média 10.0, já na escala de 10)
    # NovaNotaCalculada = (9.5 * 0.7) + (10.0 * 0.3) = 6.65 + 3.0 = 9.65
    # Diferença = 9.65 - 9.5 = 0.15 (menor que 0.20 -> alteração tentativa: 0)
    # Resultado esperado: 9.5
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=9.5,
        notas_recebidas=[10.0, 10.0, 10.0, 10.0, 10.0],
        total_jogadores_partida=10
    )
    assert nivel_novo == 9.5
    assert tendencia == "manteve"

    # Jogador de nível 9.1 com notas baixas (ex: 2.0, 2.0, 2.0, 2.0, 2.0)
    # NovaNotaCalculada = (9.1 * 0.7) + (2.0 * 0.3) = 6.37 + 0.6 = 6.97
    # Diferença = 6.97 - 9.1 = -2.13 (>= 0.80 -> alteração tentativa: -0.2)
    # Faixa 9.1 a 10.0 -> max alteração: 0.02
    # Clamped: -0.02
    # Novo nível: 9.1 - 0.02 = 9.08
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=9.1,
        notas_recebidas=[2.0, 2.0, 2.0, 2.0, 2.0],
        total_jogadores_partida=10
    )
    assert nivel_novo == 9.08
    # Ao arredondar para 1 casa decimal, 9.08 rounds to 9.1, logo a tendência é manteve
    assert tendencia == "manteve"

def test_arredondamento_e_limite_global():
    # Limite global máximo (10.0)
    # Nível atual: 10.0, notas ótimas -> deve continuar 10.0
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=10.0,
        notas_recebidas=[10.0, 10.0, 10.0, 10.0, 10.0],
        total_jogadores_partida=10
    )
    assert nivel_novo == 10.0
    assert tendencia == "manteve"

    # Limite global mínimo (1.0)
    # Nível atual: 1.0, notas péssimas -> deve continuar 1.0
    nivel_novo, tendencia = calcular_novo_nivel(
        nivel_atual=1.0,
        notas_recebidas=[0.5, 0.5, 0.5, 0.5, 0.5],
        total_jogadores_partida=10
    )
    assert nivel_novo == 1.0
    assert tendencia == "manteve"
