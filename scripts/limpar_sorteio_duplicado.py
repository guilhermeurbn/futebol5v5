#!/usr/bin/env python3
"""
Script de Limpeza Segura de Sorteios Duplicados Órfãos em Produção.

Uso:
  python3 scripts/limpar_sorteio_duplicado.py             # Modo Simulação (Dry-run) - NÃO altera nada
  python3 scripts/limpar_sorteio_duplicado.py --apply     # Modo Aplicação - Cria backup e remove o sorteio duplicado
"""
import sys
import os
import json
import shutil
from datetime import datetime

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.db import load_json_data, save_json_data, clear_db_cache
from services.jogador_stats_service import JogadorStatsService


def identificar_duplicados():
    historico = load_json_data("historico", [])
    partidas = load_json_data("partidas", [])
    votacoes = load_json_data("votacoes_partidas", {})
    
    votacoes_list = (
        votacoes.get("partidas", [])
        if isinstance(votacoes, dict)
        else (votacoes if isinstance(votacoes, list) else [])
    )

    # Coletar IDs de sorteios que têm partidas registradas / votação associada
    sorteios_com_resultados = set()
    for p in partidas:
        if isinstance(p, dict):
            sid = p.get("sorteio_id") or p.get("id")
            if sid is not None:
                sorteios_com_resultados.add(str(sid))
                
    for vp in votacoes_list:
        if isinstance(vp, dict):
            sid = vp.get("sorteio_id") or vp.get("id")
            if sid is not None:
                sorteios_com_resultados.add(str(sid))

    candidatos_remocao = []
    
    # Agrupar sorteios por data (YYYY-MM-DD) para detectar duplicatas no mesmo dia
    por_data = {}
    for item in historico:
        dt_str = str(item.get("data") or "")[:10]
        por_data.setdefault(dt_str, []).append(item)

    for dt, lista in por_data.items():
        if len(lista) > 1:
            # Procurar se um dos sorteios tem partida vinculada e o outro é rascunho/sem partida
            com_partida = [s for s in lista if str(s.get("id")) in sorteios_com_resultados]
            sem_partida = [s for s in lista if str(s.get("id")) not in sorteios_com_resultados]

            if com_partida and sem_partida:
                for orfao in sem_partida:
                    candidatos_remocao.append({
                        "id": orfao.get("id"),
                        "data": orfao.get("data"),
                        "rascunho": orfao.get("rascunho", False),
                        "oficial": orfao.get("oficial", True),
                        "total_jogadores": orfao.get("total_jogadores", 0),
                        "motivo": "Sorteio rascunho/órfão sem partida ou votação associada"
                    })

    return historico, candidatos_remocao


def executar_limpeza(apply: bool = False):
    historico, candidatos = identificar_duplicados()

    print("=" * 65)
    print("🔍 DIAGNÓSTICO DE SORTEIOS DUPLICADOS / ÓRFÃOS")
    print("=" * 65)

    if not candidatos:
        print("✅ Nenhum sorteio duplicado órfão foi encontrado. Os dados estão limpos!")
        return

    print(f"⚠️ Encontrado(s) {len(candidatos)} sorteio(s) duplicado(s) órfão(s):\n")
    for c in candidatos:
        print(f"  • ID Sorteio: {c['id']}")
        print(f"    Data: {c['data']}")
        print(f"    Rascunho: {c['rascunho']} | Oficial: {c['oficial']}")
        print(f"    Total Jogadores: {c['total_jogadores']}")
        print(f"    Motivo: {c['motivo']}")
        print("-" * 50)

    if not apply:
        print("\nℹ️ MODO SIMULAÇÃO (DRY-RUN): Nenhum arquivo foi alterado.")
        print("Para aplicar a remoção com backup automático, execute:")
        print("  python3 scripts/limpar_sorteio_duplicado.py --apply\n")
        return

    # Fazer Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join("backups", f"pre_cleanup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    archivos_para_backup = ["historico.json", "partidas.json", "votacoes_partidas.json", "jogadores.json"]
    for fname in archivos_para_backup:
        src = os.path.join("data", fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, fname))

    print(f"📂 Backup criado com sucesso em: {backup_dir}")

    # Filtrar removendo os duplicados
    ids_remover = {c["id"] for c in candidatos}
    novo_historico = [s for s in historico if s.get("id") not in ids_remover]

    save_json_data("historico", novo_historico)
    clear_db_cache()
    JogadorStatsService.invalidar_cache_stats()

    print(f"✅ Sorteio(s) {ids_remover} removido(s) com sucesso!")
    print("🚀 Cache limpo. O histórico dos jogadores está agora desduplicado.")


if __name__ == "__main__":
    is_apply = "--apply" in sys.argv
    executar_limpeza(apply=is_apply)
