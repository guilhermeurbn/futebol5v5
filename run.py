#!/usr/bin/env python3
"""
Script de inicialização e desenvolvimento
"""
import os
import sys
import json
from pathlib import Path

# Cores para terminal
VERDE = '\033[92m'
AZUL = '\033[94m'
AMARELO = '\033[93m'
VERMELHO = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header():
    """Exibe header"""
    print(f"\n{BOLD}{AZUL}⚽ NaTrave - Gerador de Times Equilibrados{RESET}")
    print(f"{AZUL}{'='*50}{RESET}\n")


def criar_dados_exemplo():
    """Cria arquivo de dados de exemplo"""
    exemplo_jogadores = [
        {"id": "1", "nome": "Cristiano", "nivel": 10, "criado_em": "2026-04-01T10:00:00"},
        {"id": "2", "nome": "Messi", "nivel": 10, "criado_em": "2026-04-01T10:00:00"},
        {"id": "3", "nome": "Neymar", "nivel": 9, "criado_em": "2026-04-01T10:00:00"},
        {"id": "4", "nome": "Mbappé", "nivel": 9, "criado_em": "2026-04-01T10:00:00"},
        {"id": "5", "nome": "Vinicius Jr", "nivel": 8, "criado_em": "2026-04-01T10:00:00"},
        {"id": "6", "nome": "Rodrygo", "nivel": 8, "criado_em": "2026-04-01T10:00:00"},
        {"id": "7", "nome": "João Pedro", "nivel": 7, "criado_em": "2026-04-01T10:00:00"},
        {"id": "8", "nome": "Lucas", "nivel": 7, "criado_em": "2026-04-01T10:00:00"},
        {"id": "9", "nome": "Felipe", "nivel": 6, "criado_em": "2026-04-01T10:00:00"},
        {"id": "10", "nome": "Bruno", "nivel": 6, "criado_em": "2026-04-01T10:00:00"},
    ]
    
    with open("jogadores.json", "w", encoding="utf-8") as f:
        json.dump(exemplo_jogadores, f, indent=2, ensure_ascii=False)
    
    print(f"{VERDE}✅ Arquivo de exemplo criado: jogadores.json{RESET}")
    print(f"{AMARELO}   10 jogadores de teste adicionados{RESET}\n")


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print(f"{BOLD}Verificando dependências...{RESET}")
    
    try:
        import importlib.metadata
        flask_version = importlib.metadata.version("flask")
        print(f"{VERDE}✅ Flask {flask_version}{RESET}")
    except Exception:
        try:
            import flask
            print(f"{VERDE}✅ Flask (versão não detectada){RESET}")
        except ImportError:
            print(f"{VERMELHO}❌ Flask não instalado{RESET}")
            return False
    
    try:
        import importlib.metadata
        jinja2_version = importlib.metadata.version("jinja2")
        print(f"{VERDE}✅ Jinja2 {jinja2_version}{RESET}")
    except Exception:
        try:
            import jinja2
            print(f"{VERDE}✅ Jinja2 (versão não detectada){RESET}")
        except ImportError:
            print(f"{VERMELHO}❌ Jinja2 não instalado{RESET}")
            return False
    
    print()
    return True


def main():
    """Função principal"""
    print_header()
    
    # Verificar dependências
    if not check_dependencies():
        print(f"{VERMELHO}Instale as dependências com:{RESET}")
        print(f"{AMARELO}pip install -r requirements.txt{RESET}\n")
        return 1
    
    # Criar dados de exemplo
    if not os.path.exists("jogadores.json"):
        print(f"{BOLD}Criando dados de exemplo...{RESET}")
        criar_dados_exemplo()
    else:
        print(f"{AMARELO}ℹ️  jogadores.json já existe (não será sobrescrito){RESET}\n")
    
    # Iniciando servidor
    print(f"{BOLD}Iniciando servidor Flask...{RESET}\n")
    
    # Tentar porta 5000, se estiver ocupada, usar 5001, 5002, 5003...
    import socket
    
    portas_para_tentar = [5000, 5001, 5002, 5003, 5004, 8000, 8001]
    porta = None
    
    for p in portas_para_tentar:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        resultado = sock.connect_ex(('127.0.0.1', p))
        sock.close()
        
        if resultado != 0:  # Porta disponível
            porta = p
            if p != 5000:
                print(f"{AMARELO}⚠️  Porta 5000 já está em uso{RESET}")
            break
    
    if porta is None:
        print(f"{VERMELHO}❌ Nenhuma porta disponível!{RESET}")
        return 1
    
    print(f"{VERDE}{'='*50}{RESET}")
    print(f"{VERDE}⚽ Servidor rodando em: http://localhost:{porta}{RESET}")
    print(f"{VERDE}{'='*50}{RESET}\n")
    
    # Importar e executar
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=porta)
    except KeyboardInterrupt:
        print(f"\n{AMARELO}⏹️  Servidor interrompido pelo usuário{RESET}\n")
        return 0
    except Exception as e:
        print(f"{VERMELHO}❌ Erro ao iniciar servidor:{RESET}")
        print(f"{VERMELHO}{str(e)}{RESET}\n")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
