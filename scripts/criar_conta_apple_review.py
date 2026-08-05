"""
Script utilitário para criar/atualizar a conta de demonstração (Demo Account)
necessária para a submissão do app na Apple App Store (Apple Reviewer Account).
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth_service import AuthService
from services.jogador_service import JogadorService


def garantir_conta_apple_review():
    auth_svc = AuthService()
    jogador_svc = JogadorService()

    username = "apple_tester"
    password = "AppleTest2026!"
    email = "apple.reviewer@natrave.app"
    nome = "Revisor Apple"

    u_existente = auth_svc.obter_por_username(username)
    if u_existente:
        auth_svc.definir_nova_senha(u_existente["id"], password)
        auth_svc.atualizar_email(u_existente["id"], email)
        usuario = u_existente
        print(f"✅ Conta de teste Apple atualizada: username='{username}', password='{password}', email='{email}'")
    else:
        usuario = auth_svc.criar_usuario(
            email=email,
            username=username,
            nome=nome,
            password=password,
            role="usuario"
        )
        print(f"✅ Conta de teste Apple criada com sucesso: username='{username}', password='{password}', email='{email}'")

    # Garantir que o jogador vinculado existe com nivel 7.8 e estatísticas
    jogadores = jogador_svc.listar()
    jogador = next((j for j in jogadores if getattr(j, 'user_id', None) == usuario["id"] or j.nome == nome), None)
    if not jogador:
        try:
            jogador = jogador_svc.criar(
                nome=nome,
                nivel=7.8,
                tipo="fixo",
                posicao="linha",
                owner_user_id=usuario["id"]
            )
        except ValueError:
            jogador = jogador_svc.obter_por_nome(nome)

    if jogador:
        jogador.nivel = 7.8
        jogador.posicao = "linha"
        jogador.user_id = usuario["id"]
        dados_raw = jogador_svc._carregar_raw()
        for p in dados_raw:
            if p.get("id") == jogador.id:
                p["nivel"] = 7.8
                p["user_id"] = usuario["id"]
                p["posicao"] = "linha"
        jogador_svc._salvar(dados_raw)

    print(f"⚽ Jogador vinculado com sucesso: nome='{nome}', nivel=7.8, posicao='linha'")
    return usuario


if __name__ == "__main__":
    garantir_conta_apple_review()
