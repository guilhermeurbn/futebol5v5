import logging
from typing import Dict, Any, Optional
from services.jogador_service import JogadorService
from services.votacao_service import VotacaoService

logger = logging.getLogger(__name__)


class ComparadorService:
    """
    Serviço para comparação direta X1 (Head-to-Head) entre 2 jogadores.
    Calcula estatísticas individuais e retrospecto de partidas no mesmo time vs adversários.
    """

    def __init__(self, jogador_service: Optional[JogadorService] = None, votacao_service: Optional[VotacaoService] = None):
        self.jogador_service = jogador_service or JogadorService()
        self.votacao_service = votacao_service or VotacaoService()

    def _obter_jogador(self, identificador: Any) -> Optional[Dict[str, Any]]:
        if not identificador:
            return None
        id_str = str(identificador).strip().lower()
        jogadores = self.jogador_service.listar_para_dict()
        for j in jogadores:
            j_id_str = str(j.get("id", "")).strip().lower()
            j_owner_str = str(j.get("owner_user_id", "")).strip().lower()
            j_nome_str = (j.get("nome") or "").strip().lower()
            if id_str in (j_id_str, j_owner_str, j_nome_str):
                return j

        # Se não achou na lista de jogadores, tentar buscar nos usuários do AuthService
        try:
            from services.auth_service import AuthService
            auth_service = AuthService()
            user = auth_service.obter_por_id(id_str) or auth_service.obter_por_username(id_str)
            if user:
                u_id = user.get("id")
                u_nome = user.get("nome") or user.get("username") or "Atleta"
                for j in jogadores:
                    if str(j.get("owner_user_id", "")) == str(u_id):
                        return j
                return {
                    "id": u_id,
                    "nome": u_nome,
                    "nivel": 5.5,
                    "posicao": "linha",
                    "tipo": "avulso",
                    "owner_user_id": u_id
                }
        except Exception:
            pass

        return None

    def comparar(self, id1: str, id2: str) -> Dict[str, Any]:
        jogadores = self.jogador_service.listar_para_dict() or []

        j1 = self._obter_jogador(id1)
        j2 = self._obter_jogador(id2)

        if not j1 and jogadores:
            j1 = jogadores[0]
        if not j2 and jogadores:
            j2 = jogadores[1] if (len(jogadores) > 1 and j1 and str(jogadores[0].get('id')) == str(j1.get('id'))) else jogadores[0]

        if not j1 or not j2:
            return {
                "sucesso": False,
                "erro": "Um ou ambos os jogadores não foram encontrados.",
                "j1": j1,
                "j2": j2,
            }

        nome1 = j1.get("nome")
        nome2 = j2.get("nome")

        # Usar JogadorStatsService para garantir que todas as estatísticas (gols, vitórias, nota_média) venham de forma robusta e precisa
        stats1_raw = {}
        stats2_raw = {}
        try:
            from services.jogador_stats_service import JogadorStatsService
            jss = JogadorStatsService()
            if j1:
                stats1_raw = jss.obter_stats_jogador(
                    nome1,
                    jogador_id=j1.get("id"),
                    user_id=j1.get("owner_user_id") or j1.get("id")
                ) or {}
            if j2:
                stats2_raw = jss.obter_stats_jogador(
                    nome2,
                    jogador_id=j2.get("id"),
                    user_id=j2.get("owner_user_id") or j2.get("id")
                ) or {}
        except Exception as e:
            logger.warning(f"Erro ao obter estatísticas via JogadorStatsService no Duelo: {e}")

        # Obter ranking geral para fallback de extração
        dados_geral = self.votacao_service.ranking_jogadores_geral(limite=500)
        ranking_list = dados_geral.get("ranking", [])

        def _encontrar_no_ranking(j_dict, nome):
            if not j_dict and not nome:
                return {}
            j_id = str(j_dict.get("id") or "").strip().lower()
            j_owner = str(j_dict.get("owner_user_id") or "").strip().lower()
            n_lower = str(nome or "").strip().lower()

            for item in ranking_list:
                item_jid = str(item.get("jogador_id") or item.get("id") or "").strip().lower()
                item_uid = str(item.get("user_id") or item.get("owner_user_id") or "").strip().lower()
                if (j_id and (j_id == item_jid or j_id == item_uid)) or (j_owner and (j_owner == item_jid or j_owner == item_uid)):
                    return item

            for item in ranking_list:
                item_nome = str(item.get("jogador_nome") or item.get("nome") or "").strip().lower()
                if n_lower and item_nome == n_lower:
                    return item

            for item in ranking_list:
                item_nome = str(item.get("jogador_nome") or item.get("nome") or "").strip().lower()
                if n_lower and (n_lower in item_nome or item_nome in n_lower):
                    return item

            return {}

        rk1 = _encontrar_no_ranking(j1, nome1)
        rk2 = _encontrar_no_ranking(j2, nome2)

        gols1 = stats1_raw.get("gols") if (stats1_raw.get("gols") is not None and stats1_raw.get("gols") > 0) else rk1.get("gols", 0)
        gols2 = stats2_raw.get("gols") if (stats2_raw.get("gols") is not None and stats2_raw.get("gols") > 0) else rk2.get("gols", 0)

        vitorias1 = stats1_raw.get("vitorias") if stats1_raw.get("vitorias") is not None else rk1.get("vitorias", 0)
        vitorias2 = stats2_raw.get("vitorias") if stats2_raw.get("vitorias") is not None else rk2.get("vitorias", 0)

        jogos1 = stats1_raw.get("jogos") if stats1_raw.get("jogos") is not None else rk1.get("jogos", 0)
        jogos2 = stats2_raw.get("jogos") if stats2_raw.get("jogos") is not None else rk2.get("jogos", 0)

        nota1 = stats1_raw.get("nota_media") if stats1_raw.get("nota_media") is not None else rk1.get("nota_media", 0.0)
        nota2 = stats2_raw.get("nota_media") if stats2_raw.get("nota_media") is not None else rk2.get("nota_media", 0.0)

        stats1 = {
            "jogador_nome": nome1,
            "jogos": jogos1,
            "vitorias": vitorias1,
            "gols": gols1,
            "destaques": stats1_raw.get("destaques") or rk1.get("destaques", 0),
            "nota_media": float(nota1 or 0.0),
            "pontos": float(stats1_raw.get("pontos") or rk1.get("pontos", 0.0) or 0.0),
            "foto_url": j1.get("foto_url") or j1.get("foto") or stats1_raw.get("foto_url") or rk1.get("foto_url") or "",
            "foto": j1.get("foto_url") or j1.get("foto") or stats1_raw.get("foto_url") or rk1.get("foto_url") or "",
            "nivel": j1.get("nivel", 5.5),
            "posicao": j1.get("posicao", "linha"),
            "tipo": j1.get("tipo", "avulso"),
            "pct_vitorias": round((vitorias1 / jogos1 * 100), 1) if jogos1 else 0.0
        }

        stats2 = {
            "jogador_nome": nome2,
            "jogos": jogos2,
            "vitorias": vitorias2,
            "gols": gols2,
            "destaques": stats2_raw.get("destaques") or rk2.get("destaques", 0),
            "nota_media": float(nota2 or 0.0),
            "pontos": float(stats2_raw.get("pontos") or rk2.get("pontos", 0.0) or 0.0),
            "foto_url": j2.get("foto_url") or j2.get("foto") or stats2_raw.get("foto_url") or rk2.get("foto_url") or "",
            "foto": j2.get("foto_url") or j2.get("foto") or stats2_raw.get("foto_url") or rk2.get("foto_url") or "",
            "nivel": j2.get("nivel", 5.5),
            "posicao": j2.get("posicao", "linha"),
            "tipo": j2.get("tipo", "avulso"),
            "pct_vitorias": round((vitorias2 / jogos2 * 100), 1) if jogos2 else 0.0
        }

        # Análise de Retrospecto Direto (Partidas Encerradas)
        partidas = [p for p in self.votacao_service.listar() if p.get("status") == "encerrada"]

        jogos_juntos = 0
        vitorias_juntos = 0
        gols_juntos = 0

        jogos_contra = 0
        vitorias_j1 = 0
        vitorias_j2 = 0
        empates_confronto = 0

        for p in partidas:
            participantes = {part.get("jogador_nome"): part for part in p.get("participantes", []) if part.get("jogador_nome")}
            if nome1 in participantes and nome2 in participantes:
                p1 = participantes[nome1]
                p2 = participantes[nome2]
                time1 = p1.get("time_numero")
                time2 = p2.get("time_numero")

                resultado = p.get("resultado_partida") or {}
                res_time1 = self.votacao_service._resultado_por_time(resultado, time1) if resultado else "empate"

                if time1 == time2:
                    # Mesma equipe
                    jogos_juntos += 1
                    if res_time1 == "vitoria":
                        vitorias_juntos += 1
                    # Gols dos dois juntos na partida
                    detalhes = {item.get("nome"): item for item in resultado.get("jogadores_detalhes", []) or []}
                    gols_juntos += int((detalhes.get(nome1) or {}).get("gols", 0) or 0)
                    gols_juntos += int((detalhes.get(nome2) or {}).get("gols", 0) or 0)
                else:
                    # Times adversários
                    jogos_contra += 1
                    res_time2 = self.votacao_service._resultado_por_time(resultado, time2) if resultado else "empate"

                    if res_time1 == "vitoria":
                        vitorias_j1 += 1
                    elif res_time2 == "vitoria":
                        vitorias_j2 += 1
                    else:
                        empates_confronto += 1

        confronto_direto = {
            "jogos_juntos": jogos_juntos,
            "vitorias_juntos": vitorias_juntos,
            "pct_vitorias_juntos": round((vitorias_juntos / jogos_juntos * 100), 1) if jogos_juntos else 0.0,
            "gols_juntos": gols_juntos,
            "jogos_contra": jogos_contra,
            "vitorias_j1": vitorias_j1,
            "vitorias_j2": vitorias_j2,
            "empates_confronto": empates_confronto,
            "lider_confronto": nome1 if vitorias_j1 > vitorias_j2 else (nome2 if vitorias_j2 > vitorias_j1 else None)
        }

        return {
            "sucesso": True,
            "j1": stats1,
            "j2": stats2,
            "confronto_direto": confronto_direto
        }
