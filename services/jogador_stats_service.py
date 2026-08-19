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

    def _chave_cache_stats(self, nome_jogador: str) -> str:
        """Monta uma chave que evita reaproveitar stats entre fontes diferentes."""
        chave_nome = self._normalizar_nome(nome_jogador)
        return f"{self.__class__.__name__}:{id(self)}:{chave_nome}"
    
    def _carregar_partidas(self) -> List[dict]:
        """Carrega dados de partidas combinando partidas e votacoes_partidas"""
        if os.getenv("DATABASE_URL"):
            partidas = load_json_data("partidas", [])
            votacoes = load_json_data("votacoes_partidas", {})
        else:
            try:
                with open(self.partidas_arquivo, "r", encoding="utf-8") as f:
                    partidas = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                partidas = []
            try:
                with open("data/votacoes.json", "r", encoding="utf-8") as f:
                    votacoes = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                votacoes = {}

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
        for p in partidas:
            if isinstance(p, dict):
                pid = str(p.get("id") or p.get("sorteio_id") or "")
                sid = str(p.get("sorteio_id") or "")
                if pid:
                    p_copy = dict(p)
                    vp = v_by_sorteio.get(sid) or v_by_id.get(pid) or v_by_sorteio.get(pid)
                    if vp:
                        data_val = p_copy.get("data") or vp.get("data") or vp.get("encerrado_em") or vp.get("aberta_em") or ""
                        p_copy["data"] = data_val
                        if not p_copy.get("jogadores_detalhes") and vp.get("participantes"):
                            p_copy["participantes"] = vp.get("participantes")
                        if not p_copy.get("resultado_resumido") and vp.get("resultado_resumido"):
                            p_copy["resultado_resumido"] = vp.get("resultado_resumido")
                        if vp.get("ranking"):
                            p_copy["ranking"] = vp.get("ranking")
                    partidas_dict[pid] = p_copy

        for vp in votacoes_list:
            if isinstance(vp, dict):
                pid = str(vp.get("id") or vp.get("sorteio_id") or "")
                sid = str(vp.get("sorteio_id") or "")
                if not pid and not sid:
                    continue
                if pid not in partidas_dict and (not sid or sid not in partidas_dict):
                    data_val = vp.get("data") or vp.get("encerrado_em") or vp.get("aberta_em") or ""
                    vp_copy = dict(vp)
                    vp_copy["data"] = data_val
                    partidas_dict[pid or sid] = vp_copy

        return list(partidas_dict.values())
    
    def _carregar_historico(self) -> List[dict]:
        """Carrega dados do histórico de sorteios"""
        if os.getenv("DATABASE_URL"):
            return load_json_data("historico", [])
        try:
            with open(self.historico_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

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

        # 1. Checar resultado_resumido (formato da VotacaoService)
        resumo = partida.get("resultado_resumido") or []
        if resumo and isinstance(resumo, list) and len(resumo) >= 2:
            meu_gols = None
            outro_gols = None
            for item in resumo:
                if isinstance(item, dict):
                    if item.get("time_numero") == int(time_numero):
                        meu_gols = int(item.get("gols", 0) or 0)
                    else:
                        outro_gols = int(item.get("gols", 0) or 0)
            if meu_gols is not None and outro_gols is not None:
                if meu_gols > outro_gols:
                    return "vitória"
                elif meu_gols < outro_gols:
                    return "derrota"
                else:
                    return "empate"

        # 2. Checar times_desempenho
        for item in partida.get("times_desempenho", []) or []:
            if int(item.get("time_numero", 0) or 0) != int(time_numero):
                continue
            v = int(item.get("vitorias", 0) or 0)
            d = int(item.get("derrotas", 0) or 0)
            e = int(item.get("empates", 0) or 0)
            if v == 0 and d == 0 and e == 0:
                continue
            if v > 0:
                return "vitória"
            if d > 0:
                return "derrota"
            if e > 0:
                return "empate"

        # 3. Checar time_vencedor
        time_vencedor = partida.get("time_vencedor")
        if time_vencedor is not None:
            if int(time_numero) == int(time_vencedor):
                return "vitória"
            else:
                return "derrota"

        gols_times = partida.get("gols_times", []) or []
        indice = int(time_numero) - 1
        if 0 <= indice < len(gols_times):
            meu_placar = gols_times[indice]
            if any(g > meu_placar for idx, g in enumerate(gols_times) if idx != indice):
                return "derrota"
            if any(g == meu_placar for idx, g in enumerate(gols_times) if idx != indice):
                return "empate"

        return "empate"
    
    def obter_stats_jogador(self, nome_jogador: str) -> Dict:
        """
        Obtém estatísticas completas de um jogador
        """
        try:
            chave_cache = self._chave_cache_stats(nome_jogador)
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
                detalhes = self._extrair_detalhes_jogador(partida, nome_jogador, sorteio)
                
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
                        "posicao": detalhes.get("posicao"),
                        "nota_media": detalhes.get("nota_media", 0.0),
                        "nota_partida": detalhes.get("nota_partida", 0.0)
                    })
            
            # Calcular taxas
            if stats["total_partidas"] > 0:
                stats["win_rate"] = round((stats["vitórias"] / stats["total_partidas"]) * 100, 1)
                stats["gols_por_partida"] = round(stats["gols"] / stats["total_partidas"], 2)
                stats["assistencias_por_partida"] = round(stats["assistencias"] / stats["total_partidas"], 2)
            stats["vitorias"] = stats["vitórias"]
            
            # Verificar se é o maior artilheiro (por total de gols)
            if gols_todos and max(gols_todos.values(), default=0) == stats["gols"] and stats["gols"] > 0:
                stats["maior_artilheiro"] = True
            
            # Ordenar histórico por data (mais recente primeiro, com tratamento seguro para None)
            stats["historico_partidas"].sort(key=lambda x: str(x.get('data') or ''), reverse=True)

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
    
    def _extrair_detalhes_jogador(self, partida: dict, nome_jogador: str, sorteio: dict) -> Optional[dict]:
        """
        Extrai detalhes de um jogador específico em uma partida
        """
        nome_normalizado = self._normalizar_nome(nome_jogador)
        nota_media_ranking = 0.0

        # Obter aliases e user_id do jogador
        target_user_id = None
        player_aliases = {nome_normalizado}
        try:
            from services.auth_service import AuthService
            usuarios = AuthService()._carregar()
            u_target = next((u for u in usuarios if self._normalizar_nome(u.get("nome", "")) == nome_normalizado or self._normalizar_nome(u.get("username", "")) == nome_normalizado), None)
            if u_target:
                target_user_id = u_target.get("id")
                if u_target.get("nome"):
                    player_aliases.add(self._normalizar_nome(u_target["nome"]))
            target_user_ids = {str(target_user_id)} if target_user_id else set()
            gui_main_id = "18c652b0-330e-4e0d-9c5d-eb9a27b889a2"
            gui_old_id = "09142ace-266e-4d33-96db-8b92ed6144c8"
            if gui_main_id in target_user_ids:
                target_user_ids.add(gui_old_id)
                player_aliases.add(self._normalizar_nome("guilherme"))

        except Exception:
            pass

        def _is_match(item_nome: str, item_user_id: Optional[str]) -> bool:
            if target_user_ids and item_user_id and str(item_user_id) in target_user_ids:
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
                if _is_match(rj_nome, rj_uid):
                    nota_media_ranking = float(rj.get("nota_media", 0) or 0)
                    break

        jogadores_detalhes = partida.get("jogadores_detalhes", [])
        
        # 1. Procurar em jogadores_detalhes
        for detalhe in jogadores_detalhes:
            d_nome = detalhe.get("nome", "")
            d_uid = detalhe.get("user_id") or detalhe.get("owner_user_id")
            if _is_match(d_nome, d_uid):
                time_numero = detalhe.get("time_numero")
                resultado = self._resultado_por_time(partida, time_numero)
                dados = dict(detalhe)
                dados["resultado"] = resultado
                nota_val = float(dados.get("nota_media") or dados.get("nota_partida") or dados.get("nota") or nota_media_ranking or 0.0)
                dados["nota_media"] = nota_val
                dados["nota_partida"] = nota_val
                return dados

        # 2. Procurar em participantes (partidas de votação)
        participantes = partida.get("participantes", [])
        for part in participantes:
            p_nome = part.get("jogador_nome") or part.get("nome_usuario") or part.get("username") or ""
            p_uid = part.get("user_id") or part.get("owner_user_id")
            if _is_match(p_nome, p_uid):
                time_numero = part.get("time_numero")
                resultado = self._resultado_por_time(partida, time_numero)
                nota_val = float(part.get("nota_media") or part.get("nota_partida") or part.get("nota") or nota_media_ranking or 0.0)
                return {
                    "gols": 0,
                    "assistencias": 0,
                    "cartoes_amarelos": 0,
                    "cartoes_vermelhos": 0,
                    "resultado": resultado,
                    "time_numero": time_numero,
                    "posicao": part.get("posicao", "linha"),
                    "nota_media": nota_val,
                    "nota_partida": nota_val
                }
        
        # 3. Procurar no sorteio (historico)
        if sorteio:
            times = sorteio.get('times', [])
            for time_idx, time_data in enumerate(times):
                jogadores = time_data.get('jogadores', [])
                for jogador in jogadores:
                    j_nome = jogador.get('nome', '')
                    j_uid = jogador.get('owner_user_id') or jogador.get('user_id')
                    if _is_match(j_nome, j_uid):
                        time_numero = time_idx + 1
                        resultado = self._resultado_por_time(partida, time_numero)
                        nota_val = float(jogador.get("nota") or nota_media_ranking or 0.0)
                        return {
                            "gols": 0,
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
