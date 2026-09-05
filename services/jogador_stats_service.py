"""
Serviço de Estatísticas Detalhadas de Jogador
Rastreia gols, assistências, cartões, vitórias e muito mais de cada jogador
"""
import json
import os
import time
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from services.db import load_json_data, save_json_data


class JogadorStatsService:
    """Serviço para calcular estatísticas detalhadas por jogador"""

    _cache_stats: Dict[str, Dict] = {}
    _cache_ttl_seconds = 60
    _cache_partidas_combinadas: Optional[List[dict]] = None
    _cache_partidas_ts: float = 0.0
    _cached_usuarios_ext: Optional[List[dict]] = None
    _cached_jogadores_ext: Optional[List[dict]] = None
    _cached_aux_ts: float = 0.0
    
    def __init__(self, partidas_arquivo: str = "data/partidas.json", historico_arquivo: str = "data/historico.json"):
        """
        Inicializa o serviço
        
        Args:
            partidas_arquivo: Caminho do arquivo de partidas
            historico_arquivo: Caminho do arquivo de histórico
        """
        self.partidas_arquivo = partidas_arquivo
        self.historico_arquivo = historico_arquivo

    @classmethod
    def invalidar_cache_stats(cls) -> None:
        """Limpa cache em memória das estatísticas por jogador."""
        cls._cache_stats.clear()
        cls._cache_partidas_combinadas = None
        cls._cache_partidas_ts = 0.0
        cls._cached_usuarios_ext = None
        cls._cached_jogadores_ext = None
        cls._cached_aux_ts = 0.0

    def _obter_auxiliares_extracao(self):
        now = time.time()
        if (
            JogadorStatsService._cached_usuarios_ext is not None
            and JogadorStatsService._cached_jogadores_ext is not None
            and (now - JogadorStatsService._cached_aux_ts) < 10
        ):
            return JogadorStatsService._cached_usuarios_ext, JogadorStatsService._cached_jogadores_ext

        from services.auth_service import AuthService
        usuarios = AuthService()._carregar()
        jogadores = load_json_data("jogadores", [])
        JogadorStatsService._cached_usuarios_ext = usuarios
        JogadorStatsService._cached_jogadores_ext = jogadores
        JogadorStatsService._cached_aux_ts = now
        return usuarios, jogadores

    def _obter_stats_em_cache(self, chave: str) -> Optional[Dict]:
        item = self._cache_stats.get(chave)
        if not item:
            return None
        if time.time() - item.get("ts", 0) > self._cache_ttl_seconds:
            self._cache_stats.pop(chave, None)
            return None
        return item.get("data")

    def _salvar_stats_em_cache(self, chave: str, data: Dict) -> None:
        self._cache_stats[chave] = {
            "ts": time.time(),
            "data": data,
        }

    def _chave_cache_stats(self, nome_jogador: str, jogador_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Monta uma chave que evita reaproveitar stats entre fontes diferentes."""
        chave_id = user_id or jogador_id or self._normalizar_nome(nome_jogador)
        return f"JogadorStatsService:{chave_id}"
    
    def _carregar_partidas(self) -> List[dict]:
        """Carrega dados de partidas combinando partidas e votacoes_partidas"""
        now = time.time()
        if (
            JogadorStatsService._cache_partidas_combinadas is not None
            and (now - JogadorStatsService._cache_partidas_ts) < 10
        ):
            return JogadorStatsService._cache_partidas_combinadas

        partidas = load_json_data("partidas", [])
        votacoes = load_json_data("votacoes_partidas", {})

        votacoes_list = (
            votacoes.get("partidas", [])
            if isinstance(votacoes, dict)
            else (votacoes if isinstance(votacoes, list) else [])
        )

        v_by_id = {}
        v_by_sorteio = {}
        for vp in votacoes_list:
            if isinstance(vp, dict):
                if vp.get("id"):
                    v_by_id[str(vp["id"])] = vp
                if vp.get("sorteio_id"):
                    v_by_sorteio[str(vp["sorteio_id"])] = vp

        partidas_dict = {}
        used_votacao_ids = set()

        for p in partidas:
            if isinstance(p, dict):
                pid = str(p.get("id") or "")
                sid = str(p.get("sorteio_id") or "")
                if pid or sid:
                    p_copy = dict(p)
                    # Priorizar id exato, depois sorteio_id
                    vp = None
                    if pid and pid in v_by_id:
                        vp = v_by_id[pid]
                    elif sid and sid in v_by_sorteio:
                        vp = v_by_sorteio[sid]
                    elif pid and pid in v_by_sorteio:
                        vp = v_by_sorteio[pid]
                    elif sid and sid in v_by_id:
                        vp = v_by_id[sid]

                    if vp:
                        used_votacao_ids.add(str(vp.get("id")))
                        data_val = p_copy.get("data") or vp.get("data") or vp.get("encerrado_em") or vp.get("aberta_em") or ""
                        p_copy["data"] = data_val
                        if not p_copy.get("jogadores_detalhes") and vp.get("participantes"):
                            p_copy["participantes"] = vp.get("participantes")
                        if not p_copy.get("resultado_resumido") and vp.get("resultado_resumido"):
                            p_copy["resultado_resumido"] = vp.get("resultado_resumido")
                        if vp.get("ranking"):
                            p_copy["ranking"] = vp.get("ranking")
                    partidas_dict[pid or sid] = p_copy

        for vp in votacoes_list:
            if isinstance(vp, dict):
                vpid = str(vp.get("id") or "")
                vsid = str(vp.get("sorteio_id") or "")
                if not vpid and not vsid:
                    continue
                if vpid not in used_votacao_ids:
                    data_val = vp.get("data") or vp.get("encerrado_em") or vp.get("aberta_em") or ""
                    vp_copy = dict(vp)
                    vp_copy["data"] = data_val
                    key = vpid or vsid
                    if key not in partidas_dict:
                        partidas_dict[key] = vp_copy

        res = list(partidas_dict.values())
        JogadorStatsService._cache_partidas_combinadas = res
        JogadorStatsService._cache_partidas_ts = now
        return res
    
    def _carregar_historico(self) -> List[dict]:
        """Carrega dados do histórico de sorteios"""
        return load_json_data("historico", [])

    def _stats_vazio(self, nome_jogador: str) -> Dict:
        """Retorna estrutura base de estatísticas com compatibilidade retroativa."""
        return {
            "nome": nome_jogador,
            "total_partidas": 0,
            "gols": 0,
            "assistencias": 0,
            "cartoes_amarelos": 0,
            "cartoes_vermelhos": 0,
            "vitórias": 0,
            "vitorias": 0,
            "derrotas": 0,
            "empates": 0,
            "win_rate": 0.0,
            "win_rate_valido": True,
            "gols_por_partida": 0.0,
            "assistencias_por_partida": 0.0,
            "maior_artilheiro": False,
            "melhor_artilheiro_partida": 0,
            "partidas_sem_gols": 0,
            "historico_partidas": [],
            "efficiency": {
                "participacoes_gol": 0,
                "participacoes_por_partida": 0.0,
                "taxa_partidas_com_participacao": 0.0,
                "peso_gols_assistencias": 0.0,
            },
            "discipline": {
                "cartoes_total": 0,
                "cartoes_por_partida": 0.0,
                "indice_disciplina": 100.0,
                "partidas_sem_cartao_aprox": 0,
            },
            "ultimos_resultados": {
                "limite": 5,
                "forma": [],
                "sequencia": "",
                "pontos": 0,
                "partidas": [],
            },
            "mini_dashboard": {
                "kpis": {
                    "win_rate": 0.0,
                    "participacoes_por_partida": 0.0,
                    "indice_disciplina": 100.0,
                },
                "series_ultimos_5": [],
            },
            "planilha_metricas": [],
        }

    def _normalizar_nome(self, nome: str) -> str:
        """Normaliza nomes para comparação case-insensitive e sem acentos."""
        if not isinstance(nome, str):
            return ""
        texto = unicodedata.normalize("NFKD", nome.strip().casefold())
        return "".join(c for c in texto if not unicodedata.combining(c))

    def _resultado_para_pontos(self, resultado: str) -> int:
        if resultado == "vitória":
            return 3
        if resultado == "empate":
            return 1
        return 0

    def _build_recent_form(self, historico_partidas: List[Dict], limite: int = 5) -> Dict:
        ultimas = (historico_partidas or [])[:limite]
        sigla = {"vitória": "V", "empate": "E", "derrota": "D"}
        forma = [sigla.get(p.get("resultado"), "E") for p in ultimas]
        pontos = sum(self._resultado_para_pontos(p.get("resultado", "empate")) for p in ultimas)

        return {
            "limite": limite,
            "forma": forma,
            "sequencia": "".join(forma),
            "pontos": pontos,
            "partidas": ultimas,
        }

    def _build_efficiency(self, stats: Dict) -> Dict:
        total = int(stats.get("total_partidas", 0) or 0)
        gols = int(stats.get("gols", 0) or 0)
        assist = int(stats.get("assistencias", 0) or 0)
        participacoes = gols + assist

        partidas_com_participacao = 0
        for partida in stats.get("historico_partidas", []):
            if (partida.get("gols", 0) or 0) + (partida.get("assistencias", 0) or 0) > 0:
                partidas_com_participacao += 1

        return {
            "participacoes_gol": participacoes,
            "participacoes_por_partida": round(participacoes / total, 2) if total > 0 else 0.0,
            "taxa_partidas_com_participacao": round((partidas_com_participacao / total) * 100, 1) if total > 0 else 0.0,
            "peso_gols_assistencias": round(((gols * 1.0) + (assist * 0.7)) / total, 2) if total > 0 else 0.0,
        }

    def _build_discipline(self, stats: Dict) -> Dict:
        total = int(stats.get("total_partidas", 0) or 0)
        amarelos = int(stats.get("cartoes_amarelos", 0) or 0)
        vermelhos = int(stats.get("cartoes_vermelhos", 0) or 0)
        punicao = (amarelos * 1) + (vermelhos * 3)

        indice = 100.0
        if total > 0:
            indice = max(0.0, round(100 - ((punicao / total) * 12), 1))

        return {
            "cartoes_total": amarelos + vermelhos,
            "cartoes_por_partida": round((amarelos + vermelhos) / total, 2) if total > 0 else 0.0,
            "indice_disciplina": indice,
            "partidas_sem_cartao_aprox": max(0, total - (amarelos + vermelhos)),
        }

    def _build_mini_dashboard(self, stats: Dict) -> Dict:
        ultimos = stats.get("ultimos_resultados", {}).get("partidas", [])
        return {
            "kpis": {
                "win_rate": stats.get("win_rate", 0.0),
                "participacoes_por_partida": stats.get("efficiency", {}).get("participacoes_por_partida", 0.0),
                "indice_disciplina": stats.get("discipline", {}).get("indice_disciplina", 100.0),
                "pontos_ultimos_5": stats.get("ultimos_resultados", {}).get("pontos", 0),
            },
            "series_ultimos_5": [
                {
                    "data": p.get("data"),
                    "resultado": p.get("resultado"),
                    "gols": p.get("gols", 0),
                    "assistencias": p.get("assistencias", 0),
                    "pontos": self._resultado_para_pontos(p.get("resultado", "empate")),
                }
                for p in ultimos
            ],
        }

    def _build_planilha_metricas(self, stats: Dict) -> List[Dict]:
        """Dados tabulares prontos para exportação CSV em formato de planilha."""
        linhas = []
        for partida in stats.get("historico_partidas", []):
            resultado = partida.get("resultado", "empate")
            linhas.append({
                "data": (partida.get("data") or "")[:10],
                "partida_id": partida.get("partida_id"),
                "time": partida.get("time_numero"),
                "resultado": resultado,
                "pontos": self._resultado_para_pontos(resultado),
                "gols": partida.get("gols", 0),
                "assistencias": partida.get("assistencias", 0),
                "cartoes_amarelos": partida.get("cartoes_amarelos", 0),
                "cartoes_vermelhos": partida.get("cartoes_vermelhos", 0),
            })
        return linhas

    def _validar_win_rate(self, stats: Dict) -> bool:
        """Valida consistência do win rate calculado para evitar regressões silenciosas."""
        total = int(stats.get("total_partidas", 0) or 0)
        if total <= 0:
            return float(stats.get("win_rate", 0.0) or 0.0) == 0.0
        esperado = round((int(stats.get("vitórias", 0) or 0) / total) * 100, 1)
        return float(stats.get("win_rate", 0.0) or 0.0) == esperado

    def _resultado_por_time(self, partida: dict, time_numero: Optional[int]) -> str:
        """Calcula resultado (vitória/empate/derrota) para um time em uma partida."""
        if not time_numero:
            return "empate"

        # 1. Checar gols_times (placar real da partida)
        gols_times = partida.get("gols_times") or (partida.get("resultado_partida") or {}).get("gols_times", []) or []
        indice = int(time_numero) - 1
        if 0 <= indice < len(gols_times):
            meu_placar = int(gols_times[indice] or 0)
            outros_gols = [int(g or 0) for idx, g in enumerate(gols_times) if idx != indice]
            if outros_gols:
                maior_outro = max(outros_gols)
                if meu_placar > maior_outro:
                    return "vitória"
                elif meu_placar < maior_outro:
                    return "derrota"
                elif meu_placar == maior_outro and len(set(gols_times)) > 1:
                    time_vencedor = partida.get("time_vencedor") or (partida.get("resultado_partida") or {}).get("time_vencedor")
                    if time_vencedor is not None:
                        if int(time_numero) == int(time_vencedor):
                            return "vitória"
                        else:
                            return "derrota"

        # 2. Checar time_vencedor explícito
        time_vencedor = partida.get("time_vencedor") or (partida.get("resultado_partida") or {}).get("time_vencedor")
        if time_vencedor is not None and int(time_vencedor) != 0:
            if int(time_numero) == int(time_vencedor):
                return "vitória"
            else:
                return "derrota"

        # 3. Checar times_desempenho
        for item in partida.get("times_desempenho", []) or []:
            if int(item.get("time_numero", 0) or 0) != int(time_numero):
                continue
            v = int(item.get("vitorias", 0) or 0)
            d = int(item.get("derrotas", 0) or 0)
            e = int(item.get("empates", 0) or 0)
            if v > d and v > 0:
                return "vitória"
            if d > v:
                return "derrota"
            if e > 0:
                return "empate"

        # 4. Checar resultado_resumido como fallback
        resumo = partida.get("resultado_resumido") or []
        if resumo and isinstance(resumo, list) and len(resumo) >= 2:
            meu_gols = None
            outro_gols = None
            for item in resumo:
                if isinstance(item, dict):
                    if int(item.get("time_numero", 0) or 0) == int(time_numero):
                        meu_gols = int(item.get("gols", 0) or 0)
                    else:
                        outro_gols = max(outro_gols or 0, int(item.get("gols", 0) or 0))
            if meu_gols is not None and outro_gols is not None:
                if meu_gols > outro_gols:
                    return "vitória"
                elif meu_gols < outro_gols:
                    return "derrota"

        return "empate"

    def obter_stats_jogador(self, nome_jogador: str, jogador_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict:
        """
        Obtém estatísticas completas de um jogador por nome, jogador_id ou user_id
        """
        try:
            chave_cache = self._chave_cache_stats(nome_jogador, jogador_id=jogador_id, user_id=user_id)
            cache_hit = self._obter_stats_em_cache(chave_cache)
            if cache_hit is not None:
                return cache_hit

            partidas = self._carregar_partidas()
            historico = self._carregar_historico()
            stats = self._stats_vazio(nome_jogador)
            
            if not partidas:
                return stats
            
            historico_dict = {h.get('id'): h for h in historico}
            gols_todos = defaultdict(int)
            
            # Processar cada partida
            for partida in partidas:
                for detalhe_global in partida.get("jogadores_detalhes", []) or []:
                    nome_global = detalhe_global.get("nome")
                    if nome_global:
                        gols_todos[nome_global] += int(detalhe_global.get("gols", 0) or 0)

                sorteio_id = partida.get('sorteio_id')
                sorteio = historico_dict.get(sorteio_id, {})
                
                # Obter detalhes do jogador na partida
                detalhes = self._extrair_detalhes_jogador(partida, nome_jogador, sorteio, jogador_id=jogador_id, user_id=user_id)
                
                if detalhes:
                    stats["total_partidas"] += 1
                    stats["gols"] += detalhes.get("gols", 0)
                    stats["assistencias"] += detalhes.get("assistencias", 0)
                    stats["cartoes_amarelos"] += detalhes.get("cartoes_amarelos", 0)
                    stats["cartoes_vermelhos"] += detalhes.get("cartoes_vermelhos", 0)
                    
                    # Contar resultado
                    resultado = detalhes.get("resultado", "empate")
                    if resultado == "vitória":
                        stats["vitórias"] += 1
                    elif resultado == "derrota":
                        stats["derrotas"] += 1
                    else:
                        stats["empates"] += 1
                    
                    # Rastrear melhor artilheiro em uma partida
                    gols_partida = detalhes.get("gols", 0)
                    if gols_partida > stats["melhor_artilheiro_partida"]:
                        stats["melhor_artilheiro_partida"] = gols_partida
                    
                    # Contar partidas sem gols
                    if detalhes.get("gols", 0) == 0:
                        stats["partidas_sem_gols"] += 1
                    
                    gols_times_val = partida.get("gols_times") or (partida.get("resultado_partida") or {}).get("gols_times", [])

                    # Adicionar ao histórico de partidas
                    stats["historico_partidas"].append({
                        "partida_id": partida.get('id'),
                        "sorteio_id": sorteio_id,
                        "data": partida.get('data') or partida.get('encerrado_em') or partida.get('aberta_em') or '',
                        "gols": detalhes.get("gols", 0),
                        "assistencias": detalhes.get("assistencias", 0),
                        "cartoes_amarelos": detalhes.get("cartoes_amarelos", 0),
                        "cartoes_vermelhos": detalhes.get("cartoes_vermelhos", 0),
                        "resultado": resultado,
                        "time_numero": detalhes.get("time_numero"),
                        "gols_times": gols_times_val,
                        "posicao": detalhes.get("posicao"),
                        "nota_media": detalhes.get("nota_media", 0.0),
                        "nota_partida": detalhes.get("nota_partida", 0.0)
                    })
            
            # Desduplicar partidas geradas por testes/substituições no mesmo dia
            stats["historico_partidas"] = self._desduplicar_historico_partidas(stats["historico_partidas"])

            # Recalcular métricas após desduplicação
            stats["total_partidas"] = len(stats["historico_partidas"])
            stats["gols"] = sum(p.get("gols", 0) for p in stats["historico_partidas"])
            stats["assistencias"] = sum(p.get("assistencias", 0) for p in stats["historico_partidas"])
            stats["cartoes_amarelos"] = sum(p.get("cartoes_amarelos", 0) for p in stats["historico_partidas"])
            stats["cartoes_vermelhos"] = sum(p.get("cartoes_vermelhos", 0) for p in stats["historico_partidas"])
            stats["vitórias"] = sum(1 for p in stats["historico_partidas"] if p.get("resultado") == "vitória")
            stats["derrotas"] = sum(1 for p in stats["historico_partidas"] if p.get("resultado") == "derrota")
            stats["empates"] = sum(1 for p in stats["historico_partidas"] if p.get("resultado") == "empate")
            stats["vitorias"] = stats["vitórias"]
            stats["melhor_artilheiro_partida"] = max([p.get("gols", 0) for p in stats["historico_partidas"]], default=0)
            stats["partidas_sem_gols"] = sum(1 for p in stats["historico_partidas"] if p.get("gols", 0) == 0)

            # Calcular taxas
            if stats["total_partidas"] > 0:
                stats["win_rate"] = round((stats["vitórias"] / stats["total_partidas"]) * 100, 1)
                stats["gols_por_partida"] = round(stats["gols"] / stats["total_partidas"], 2)
                stats["assistencias_por_partida"] = round(stats["assistencias"] / stats["total_partidas"], 2)
            else:
                stats["win_rate"] = 0.0
                stats["gols_por_partida"] = 0.0
                stats["assistencias_por_partida"] = 0.0

            # Verificar se é o maior artilheiro (por total de gols)
            if gols_todos and max(gols_todos.values(), default=0) == stats["gols"] and stats["gols"] > 0:
                stats["maior_artilheiro"] = True

            # Dashboard e dados para planilha/exportação
            stats["ultimos_resultados"] = self._build_recent_form(stats["historico_partidas"], limite=5)
            stats["efficiency"] = self._build_efficiency(stats)
            stats["discipline"] = self._build_discipline(stats)
            stats["mini_dashboard"] = self._build_mini_dashboard(stats)
            stats["planilha_metricas"] = self._build_planilha_metricas(stats)
            stats["win_rate_valido"] = self._validar_win_rate(stats)
            self._salvar_stats_em_cache(chave_cache, stats)

            return stats
        except Exception as e:
            import sys
            print(f"Erro ao calcular stats para {nome_jogador}: {str(e)}", file=sys.stderr)
            return self._stats_vazio(nome_jogador)

    def _desduplicar_historico_partidas(self, historico_partidas: List[Dict]) -> List[Dict]:
        """
        Remove partidas duplicadas/rascunho geradas no mesmo dia durante o setup de substituições,
        e desconsidera cascas de partidas de teste sem notas, sem votos e sem estatísticas reais.
        """
        if not historico_partidas:
            return []

        def _is_partida_valida(x: dict) -> bool:
            nota = float(x.get("nota_media", 0) or x.get("nota_partida", 0) or x.get("nota", 0) or 0)
            gols = int(x.get("gols", 0) or 0)
            assist = int(x.get("assistencias", 0) or 0)
            has_voto = x.get("tem_voto", False) or x.get("votos_contabilizados", False)
            has_resultado = bool(x.get("resultado") or x.get("times_desempenho"))
            return nota > 0 or gols > 0 or assist > 0 or has_voto or has_resultado

        tem_partidas_reais = any(_is_partida_valida(x) for x in historico_partidas)

        partidas_filtradas = []
        for p in historico_partidas:
            if tem_partidas_reais:
                if _is_partida_valida(p):
                    partidas_filtradas.append(p)
            else:
                partidas_filtradas.append(p)

        por_data = {}
        for p in partidas_filtradas:
            dt = str(p.get("data") or "")[:10]
            por_data.setdefault(dt, []).append(p)

        resultado_final = []
        for dt, items in por_data.items():
            com_avaliacao = [x for x in items if _is_partida_valida(x)]
            if com_avaliacao:
                resultado_final.extend(com_avaliacao)
            else:
                items_ordenados = sorted(items, key=lambda x: str(x.get("data") or ""), reverse=True)
                resultado_final.append(items_ordenados[0])

        resultado_final.sort(key=lambda x: str(x.get("data") or ""), reverse=True)
        return resultado_final
    
    def _extrair_detalhes_jogador(self, partida: dict, nome_jogador: str, sorteio: dict, jogador_id: Optional[str] = None, user_id: Optional[str] = None) -> Optional[dict]:
        """
        Extrai detalhes de um jogador específico em uma partida usando ID único (jogador_id / user_id)
        com fallback para nome.
        """
        nome_normalizado = self._normalizar_nome(nome_jogador)
        nota_media_ranking = 0.0

        target_user_ids = set()
        target_jogador_ids = set()
        player_aliases = set()
        if nome_normalizado:
            player_aliases.add(nome_normalizado)
        if user_id:
            target_user_ids.add(str(user_id))
        if jogador_id:
            target_jogador_ids.add(str(jogador_id))

        try:
            usuarios, jogadores = self._obter_auxiliares_extracao()

            u_target = None
            if user_id:
                u_target = next((u for u in usuarios if str(u.get("id")) == str(user_id)), None)
            if not u_target and jogador_id:
                j = next((j for j in jogadores if isinstance(j, dict) and str(j.get("id")) == str(jogador_id)), None)
                if j:
                    j_uid = str(j.get("owner_user_id") or j.get("user_id") or "")
                    if j_uid:
                        u_target = next((u for u in usuarios if str(u.get("id")) == j_uid), None)

            if not u_target and nome_normalizado:
                u_target = next((u for u in usuarios if self._normalizar_nome(u.get("nome", "")) == nome_normalizado or self._normalizar_nome(u.get("username", "")) == nome_normalizado), None)
                if not u_target:
                    j_target = next((j for j in jogadores if isinstance(j, dict) and self._normalizar_nome(j.get("nome", "")) == nome_normalizado), None)
                    if j_target:
                        j_uid = str(j_target.get("owner_user_id") or j_target.get("user_id") or "")
                        if j_uid:
                            u_target = next((u for u in usuarios if str(u.get("id")) == j_uid), None)

            if u_target:
                uid_str = str(u_target.get("id"))
                target_user_ids.add(uid_str)
                if u_target.get("nome"):
                    player_aliases.add(self._normalizar_nome(u_target["nome"]))
                if u_target.get("username"):
                    player_aliases.add(self._normalizar_nome(u_target["username"]))

                for j in jogadores:
                    if isinstance(j, dict):
                        j_uid = str(j.get("owner_user_id") or j.get("user_id") or "")
                        j_id = str(j.get("id") or "")
                        if (j_uid and j_uid == uid_str) or (jogador_id and j_id == str(jogador_id)):
                            if j_id:
                                target_jogador_ids.add(j_id)
                            if j.get("nome"):
                                player_aliases.add(self._normalizar_nome(j["nome"]))
            elif jogador_id:
                target_jogador_ids.add(str(jogador_id))
                for j in jogadores:
                    if isinstance(j, dict) and str(j.get("id")) == str(jogador_id):
                        if j.get("nome"):
                            player_aliases.add(self._normalizar_nome(j["nome"]))

            gui_main_id = "18c652b0-330e-4e0d-9c5d-eb9a27b889a2"
            gui_old_id = "09142ace-266e-4d33-96db-8b92ed6144c8"
            if gui_main_id in target_user_ids or gui_old_id in target_user_ids:
                target_user_ids.update({gui_main_id, gui_old_id})
                player_aliases.update({
                    self._normalizar_nome("guilherme"),
                    self._normalizar_nome("guilherme urbano"),
                    self._normalizar_nome("guilherme_urbano")
                })

        except Exception:
            pass

        def _is_match(item_nome: str, item_user_id: Optional[str], item_jogador_id: Optional[str] = None) -> bool:
            if target_user_ids and item_user_id and str(item_user_id) in target_user_ids:
                return True
            if target_jogador_ids and item_jogador_id and str(item_jogador_id) in target_jogador_ids:
                return True
            n = self._normalizar_nome(item_nome)
            if not n:
                return False
            return any(alias == n for alias in player_aliases)

        ranking = partida.get("ranking") or {}
        if isinstance(ranking, dict):
            for rj in ranking.get("ranking_jogadores", []) or []:
                rj_nome = rj.get("jogador_nome", "")
                rj_uid = rj.get("user_id") or rj.get("owner_user_id")
                rj_jid = rj.get("jogador_id") or rj.get("id")
                if _is_match(rj_nome, rj_uid, rj_jid):
                    n_val = float(rj.get("nota_media", 0) or 0)
                    if n_val > 0:
                        nota_media_ranking = n_val
                        break

        # Fallback: se nota_media_ranking não foi encontrada na partida, buscar em votacoes_partidas
        if nota_media_ranking == 0.0:
            try:
                vot_dados = load_json_data("votacoes_partidas", {})
                vot_list = vot_dados.get("partidas", []) if isinstance(vot_dados, dict) else []
                pid = str(partida.get("id") or "")
                sid = str(partida.get("sorteio_id") or "")
                for vp in vot_list:
                    if not isinstance(vp, dict):
                        continue
                    v_pid = str(vp.get("id") or "")
                    v_sid = str(vp.get("sorteio_id") or "")
                    if (pid and (v_pid == pid or v_sid == pid)) or (sid and (v_sid == sid or v_pid == sid)):
                        v_rk = vp.get("ranking") or {}
                        if isinstance(v_rk, dict):
                            for rj in v_rk.get("ranking_jogadores", []) or []:
                                rj_nome = rj.get("jogador_nome", "")
                                rj_uid = rj.get("user_id") or rj.get("owner_user_id")
                                rj_jid = rj.get("jogador_id") or rj.get("id")
                                if _is_match(rj_nome, rj_uid, rj_jid):
                                    n_val = float(rj.get("nota_media", 0) or 0)
                                    if n_val > 0:
                                        nota_media_ranking = n_val
                                        break
                    if nota_media_ranking > 0:
                        break
            except Exception:
                pass

        jogadores_detalhes = partida.get("jogadores_detalhes", [])
        
        # Helper para resolver gols em participantes / votos
        def _extrair_gols_votacao(p_uid: Optional[str], p_jid: Optional[str], p_nome: str) -> int:
            for part in partida.get("participantes", []):
                part_nome = part.get("jogador_nome") or part.get("nome_usuario") or part.get("username") or ""
                part_uid = part.get("user_id") or part.get("owner_user_id")
                part_jid = part.get("jogador_id") or part.get("id")
                if _is_match(part_nome, part_uid, part_jid):
                    g_val = int(part.get("gols", 0) or 0)
                    if g_val > 0:
                        return g_val
            uids = target_user_ids or ({str(p_uid)} if p_uid else set())
            for v in partida.get("votos", []):
                v_uid = str(v.get("user_id") or "").strip()
                if v_uid and (v_uid in uids or (p_uid and v_uid == str(p_uid).strip())):
                    g_val = int(v.get("gols_marcados", 0) or 0)
                    if g_val > 0:
                        return g_val
            return 0

        # 1. Procurar em jogadores_detalhes
        for detalhe in jogadores_detalhes:
            d_nome = detalhe.get("nome", "")
            d_uid = detalhe.get("user_id") or detalhe.get("owner_user_id")
            d_jid = detalhe.get("jogador_id") or detalhe.get("id")
            if _is_match(d_nome, d_uid, d_jid):
                time_numero = detalhe.get("time_numero")
                resultado = self._resultado_por_time(partida, time_numero)
                dados = dict(detalhe)
                dados["resultado"] = resultado
                nota_val = nota_media_ranking if nota_media_ranking > 0 else float(dados.get("nota_media") or dados.get("nota_partida") or dados.get("nota") or 0.0)
                dados["nota_media"] = nota_val
                dados["nota_partida"] = nota_val
                if int(dados.get("gols", 0) or 0) == 0:
                    gols_v = _extrair_gols_votacao(d_uid, d_jid, d_nome)
                    if gols_v > 0:
                        dados["gols"] = gols_v
                return dados

        # 2. Procurar em participantes (partidas de votação)
        participantes = partida.get("participantes", [])
        for part in participantes:
            p_nome = part.get("jogador_nome") or part.get("nome_usuario") or part.get("username") or ""
            p_uid = part.get("user_id") or part.get("owner_user_id")
            p_jid = part.get("jogador_id") or part.get("id")
            if _is_match(p_nome, p_uid, p_jid):
                time_numero = part.get("time_numero")
                resultado = self._resultado_por_time(partida, time_numero)
                nota_val = nota_media_ranking if nota_media_ranking > 0 else float(part.get("nota_media") or part.get("nota_partida") or part.get("nota") or 0.0)
                gols_v = _extrair_gols_votacao(p_uid, p_jid, p_nome)
                return {
                    "gols": gols_v,
                    "assistencias": int(part.get("assistencias", 0) or 0),
                    "cartoes_amarelos": int(part.get("cartoes_amarelos", 0) or 0),
                    "cartoes_vermelhos": int(part.get("cartoes_vermelhos", 0) or 0),
                    "resultado": resultado,
                    "time_numero": time_numero,
                    "posicao": part.get("posicao", "linha"),
                    "nota_media": nota_val,
                    "nota_partida": nota_val
                }
        
        # 3. Procurar no sorteio (historico)
        if sorteio:
            if sorteio.get('rascunho') or not sorteio.get('oficial', True):
                return None
            times = sorteio.get('times', [])
            for time_idx, time_data in enumerate(times):
                jogadores = time_data.get('jogadores', [])
                for jogador in jogadores:
                    j_nome = jogador.get('nome', '')
                    j_uid = jogador.get('owner_user_id') or jogador.get('user_id')
                    j_jid = jogador.get('jogador_id') or jogador.get('id')
                    if _is_match(j_nome, j_uid, j_jid):
                        time_numero = time_idx + 1
                        resultado = self._resultado_por_time(partida, time_numero)
                        nota_val = nota_media_ranking if nota_media_ranking > 0 else float(jogador.get("nota") or 0.0)
                        gols_v = _extrair_gols_votacao(j_uid, j_jid, j_nome)
                        return {
                            "gols": gols_v,
                            "assistencias": 0,
                            "cartoes_amarelos": 0,
                            "cartoes_vermelhos": 0,
                            "resultado": resultado,
                            "time_numero": time_numero,
                            "posicao": jogador.get("posicao"),
                            "nota_media": nota_val,
                            "nota_partida": nota_val
                        }
        
        return None
    
    def _calcular_gols_todos_jogadores(self) -> Dict[str, int]:
        """Calcula total de gols de todos os jogadores"""
        partidas = self._carregar_partidas()
        gols_por_jogador = defaultdict(int)
        
        for partida in partidas:
            jogadores_detalhes = partida.get("jogadores_detalhes", [])
            for detalhe in jogadores_detalhes:
                nome = detalhe.get("nome")
                gols = detalhe.get("gols", 0)
                gols_por_jogador[nome] += gols
        
        return dict(gols_por_jogador)
    
    def obter_historico_jogador(self, nome_jogador: str, limite: int = 10) -> List[Dict]:
        """
        Obtém histórico de partidas de um jogador (mais recentes primeiro)
        
        Args:
            nome_jogador: Nome do jogador
            limite: Número máximo de partidas a retornar
            
        Returns:
            Lista com histórico das últimas partidas
        """
        stats = self.obter_stats_jogador(nome_jogador)
        return stats.get("historico_partidas", [])[:limite]
    
    def obter_ranking_artilheiros(self, limite: int = 10) -> List[Dict]:
        """
        Obtém ranking dos maiores artilheiros
        
        Args:
            limite: Número máximo de jogadores a retornar
            
        Returns:
            Lista com ranking de artilheiros
        """
        partidas = self._carregar_partidas()
        gols_por_jogador = defaultdict(lambda: {"gols": 0, "partidas": 0})
        
        for partida in partidas:
            jogadores_detalhes = partida.get("jogadores_detalhes", [])
            for detalhe in jogadores_detalhes:
                nome = detalhe.get("nome")
                gols = detalhe.get("gols", 0)
                gols_por_jogador[nome]["gols"] += gols
                gols_por_jogador[nome]["partidas"] += 1
        
        # Converter para lista e calcular média
        ranking = []
        for nome, dados in gols_por_jogador.items():
            ranking.append({
                "nome": nome,
                "gols": dados["gols"],
                "partidas": dados["partidas"],
                "media_gols": round(dados["gols"] / dados["partidas"], 2) if dados["partidas"] > 0 else 0
            })
        
        # Ordenar por gols (decrescente)
        ranking.sort(key=lambda x: x["gols"], reverse=True)
        return ranking[:limite]
    
    def obter_ranking_assistencias(self, limite: int = 10) -> List[Dict]:
        """
        Obtém ranking de maiores assistentes
        
        Args:
            limite: Número máximo de jogadores a retornar
            
        Returns:
            Lista com ranking de assistências
        """
        partidas = self._carregar_partidas()
        assist_por_jogador = defaultdict(lambda: {"assistencias": 0, "partidas": 0})
        
        for partida in partidas:
            jogadores_detalhes = partida.get("jogadores_detalhes", [])
            for detalhe in jogadores_detalhes:
                nome = detalhe.get("nome")
                assist = detalhe.get("assistencias", 0)
                assist_por_jogador[nome]["assistencias"] += assist
                assist_por_jogador[nome]["partidas"] += 1
        
        # Converter para lista
        ranking = []
        for nome, dados in assist_por_jogador.items():
            ranking.append({
                "nome": nome,
                "assistencias": dados["assistencias"],
                "partidas": dados["partidas"],
                "media_assist": round(dados["assistencias"] / dados["partidas"], 2) if dados["partidas"] > 0 else 0
            })
        
        # Ordenar por assistências (decrescente)
        ranking.sort(key=lambda x: x["assistencias"], reverse=True)
        return ranking[:limite]
    
    def registrar_desempenho_jogador(self, partida_id: int, nome_jogador: str, 
                                     gols: int = 0, assistencias: int = 0,
                                     cartoes_amarelos: int = 0, cartoes_vermelhos: int = 0,
                                     time_numero: int = 1, posicao: str = "linha") -> bool:
        """
        Registra o desempenho individual de um jogador em uma partida
        
        Args:
            partida_id: ID da partida
            nome_jogador: Nome do jogador
            gols: Quantidade de gols
            assistencias: Quantidade de assistências
            cartoes_amarelos: Quantidade de cartões amarelos
            cartoes_vermelhos: Quantidade de cartões vermelhos
            time_numero: Número do time (1, 2, 3, etc)
            posicao: Posição do jogador (linha ou goleiro)
            
        Returns:
            True se registrado com sucesso, False caso contrário
        """
        partidas = self._carregar_partidas()
        
        # Encontrar a partida
        partida = next((p for p in partidas if p.get('id') == partida_id), None)
        if not partida:
            return False
        
        # Inicializar lista de detalhes se não existir
        if "jogadores_detalhes" not in partida:
            partida["jogadores_detalhes"] = []
        
        # Procurar se jogador já foi registrado
        detalhe = next((d for d in partida["jogadores_detalhes"] 
                       if d.get("nome") == nome_jogador), None)
        
        if detalhe:
            # Atualizar detalhes existentes
            detalhe["gols"] = gols
            detalhe["assistencias"] = assistencias
            detalhe["cartoes_amarelos"] = cartoes_amarelos
            detalhe["cartoes_vermelhos"] = cartoes_vermelhos
        else:
            # Criar novo registro
            partida["jogadores_detalhes"].append({
                "nome": nome_jogador,
                "gols": gols,
                "assistencias": assistencias,
                "cartoes_amarelos": cartoes_amarelos,
                "cartoes_vermelhos": cartoes_vermelhos,
                "time_numero": time_numero,
                "posicao": posicao,
                "data_registro": datetime.now().isoformat()
            })
        
        # Salvar mudanças
        try:
            if os.getenv("DATABASE_URL"):
                save_json_data("partidas", partidas)
            else:
                with open(self.partidas_arquivo, "w", encoding="utf-8") as f:
                    json.dump(partidas, f, indent=2, ensure_ascii=False)
            self.invalidar_cache_stats()
            return True
        except Exception:
            return False
