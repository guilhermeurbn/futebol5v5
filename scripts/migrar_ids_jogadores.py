"""
Script de migração para backfill de IDs únicos (jogador_id e user_id)
em todas as partidas, votações_partidas e histórico do futebol5v5.
"""
import sys
import os

# Adicionar o diretório raiz ao sys.path se necessário
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unicodedata
from services.db import load_json_data, save_json_data, clear_db_cache
from services.auth_service import AuthService
from services.jogador_service import JogadorService
from services.jogador_stats_service import JogadorStatsService


def norm(txt: str) -> str:
    if not txt:
        return ""
    s = unicodedata.normalize("NFKD", str(txt).strip().casefold())
    return "".join(c for c in s if not unicodedata.combining(c))



def executar_migracao_ids() -> dict:
    """
    Percorre todo o banco de dados/JSON e retroencher jogador_id e user_id
    em cada participante de partida, votação e histórico.
    """
    auth_svc = AuthService()
    usuarios = auth_svc._carregar()
    jog_svc = JogadorService()
    jogadores_raw = jog_svc._carregar_raw()

    user_by_id = {str(u["id"]): u for u in usuarios if u.get("id")}
    user_canonical_name = {}
    user_aliases_map = {}

    for u in usuarios:
        uid = str(u.get("id") or "")
        nome = (u.get("nome") or "").strip()
        username = (u.get("username") or "").strip()
        if not uid or not (nome or username):
            continue
        c_name = nome or username
        user_canonical_name[uid] = c_name
        aliases = {norm(nome), norm(username)}
        aliases.discard("")
        user_aliases_map[uid] = aliases

    # Exceções conhecidas / legadas
    gui_main_id = "18c652b0-330e-4e0d-9c5d-eb9a27b889a2"
    gui_old_id = "09142ace-266e-4d33-96db-8b92ed6144c8"
    if gui_main_id in user_canonical_name:
        user_canonical_name[gui_old_id] = user_canonical_name[gui_main_id]
        if gui_main_id in user_aliases_map:
            user_aliases_map[gui_main_id].update({norm("guilherme"), norm("guilherme urbano"), norm("guilherme_urbano")})
            user_aliases_map[gui_old_id] = user_aliases_map[gui_main_id]

    user_jogador_id_map = {}
    jogador_by_id = {}
    jogador_name_map = {}

    for j in jogadores_raw:
        if isinstance(j, dict):
            jid = str(j.get("id") or "")
            owner_id = str(j.get("owner_user_id") or j.get("user_id") or "")
            j_nome = (j.get("nome") or "").strip()
            if jid:
                jogador_by_id[jid] = j
            if owner_id and jid:
                user_jogador_id_map[owner_id] = jid
            if j_nome:
                jogador_name_map[norm(j_nome)] = jid
                if owner_id and owner_id in user_aliases_map:
                    user_aliases_map[owner_id].add(norm(j_nome))

    if gui_main_id in user_jogador_id_map:
        user_jogador_id_map[gui_old_id] = user_jogador_id_map[gui_main_id]

    # Coletar aliases retroativos existentes nos históricos
    partidas = load_json_data("partidas", []) or []
    vot_dados = load_json_data("votacoes_partidas", {}) or {}
    vot_partidas = vot_dados.get("partidas", []) if isinstance(vot_dados, dict) else (vot_dados if isinstance(vot_dados, list) else [])
    historico = load_json_data("historico", []) or []

    for p in partidas:
        if isinstance(p, dict):
            for det in p.get("jogadores_detalhes", []) or []:
                if isinstance(det, dict):
                    uid = str(det.get("user_id") or det.get("owner_user_id") or "")
                    dname = (det.get("nome") or "").strip()
                    if uid and uid in user_aliases_map and dname:
                        user_aliases_map[uid].add(norm(dname))

    for vp in vot_partidas:
        if isinstance(vp, dict):
            for part in vp.get("participantes", []) or []:
                if isinstance(part, dict):
                    uid = str(part.get("user_id") or part.get("owner_user_id") or "")
                    pname = (part.get("jogador_nome") or part.get("nome_usuario") or part.get("nome") or "").strip()
                    if uid and uid in user_aliases_map and pname:
                        user_aliases_map[uid].add(norm(pname))

    def resolver_ids(p_nome: str, p_uid: str = None, p_jid: str = None):
        res_uid = str(p_uid) if p_uid else None
        res_jid = str(p_jid) if p_jid else None
        canonical = None

        if res_uid and res_uid in user_canonical_name:
            canonical = user_canonical_name[res_uid]
            if not res_jid:
                res_jid = user_jogador_id_map.get(res_uid)
            return res_uid, res_jid, canonical

        norm_p = norm(p_nome)
        if norm_p:
            for uid, aliases in user_aliases_map.items():
                if norm_p in aliases:
                    res_uid = uid
                    canonical = user_canonical_name.get(uid)
                    res_jid = user_jogador_id_map.get(uid)
                    return res_uid, res_jid, canonical

            if not res_jid and norm_p in jogador_name_map:
                res_jid = jogador_name_map[norm_p]

        return res_uid, res_jid, canonical

    modificou_partidas = False
    modificou_votacoes = False
    modificou_historico = False
    contagem_ids_adicionados = 0

    # 1. Processar partidas.json
    for p in partidas:
        if not isinstance(p, dict):
            continue
        for det in p.get("jogadores_detalhes", []) or []:
            if isinstance(det, dict):
                uid, jid, canonical = resolver_ids(det.get("nome"), det.get("user_id") or det.get("owner_user_id"), det.get("jogador_id"))
                if uid and det.get("user_id") != uid:
                    det["user_id"] = uid
                    det["owner_user_id"] = uid
                    modificou_partidas = True
                    contagem_ids_adicionados += 1
                if jid and det.get("jogador_id") != jid:
                    det["jogador_id"] = jid
                    modificou_partidas = True
                    contagem_ids_adicionados += 1
                if canonical and det.get("nome") != canonical:
                    det["nome"] = canonical
                    modificou_partidas = True

    # 2. Processar votacoes_partidas
    for vp in vot_partidas:
        if not isinstance(vp, dict):
            continue
        for part in vp.get("participantes", []) or []:
            if isinstance(part, dict):
                p_nome = part.get("jogador_nome") or part.get("nome_usuario") or part.get("nome")
                uid, jid, canonical = resolver_ids(p_nome, part.get("user_id") or part.get("owner_user_id"), part.get("jogador_id"))
                if uid and part.get("user_id") != uid:
                    part["user_id"] = uid
                    part["owner_user_id"] = uid
                    modificou_votacoes = True
                    contagem_ids_adicionados += 1
                if jid and part.get("jogador_id") != jid:
                    part["jogador_id"] = jid
                    modificou_votacoes = True
                    contagem_ids_adicionados += 1
                if canonical:
                    if part.get("jogador_nome") != canonical:
                        part["jogador_nome"] = canonical
                        modificou_votacoes = True
                    if part.get("nome_usuario") != canonical:
                        part["nome_usuario"] = canonical
                        modificou_votacoes = True

        for voto in (vp.get("votos", []) or []):
            if isinstance(voto, dict):
                for voto_j in (voto.get("votos", []) or []):
                    if isinstance(voto_j, dict):
                        uid, jid, canonical = resolver_ids(voto_j.get("jogador_nome"), voto_j.get("user_id") or voto_j.get("owner_user_id"), voto_j.get("jogador_id"))
                        if uid and voto_j.get("user_id") != uid:
                            voto_j["user_id"] = uid
                            modificou_votacoes = True
                        if jid and voto_j.get("jogador_id") != jid:
                            voto_j["jogador_id"] = jid
                            modificou_votacoes = True
                        if canonical and voto_j.get("jogador_nome") != canonical:
                            voto_j["jogador_nome"] = canonical
                            modificou_votacoes = True

        ranking_info = vp.get("ranking")
        if ranking_info and isinstance(ranking_info, dict):
            for rj in ranking_info.get("ranking_jogadores", []) or []:
                if isinstance(rj, dict):
                    uid, jid, canonical = resolver_ids(rj.get("jogador_nome") or rj.get("nome"), rj.get("user_id") or rj.get("owner_user_id"), rj.get("jogador_id"))
                    if uid and rj.get("user_id") != uid:
                        rj["user_id"] = uid
                        modificou_votacoes = True
                    if jid and rj.get("jogador_id") != jid:
                        rj["jogador_id"] = jid
                        modificou_votacoes = True
                    if canonical and rj.get("jogador_nome") != canonical:
                        rj["jogador_nome"] = canonical
                        modificou_votacoes = True

    # 3. Processar historico.json
    for h in historico:
        if not isinstance(h, dict):
            continue
        for t in h.get("times", []) or []:
            if isinstance(t, dict):
                for jog in t.get("jogadores", []) or []:
                    if isinstance(jog, dict):
                        uid, jid, canonical = resolver_ids(jog.get("nome"), jog.get("owner_user_id") or jog.get("user_id"), jog.get("jogador_id") or jog.get("id"))
                        if uid and jog.get("owner_user_id") != uid:
                            jog["owner_user_id"] = uid
                            jog["user_id"] = uid
                            modificou_historico = True
                        if jid and jog.get("jogador_id") != jid:
                            jog["jogador_id"] = jid
                            modificou_historico = True
                        if canonical and jog.get("nome") != canonical:
                            jog["nome"] = canonical
                            modificou_historico = True

    if modificou_partidas:
        save_json_data("partidas", partidas)
    if modificou_votacoes:
        if isinstance(vot_dados, dict):
            vot_dados["partidas"] = vot_partidas
            save_json_data("votacoes_partidas", vot_dados)
        else:
            save_json_data("votacoes_partidas", vot_partidas)
    if modificou_historico:
        save_json_data("historico", historico)

    clear_db_cache()
    JogadorStatsService.invalidar_cache_stats()

    res = {
        "modificou_partidas": modificou_partidas,
        "modificou_votacoes": modificou_votacoes,
        "modificou_historico": modificou_historico,
        "ids_adicionados": contagem_ids_adicionados
    }
    print(f"Migração de IDs executada: {res}")
    return res


if __name__ == "__main__":
    executar_migracao_ids()
