#!/usr/bin/env python3
"""
Script de inicialização e desenvolvimento
"""
import os
import sys
import json
import argparse
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
        {"id": "d0ba86dc-0e10-423d-a2a4-14e5ab1de033", "nome": "Guilherme Urbano", "nivel": 8.5, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "gabriel-goleiro-id-01", "nome": "Gabriel Silva", "nivel": 8.0, "posicao": "goleiro", "criado_em": "2026-04-01T10:00:00"},
        {"id": "carlos-ferreira-id-02", "nome": "Carlos Ferreira", "nivel": 7.5, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "lucas-teixeira-id-03", "nome": "Lucas Teixeira", "nivel": 7.0, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "andre-balada-id-04", "nome": "André Balada", "nivel": 7.5, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "renan-costa-id-05", "nome": "Renan Costa", "nivel": 7.0, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "ramon-santos-id-06", "nome": "Ramon Santos", "nivel": 6.5, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "luan-oliveira-id-07", "nome": "Luan Oliveira", "nivel": 7.0, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "94b644ac-65c3-4172-9e68-2d832cf0dfb7", "nome": "Alex", "nivel": 6.5, "posicao": "linha", "criado_em": "2026-04-01T10:00:00"},
        {"id": "rafael-goleiro-id-09", "nome": "Rafael Souza", "nivel": 7.5, "posicao": "goleiro", "criado_em": "2026-04-01T10:00:00"},
    ]
    
    path = Path(__file__).resolve().parent / "data" / "jogadores.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
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
    target_data = Path(__file__).resolve().parent / "data" / "jogadores.json"
    if not target_data.exists():
        print(f"{BOLD}Criando dados de exemplo...{RESET}")
        criar_dados_exemplo()
    else:
        print(f"{AMARELO}ℹ️  data/jogadores.json já existe (não será sobrescrito){RESET}\n")
    
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
