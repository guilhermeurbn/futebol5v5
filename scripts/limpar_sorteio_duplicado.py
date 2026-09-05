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
    
    # 1. Agrupar sorteios por data (YYYY-MM-DD) para detectar duplicatas no mesmo dia
    por_data = {}
    for item in historico:
        dt_str = str(item.get("data") or "")[:10]
        if dt_str:
            por_data.setdefault(dt_str, []).append(item)

    for dt, lista in por_data.items():
        if len(lista) > 1:
            # Caso A: Sorteios sem partida quando existe pelo menos 1 sorteio com partida no mesmo dia
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
                        "motivo": "Sorteio rascunho/órfão sem partida associada no mesmo dia"
                    })

            # Caso B: Múltiplos sorteios oficiais com partidas vazias/shell no mesmo dia (troca/substituição durante setup)
            # Mantém apenas o sorteio mais recente do dia que foi a partida final oficial
            if len(com_partida) > 1:
                # Ordenar por data/hora (mais recente por último)
                com_partida_ordenados = sorted(com_partida, key=lambda s: str(s.get("data") or ""))
                # Os anteriores são candidatos a remoção/desativação se não tiverem votação/detalhes
                superseeding_testes = com_partida_ordenados[:-1]
                for teste in superseeding_testes:
                    sid_str = str(teste.get("id"))
                    # Verificar se este teste antigo possui votacao/ranking associado
                    tem_votacao_real = any(
                        isinstance(vp, dict) and str(vp.get("sorteio_id") or vp.get("id")) == sid_str and (vp.get("votos") or vp.get("ranking"))
                        for vp in votacoes_list
                    )
                    if not tem_votacao_real:
                        candidatos_remocao.append({
                            "id": teste.get("id"),
                            "data": teste.get("data"),
                            "rascunho": teste.get("rascunho", False),
                            "oficial": teste.get("oficial", True),
                            "total_jogadores": teste.get("total_jogadores", 0),
                            "motivo": "Sorteio de teste/setup substituído por sorteio mais recente no mesmo dia"
                        })

    # 2. Detectar sorteios/partidas de teste vazios sem votos, sem notas e sem gols em qualquer data
    from services.juiz_partida_service import JuizPartidaService
    sid_atual = ""
    try:
        estado_juiz = JuizPartidaService().obter_estado()
        partida_atual = estado_juiz.get("partida_atual") or {}
        sid_atual = str(partida_atual.get("sorteio_id") or "")
    except Exception:
        pass

    for item in historico:
        sid_str = str(item.get("id"))
        if sid_str == sid_atual:
            continue

        tem_votacao_real = any(
            isinstance(vp, dict) and str(vp.get("sorteio_id") or vp.get("id")) == sid_str and (vp.get("votos") or vp.get("ranking"))
            for vp in votacoes_list
        )
        tem_partida_com_gols = any(
            isinstance(p, dict) and str(p.get("sorteio_id") or p.get("id")) == sid_str and (
                (p.get("gols_time1", 0) or 0) > 0 or (p.get("gols_time2", 0) or 0) > 0 or p.get("tem_voto", False) or p.get("votos_contabilizados", False)
            )
            for p in partidas
        )

        if not tem_votacao_real and not tem_partida_com_gols and len(historico) > 1:
            candidatos_remocao.append({
                "id": item.get("id"),
                "data": item.get("data"),
                "rascunho": item.get("rascunho", False),
                "oficial": item.get("oficial", True),
                "total_jogadores": item.get("total_jogadores", 0),
                "motivo": "Sorteio/partida de teste sem votos, sem notas e sem gols gravados"
            })

    # Remover duplicatas da lista de candidatos por ID
    candidatos_unicos = []
    ids_vistos = set()
    for c in candidatos_remocao:
        if c["id"] not in ids_vistos:
            ids_vistos.add(c["id"])
            candidatos_unicos.append(c)

    return historico, candidatos_unicos


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
    ids_remover_str = {str(c["id"]) for c in candidatos}

    novo_historico = [s for s in historico if s.get("id") not in ids_remover]

    partidas = load_json_data("partidas", [])
    novas_partidas = [
        p for p in partidas
        if isinstance(p, dict) and str(p.get("sorteio_id")) not in ids_remover_str and str(p.get("id")) not in ids_remover_str
    ]

    save_json_data("historico", novo_historico)
    save_json_data("partidas", novas_partidas)
    clear_db_cache()
    JogadorStatsService.invalidar_cache_stats()

    print(f"✅ Sorteio(s) e partida(s) {ids_remover} removido(s) com sucesso!")
    print("🚀 Cache limpo. O histórico dos jogadores está agora desduplicado.")


if __name__ == "__main__":
    is_apply = "--apply" in sys.argv
    executar_limpeza(apply=is_apply)
