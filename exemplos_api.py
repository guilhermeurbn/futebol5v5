"""
Exemplo de uso da API
"""

import requests
import json

BASE_URL = "http://localhost:5000"

# Headers padrão
HEADERS = {"Content-Type": "application/json"}


def exemplo_criar_jogadores():
    """Exemplo: Criar jogadores via API"""
    print("\n📝 Criando jogadores...")
    
    jogadores = [
        {"nome": "João Silva", "nivel": 8},
        {"nome": "Maria Santos", "nivel": 7},
        {"nome": "Pedro Oliveira", "nivel": 9},
    ]
    
    for jogador in jogadores:
        response = requests.post(
            f"{BASE_URL}/api/jogadores",
            json=jogador,
            headers=HEADERS
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"  ✅ {jogador['nome']} criado com sucesso (ID: {data['jogador']['id'][:8]}...)")
        else:
            print(f"  ❌ Erro ao criar {jogador['nome']}")


def exemplo_listar_jogadores():
    """Exemplo: Listar jogadores via API"""
    print("\n👥 Listando jogadores...")
    
    response = requests.get(f"{BASE_URL}/api/jogadores")
    
    if response.status_code == 200:
        jogadores = response.json()
        print(f"  Total: {len(jogadores)} jogadores")
        
        for jogador in jogadores[:5]:  # Mostrar primeiros 5
            print(f"    • {jogador['nome']} (Nível {jogador['nivel']})")
        
        if len(jogadores) > 5:
            print(f"    ... e mais {len(jogadores) - 5}")
    else:
        print("  ❌ Erro ao listar jogadores")


def exemplo_sortear_times():
    """Exemplo: Sortear times via API"""
    print("\n🎲 Sorteando times...")
    
    response = requests.get(f"{BASE_URL}/api/times")
    
    if response.status_code == 200:
        data = response.json()
        
        if data['sucesso']:
            print(f"  Time 1: {data['soma1']} pontos")
            for jogador in data['time1'][:3]:
                print(f"    • {jogador['nome']}")
            
            print(f"  Time 2: {data['soma2']} pontos")
            for jogador in data['time2'][:3]:
                print(f"    • {jogador['nome']}")
            
            print(f"  Favorito: {data['favorito']} (diferença: {data['diferenca']} pontos)")
        else:
            print(f"  ⚠️  {data['erro']}")
    else:
        print("  ❌ Erro ao sortear times")


if __name__ == "__main__":
    print("=" * 50)
    print("⚽ Exemplos de Uso da API")
    print("=" * 50)
    
    try:
        # Verificar se servidor está rodando
        response = requests.get(f"{BASE_URL}/api/jogadores", timeout=2)
        
        exemplo_criar_jogadores()
        exemplo_listar_jogadores()
        exemplo_sortear_times()
        
        print("\n✅ Exemplos completados!\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Erro: Servidor não está rodando")
        print("   Execute 'python run.py' para iniciar o servidor\n")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}\n")
