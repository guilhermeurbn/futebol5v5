"""
Serviço de Estatísticas Detalhadas de Jogador
Rastreia gols, assistências, cartões, vitórias e muito mais de cada jogador
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from services.db import load_json_data


class JogadorStatsService:
    """Serviço para calcular estatísticas detalhadas por jogador"""
    
    def __init__(self, partidas_arquivo: str = "partidas.json", historico_arquivo: str = "historico.json"):
        """
        Inicializa o serviço
        
        Args:
            partidas_arquivo: Caminho do arquivo de partidas
            historico_arquivo: Caminho do arquivo de histórico
        """
        self.partidas_arquivo = partidas_arquivo
        self.historico_arquivo = historico_arquivo
    
    def _carregar_partidas(self) -> List[dict]:
        """Carrega dados de partidas"""
        if os.getenv("DATABASE_URL"):
            return load_json_data("partidas", [])
        try:
            with open(self.partidas_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _carregar_historico(self) -> List[dict]:
        """Carrega dados do histórico de sorteios"""
        if os.getenv("DATABASE_URL"):
            return load_json_data("historico", [])
        try:
            with open(self.historico_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _resultado_por_time(self, partida: dict, time_numero: Optional[int]) -> str:
        """Calcula resultado (vitória/empate/derrota) para um time em uma partida."""
        if not time_numero:
            return "empate"

        for item in partida.get("times_desempenho", []) or []:
            if int(item.get("time_numero", 0) or 0) != int(time_numero):
                continue
            if int(item.get("vitorias", 0) or 0) > 0:
                return "vitória"
            if int(item.get("derrotas", 0) or 0) > 0:
                return "derrota"
            return "empate"

        time_vencedor = partida.get("time_vencedor")
        if not time_vencedor:
            return "empate"
        if int(time_numero) == int(time_vencedor):
            return "vitória"

        gols_times = partida.get("gols_times", []) or []
        indice = int(time_numero) - 1
        if 0 <= indice < len(gols_times):
            meu_placar = gols_times[indice]
            if any(g > meu_placar for idx, g in enumerate(gols_times) if idx != indice):
                return "derrota"
            if any(g == meu_placar for idx, g in enumerate(gols_times) if idx != indice):
                return "empate"

        return "derrota"
    
    def obter_stats_jogador(self, nome_jogador: str) -> Dict:
        """
        Obtém estatísticas completas de um jogador
        
        Args:
            nome_jogador: Nome do jogador
            
        Returns:
            {
                "nome": str,
                "total_partidas": int,
                "gols": int,
                "assistencias": int,
                "cartoes_amarelos": int,
                "cartoes_vermelhos": int,
                "vitórias": int,
                "derrotas": int,
                "empates": int,
                "win_rate": float,
                "gols_por_partida": float,
                "assistencias_por_partida": float,
                "maior_artilheiro": bool,
                "melhor_artilheiro_partida": int,
                "partidas_sem_gols": int,
                "historico_partidas": List[Dict]
            }
        """
        try:
            partidas = self._carregar_partidas()
            historico = self._carregar_historico()
            
            stats = {
                "nome": nome_jogador,
                "total_partidas": 0,
                "gols": 0,
                "assistencias": 0,
                "cartoes_amarelos": 0,
                "cartoes_vermelhos": 0,
                "vitórias": 0,
                "derrotas": 0,
                "empates": 0,
                "win_rate": 0.0,
                "gols_por_partida": 0.0,
                "assistencias_por_partida": 0.0,
                "maior_artilheiro": False,
                "melhor_artilheiro_partida": 0,
                "partidas_sem_gols": 0,
                "historico_partidas": []
            }
            
            if not partidas:
                return stats
            
            historico_dict = {h.get('id'): h for h in historico}
            
            # Processar cada partida
            for partida in partidas:
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
                        "data": partida.get('data'),
                        "gols": detalhes.get("gols", 0),
                        "assistencias": detalhes.get("assistencias", 0),
                        "cartoes_amarelos": detalhes.get("cartoes_amarelos", 0),
                        "cartoes_vermelhos": detalhes.get("cartoes_vermelhos", 0),
                        "resultado": resultado,
                        "time_numero": detalhes.get("time_numero"),
                        "posicao": detalhes.get("posicao")
                    })
            
            # Calcular taxas
            if stats["total_partidas"] > 0:
                stats["win_rate"] = round((stats["vitórias"] / stats["total_partidas"]) * 100, 1)
                stats["gols_por_partida"] = round(stats["gols"] / stats["total_partidas"], 2)
                stats["assistencias_por_partida"] = round(stats["assistencias"] / stats["total_partidas"], 2)
            
            # Verificar se é o maior artilheiro (por total de gols)
            gols_todos = self._calcular_gols_todos_jogadores()
            if gols_todos and max(gols_todos.values(), default=0) == stats["gols"] and stats["gols"] > 0:
                stats["maior_artilheiro"] = True
            
            # Ordenar histórico por data (mais recente primeiro)
            stats["historico_partidas"].sort(key=lambda x: x.get('data', ''), reverse=True)
            
            return stats
        except Exception as e:
            # Se houver erro, retornar stats vazio em vez de quebrar a aplicação
            import sys
            print(f"Erro ao calcular stats para {nome_jogador}: {str(e)}", file=sys.stderr)
            return {
                "nome": nome_jogador,
                "total_partidas": 0,
                "gols": 0,
                "assistencias": 0,
                "cartoes_amarelos": 0,
                "cartoes_vermelhos": 0,
                "vitórias": 0,
                "derrotas": 0,
                "empates": 0,
                "win_rate": 0.0,
                "gols_por_partida": 0.0,
                "assistencias_por_partida": 0.0,
                "maior_artilheiro": False,
                "melhor_artilheiro_partida": 0,
                "partidas_sem_gols": 0,
                "historico_partidas": []
            }
    
    def _extrair_detalhes_jogador(self, partida: dict, nome_jogador: str, sorteio: dict) -> Optional[dict]:
        """
        Extrai detalhes de um jogador específico em uma partida
        
        Returns:
            Dict com gols, assistências, cartões e resultado, ou None se não encontrado
        """
        # Procurar detalhes do jogador nos dados de jogadores da partida
        jogadores_detalhes = partida.get("jogadores_detalhes", [])
        
        for detalhe in jogadores_detalhes:
            if detalhe.get("nome") == nome_jogador:
                time_numero = detalhe.get("time_numero")
                resultado = self._resultado_por_time(partida, time_numero)
                dados = dict(detalhe)
                dados["resultado"] = resultado
                return dados
        
        # Se não houver detalhes específicos, tentar encontrar o jogador no sorteio
        if sorteio:
            times = sorteio.get('times', [])
            for time_idx, time_data in enumerate(times):
                jogadores = time_data.get('jogadores', [])
                for jogador in jogadores:
                    if jogador.get('nome') == nome_jogador:
                        # Encontrou o jogador neste time
                        time_numero = time_idx + 1
                        resultado = self._resultado_por_time(partida, time_numero)
                        
                        return {
                            "gols": 0,
                            "assistencias": 0,
                            "cartoes_amarelos": 0,
                            "cartoes_vermelhos": 0,
                            "resultado": resultado,
                            "time_numero": time_numero,
                            "posicao": jogador.get("posicao")
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
            with open(self.partidas_arquivo, "w", encoding="utf-8") as f:
                json.dump(partidas, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False