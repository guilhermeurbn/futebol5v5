#!/usr/bin/env python3
"""
Script de inicialização e desenvolvimento
"""
import os
import sys
import json
import argparse

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

    try:
        import importlib.metadata
        limiter_version = importlib.metadata.version("Flask-Limiter")
        print(f"{VERDE}✅ Flask-Limiter {limiter_version}{RESET}")
    except Exception:
        try:
            import flask_limiter
            print(f"{VERDE}✅ Flask-Limiter (versão não detectada){RESET}")
        except ImportError:
            print(f"{VERMELHO}❌ Flask-Limiter não instalado{RESET}")
            return False

    try:
        import importlib.metadata
        wtf_version = importlib.metadata.version("Flask-WTF")
        print(f"{VERDE}✅ Flask-WTF {wtf_version}{RESET}")
    except Exception:
        try:
            import flask_wtf
            print(f"{VERDE}✅ Flask-WTF (versão não detectada){RESET}")
        except ImportError:
            print(f"{VERMELHO}❌ Flask-WTF não instalado{RESET}")
            return False
    
    print()
    return True


def obter_porta(default=5000) -> int:
    """Usa PORT quando definida; caso contrario, usa a porta padrao."""
    porta_env = os.getenv('PORT')
    if not porta_env:
        return default

    try:
        porta = int(porta_env)
    except ValueError:
        raise ValueError(f"PORT precisa ser um numero inteiro. Recebido: {porta_env}")

    if not 1 <= porta <= 65535:
        raise ValueError(f"PORT precisa estar entre 1 e 65535. Recebido: {porta}")

    return porta


def main():
    """Função principal"""
    argparse.ArgumentParser(add_help=True).parse_args()

    print_header()
    
    # Verificar dependências
    if not check_dependencies():
        print(f"{VERMELHO}Instale as dependências com:{RESET}")
        print(f"{AMARELO}./start_local.sh{RESET}")
        print(f"{AMARELO}ou: python -m pip install -r requirements.txt{RESET}\n")
        return 1
    
    # Criar dados de exemplo
    if not os.path.exists("jogadores.json"):
        print(f"{BOLD}Criando dados de exemplo...{RESET}")
        criar_dados_exemplo()
    else:
        print(f"{AMARELO}ℹ️  jogadores.json já existe (não será sobrescrito){RESET}\n")
    
    # Iniciando servidor
    print(f"{BOLD}Iniciando servidor Flask...{RESET}\n")

    try:
        porta = obter_porta()
    except ValueError as e:
        print(f"{VERMELHO}❌ {e}{RESET}\n")
        return 1
    
    print(f"{VERDE}{'='*50}{RESET}")
    print(f"{VERDE}⚽ Servidor rodando em: http://localhost:{porta}{RESET}")
    print(f"{AZUL}💡 Para escolher a porta: PORT=5001 python run.py{RESET}")
    print(f"{VERDE}{'='*50}{RESET}\n")
    
    # Importar e executar
    try:
        from app import app
        # Habilita automaticamente o modo debug/reloader em development quando
        # a configuração `DEBUG` está ativa e a variável `FLASK_ENV` é 'development'.
        # Antes era necessário definir `ENABLE_FLASK_DEBUG`, agora o reload fica
        # disponível por padrão em ambiente de desenvolvimento.
        debug_enabled = (
            app.config.get('DEBUG', False)
            and os.getenv('FLASK_ENV', 'development') == 'development'
        )
        if debug_enabled:
            print(f"{AMARELO}ℹ️  Debug/reloader habilitado automaticamente (development).{RESET}")
        app.run(debug=debug_enabled, host='0.0.0.0', port=porta)
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
