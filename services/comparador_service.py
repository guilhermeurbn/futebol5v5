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
        j1 = self._obter_jogador(id1)
        j2 = self._obter_jogador(id2)

        if not j1 or not j2:
            return {
                "sucesso": False,
                "erro": "Um ou ambos os jogadores não foram encontrados.",
                "j1": j1,
                "j2": j2,
            }

        nome1 = j1.get("nome")
        nome2 = j2.get("nome")

        # Obter ranking geral para extrair estatísticas consolidadas de cada um
        dados_geral = self.votacao_service.ranking_jogadores_geral(limite=500)
        ranking_list = dados_geral.get("ranking", [])

        stats1 = next((item for item in ranking_list if item.get("jogador_nome") == nome1), {
            "jogador_nome": nome1, "jogos": 0, "vitorias": 0, "gols": 0, "destaques": 0, "nota_media": 0.0, "pontos": 0.0
        })
        stats2 = next((item for item in ranking_list if item.get("jogador_nome") == nome2), {
            "jogador_nome": nome2, "jogos": 0, "vitorias": 0, "gols": 0, "destaques": 0, "nota_media": 0.0, "pontos": 0.0
        })

        # Adicionar dados de perfil
        stats1["nivel"] = j1.get("nivel", 5.5)
        stats1["posicao"] = j1.get("posicao", "linha")
        stats1["tipo"] = j1.get("tipo", "avulso")
        stats1["pct_vitorias"] = round((stats1["vitorias"] / stats1["jogos"] * 100), 1) if stats1.get("jogos") else 0.0

        stats2["nivel"] = j2.get("nivel", 5.5)
        stats2["posicao"] = j2.get("posicao", "linha")
        stats2["tipo"] = j2.get("tipo", "avulso")
        stats2["pct_vitorias"] = round((stats2["vitorias"] / stats2["jogos"] * 100), 1) if stats2.get("jogos") else 0.0

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
