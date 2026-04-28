#!/usr/bin/env python3
"""
Script de teste para validar o sistema de goleiros com Simulated Annealing
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.jogadores import Jogador
from services.balanceamento import BalanceadorTimes
import uuid
from datetime import datetime


def criar_jogadores_teste():
    """Cria jogadores de teste com goleiros e linha"""
    dados = [
        # Goleiros
        ("Ederson", 9, "goleiro"),
        ("Neymar", 10, "goleiro"),
        ("De Gea", 8, "goleiro"),
        ("Alisson", 9, "goleiro"),
        
        # Linha
        ("Cristiano", 10, "linha"),
        ("Messi", 10, "linha"),
        ("Neymar", 9, "linha"),
        ("Mbappé", 9, "linha"),
        ("Vinicius Jr", 8, "linha"),
        ("Rodrygo", 8, "linha"),
        ("João Pedro", 7, "linha"),
        ("Lucas", 7, "linha"),
        ("Felipe", 6, "linha"),
        ("Bruno", 6, "linha"),
        ("Pedro", 9, "linha"),
        ("João", 8, "linha"),
        ("André", 7, "linha"),
        ("Carlos", 6, "linha"),
        ("Marco", 5, "linha"),
        ("Silva", 8, "linha"),
    ]
    
    jogadores = []
    for nome, nivel, posicao in dados:
        jogadores.append(Jogador(
            nome=nome,
            nivel=nivel,
            tipo="fixo" if len(jogadores) % 3 == 0 else "avulso",
            posicao=posicao,
            presente=True,
            id=str(uuid.uuid4()),
            criado_em=datetime.now().isoformat()
        ))
    
    return jogadores


def test_validacao():
    """Testa validação de jogadores"""
    print("\n" + "="*60)
    print("🧪 TESTE 1: VALIDAÇÃO DE JOGADORES COM GOLEIROS")
    print("="*60)
    
    jogadores = criar_jogadores_teste()
    
    print(f"\nJogadores totais: {len(jogadores)}")
    linha, goleiros = BalanceadorTimes.separar_goleiros(jogadores)
    print(f"Jogadores de linha: {len(linha)}")
    print(f"Goleiros: {len(goleiros)}")
    
    valido, msg = BalanceadorTimes.validar_jogadores_com_goleiros(jogadores)
    print(f"\nValidação: {'✅ OK' if valido else '❌ FALHOU'} - {msg if msg else 'Válido'}")
    
    assert valido, msg
    return True


def test_simulated_annealing():
    """Testa o Simulated Annealing"""
    print("\n" + "="*60)
    print("🧪 TESTE 2: SIMULATED ANNEALING")
    print("="*60)
    
    jogadores = criar_jogadores_teste()
    linha, _ = BalanceadorTimes.separar_goleiros(jogadores)
    num_times = BalanceadorTimes.calcular_numero_times(len(jogadores))
    
    print(f"\nDistribuindo {len(linha)} jogadores de linha em {num_times} times...")
    times_linha = BalanceadorTimes.simulated_annealing(linha, num_times, iteracoes=2000)
    
    print(f"✅ Times criados: {len(times_linha)}")
    
    somas = [sum(j.nivel for j in time) for time in times_linha]
    print(f"\nPontuações: {somas}")
    print(f"Diferença máxima: {max(somas) - min(somas)} pts")
    
    assert len(times_linha) == num_times
    return True


def test_sorteio_com_goleiros():
    """Testa o sorteio completo com goleiros"""
    print("\n" + "="*60)
    print("🧪 TESTE 3: SORTEIO COMPLETO COM GOLEIROS")
    print("="*60)
    
    jogadores = criar_jogadores_teste()
    
    try:
        times, somas, tem_aviso, aviso_msg = BalanceadorTimes.sortear_multiplos_times_com_goleiros(jogadores)

        if tem_aviso and aviso_msg:
            print(f"\n⚠️ Aviso: {aviso_msg}")
        
        print(f"\n✅ {len(times)} times criados")
        
        for i, (time, soma) in enumerate(zip(times, somas)):
            goleiro = [j for j in time if j.posicao == "goleiro"][0]
            linha = [j for j in time if j.posicao == "linha"]
            
            print(f"\n📍 Time {i+1} (Soma linha: {soma} pts):")
            print(f"   🧤 Goleiro: {goleiro.nome} (Nível {goleiro.nivel})")
            for j, jogador in enumerate(linha):
                print(f"   {j+1}. {jogador.nome} (Nível {jogador.nivel})")
        
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        print(f"\n📊 Diferença máxima: {diferenca} pts")
        print(f"📊 Melhor time: {BalanceadorTimes.obter_melhor_time(somas)}")
        
        assert len(times) == BalanceadorTimes.calcular_numero_times(len(jogadores))
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_sorteio_com_goleiros_insuficientes():
    """Valida se a falta de goleiros ainda mantém os times bem equilibrados."""
    print("\n" + "="*60)
    print("🧪 TESTE 4: GOLEIROS INSUFICIENTES")
    print("="*60)

    random_data = [
        ("Goleiro 1", 9, "goleiro"),
        ("Linha 1", 10, "linha"),
        ("Linha 2", 9, "linha"),
        ("Linha 3", 8, "linha"),
        ("Linha 4", 7, "linha"),
        ("Linha 5", 6, "linha"),
        ("Linha 6", 5, "linha"),
        ("Linha 7", 4, "linha"),
        ("Linha 8", 3, "linha"),
        ("Linha 9", 2, "linha"),
    ]

    jogadores = []
    for nome, nivel, posicao in random_data:
        jogadores.append(Jogador(
            nome=nome,
            nivel=nivel,
            tipo="avulso",
            posicao=posicao,
            presente=True,
            id=str(uuid.uuid4()),
            criado_em=datetime.now().isoformat()
        ))

    times, somas, tem_aviso, aviso_msg = BalanceadorTimes.sortear_multiplos_times_com_goleiros(jogadores)
    diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
    goleiros_por_time = [sum(1 for j in time if j.posicao == "goleiro") for time in times]

    print(f"\nPontuações: {somas}")
    print(f"Goleiros por time: {goleiros_por_time}")
    print(f"Diferença máxima: {diferenca} pts")
    print(f"Aviso: {aviso_msg}")

    assert tem_aviso
    assert "Faltam" in aviso_msg
    assert sorted(goleiros_por_time) == [0, 1]
    assert diferenca <= 1
    return True


def main():
    print(f"\n{'='*60}")
    print("⚽ TESTES - SISTEMA DE GOLEIROS COM SIMULATED ANNEALING")
    print(f"{'='*60}")
    
    testes = [
        test_validacao,
        test_simulated_annealing,
        test_sorteio_com_goleiros,
        test_sorteio_com_goleiros_insuficientes,
    ]
    
    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"\n❌ Erro no teste: {e}")
            import traceback
            traceback.print_exc()
            resultados.append(False)
    
    # Resumo
    print(f"\n{'='*60}")
    print("📋 RESUMO")
    print(f"{'='*60}\n")
    
    for i, resultado in enumerate(resultados, 1):
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"  {status} - Teste {i}")
    
    if all(resultados):
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n❌ ALGUNS TESTES FALHARAM")
        return 1


if __name__ == '__main__':
    sys.exit(main())
