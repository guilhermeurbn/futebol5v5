#!/usr/bin/env python3
"""
Script de teste para validar o sistema de múltiplos times
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from models.jogadores import Jogador
from services.jogador_service import JogadorService
from services.balanceamento import BalanceadorTimes
import uuid
from datetime import datetime


def criar_jogadores_teste():
    """Cria jogadores de teste"""
    nomes = [
        "Cristiano", "Messi", "Neymar", "Mbappé", "Vinicius Jr",
        "Rodrygo", "João Pedro", "Lucas", "Felipe", "Bruno",
        "Pedro", "João", "André", "Carlos", "Marco",
        "Silva", "Santos", "Costa", "Oliveira", "Gomes"
    ]
    
    niveis = [
        10, 10, 9, 9, 8, 8, 7, 7, 6, 6,
        9, 8, 7, 6, 5, 8, 7, 6, 5, 4
    ]
    
    jogadores = []
    for i, (nome, nivel) in enumerate(zip(nomes, niveis)):
        jogadores.append(Jogador(
            nome=nome,
            nivel=nivel,
            tipo="fixo" if i % 3 == 0 else "avulso",
            presente=True,
            id=str(uuid.uuid4()),
            criado_em=datetime.now().isoformat()
        ))
    
    return jogadores


def testar_sorteio(jogadores, quantidade):
    """Testa o sorteio com quantidade de jogadores"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTE COM {quantidade} JOGADORES")
    print(f"{'='*60}")
    
    try:
        # Validar
        valido, msg = BalanceadorTimes.validar_jogadores(jogadores[:quantidade])
        if not valido:
            print(f"❌ Validação falhou: {msg}")
            return False
        
        print(f"✅ Validação: OK")
        
        # Calcular número de times
        num_times = BalanceadorTimes.calcular_numero_times(quantidade)
        print(f"✅ Número de times: {num_times} (cada um com 5 jogadores)")
        
        # Sortear
        times, somas = BalanceadorTimes.sortear_multiplos_times(jogadores[:quantidade])
        print(f"✅ Sorteio realizado com sucesso")
        
        # Exibir times
        for i, (time, soma) in enumerate(zip(times, somas)):
            print(f"\n   📍 Time {i+1} (Total: {soma} pts):")
            for j, jogador in enumerate(time):
                print(f"      {j+1}. {jogador.nome} (Nível {jogador.nivel})")
        
        # Análise
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        print(f"\n   📊 Análise:")
        print(f"      • Diferença máxima entre times: {diferenca} pts")
        print(f"      • Melhor time: {melhor_time}")
        print(f"      • Pontuações: {somas}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal"""
    print(f"\n{'='*60}")
    print("⚽ TESTE DO SISTEMA DE MÚLTIPLOS TIMES")
    print(f"{'='*60}\n")
    
    jogadores = criar_jogadores_teste()
    print(f"📦 Criados {len(jogadores)} jogadores de teste")
    
    # Testar diferentes quantidades
    resultados = []
    for quantidade in [10, 15, 20]:
        resultado = testar_sorteio(jogadores, quantidade)
        resultados.append(resultado)
    
    # Resumo final
    print(f"\n{'='*60}")
    print("📋 RESUMO FINAL")
    print(f"{'='*60}\n")
    
    testes = [
        ("10 jogadores (2 times)", resultados[0]),
        ("15 jogadores (3 times)", resultados[1]),
        ("20 jogadores (4 times)", resultados[2]),
    ]
    
    for teste, resultado in testes:
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"  {status} - {teste}")
    
    if all(resultados):
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n❌ ALGUNS TESTES FALHARAM")
        return 1


if __name__ == '__main__':
    sys.exit(main())
