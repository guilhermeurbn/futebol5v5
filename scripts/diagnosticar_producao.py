#!/usr/bin/env python3
"""
Script de diagnóstico para inspecionar todos os sorteios e partidas no banco de dados.
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.db import load_json_data

def diagnosticar():
    historico = load_json_data("historico", [])
    partidas = load_json_data("partidas", [])
    votacoes = load_json_data("votacoes_partidas", {})
    votacoes_list = (
        votacoes.get("partidas", [])
        if isinstance(votacoes, dict)
        else (votacoes if isinstance(votacoes, list) else [])
    )

    print("==================================================")
    print("1. SORTEIOS EM HISTÓRICO:")
    print("==================================================")
    for h in historico:
        print(f"ID: {h.get('id')} | Data: {h.get('data')} | Oficial: {h.get('oficial')} | Rascunho: {h.get('rascunho')} | Jogadores: {h.get('total_jogadores')}")
        times = h.get('times', [])
        for idx, t in enumerate(times):
            j_nomes = [j.get('nome') for j in t.get('jogadores', [])]
            print(f"   Time {idx+1}: {j_nomes}")

    print("\n==================================================")
    print("2. PARTIDAS REGISTRADAS:")
    print("==================================================")
    for p in partidas:
        print(f"ID: {p.get('id')} | SorteioID: {p.get('sorteio_id')} | Data: {p.get('data')} | Vencedor: {p.get('time_vencedor')}")

    print("\n==================================================")
    print("3. VOTAÇÕES DE PARTIDAS:")
    print("==================================================")
    for vp in votacoes_list:
        print(f"ID: {vp.get('id')} | SorteioID: {vp.get('sorteio_id')} | Status: {vp.get('status')} | Data: {vp.get('data') or vp.get('encerrado_em')}")

if __name__ == "__main__":
    diagnosticar()
