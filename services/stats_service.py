"""
Serviço de Estatísticas Avançadas
Calcula estatísticas detalhadas sobre desempenho de jogadores e times
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from services.db import load_json_data


class StatsService:
    """Serviço para cálculo de estatísticas avançadas"""
    
    def __init__(self, historico_arquivo: str = "historico.json"):
        """
        Inicializa o serviço
        
        Args:
            historico_arquivo: Caminho do arquivo de histórico
        """
        self.historico_arquivo = historico_arquivo
    
    def _carregar_historico(self) -> List[dict]:
        """Carrega dados do histórico"""
        if os.getenv("DATABASE_URL"):
            return load_json_data("historico", [])
        try:
            with open(self.historico_arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def calcular_stats_jogadores(self) -> Dict[str, Dict]:
        """
        Calcula estatísticas por jogador
        
        Returns:
            {
                "jogador_nome": {
                    "vezes_sorteado": int,
                    "times_vencedores": int,
                    "win_rate": float,
                    "nivel_medio_time": float,
                    "pontuacao_media": float,
                    "posicao_media_ranking": float,
                    "melhor_performance": int,
                    "pior_performance": int,
                    "times_diferentes": int
                },
                ...
            }
        """
        sorteios = self._carregar_historico()
        stats = defaultdict(lambda: {
            "vezes_sorteado": 0,
            "times_vencedores": 0,
            "total_pontuacao_time": 0,
            "rankings": [],
            "times_diferentes": set(),
            "sorteios_ids": []
        })
        
        for sorteio in sorteios:
            times = sorteio.get('times', [])
            pontuacoes = sorteio.get('pontuacoes', [])
            
            # Encontrar melhor time
            if pontuacoes:
                max_pontuacao = max(pontuacoes)
                
                for time_idx, time_data in enumerate(times):
                    for jogador in time_data.get('jogadores', []):
                        nome = jogador.get('nome')
                        if nome:
                            stats[nome]['vezes_sorteado'] += 1
                            stats[nome]['total_pontuacao_time'] += pontuacoes[time_idx]
                            stats[nome]['rankings'].append(time_idx + 1)
                            stats[nome]['times_diferentes'].add(time_idx)
                            stats[nome]['sorteios_ids'].append(sorteio.get('id'))
                            
                            # Contar vitórias (no melhor time)
                            if pontuacoes[time_idx] == max_pontuacao:
                                stats[nome]['times_vencedores'] += 1
        
        # Formatar resultado
        resultado = {}
        for nome, dados in stats.items():
            vezes = dados['vezes_sorteado']
            if vezes > 0:
                resultado[nome] = {
                    "vezes_sorteado": vezes,
                    "times_vencedores": dados['times_vencedores'],
                    "win_rate": round((dados['times_vencedores'] / vezes) * 100, 1),
                    "nivel_medio_time": round(dados['total_pontuacao_time'] / vezes, 1),
                    "pontuacao_media": round(dados['total_pontuacao_time'] / vezes, 1),
                    "posicao_media_ranking": round(sum(dados['rankings']) / vezes, 1),
                    "times_diferentes": len(dados['times_diferentes']),
                    "melhor_performance": min(dados['rankings']),
                    "pior_performance": max(dados['rankings'])
                }
        
        return resultado
    
    def calcular_stats_times(self) -> Dict[str, Dict]:
        """
        Calcula estatísticas por time
        
        Returns:
            {
                "time_X": {
                    "vezes_criado": int,
                    "vezes_vencedor": int,
                    "win_rate": float,
                    "pontuacao_media": float,
                    "melhor_pontuacao": int,
                    "pior_pontuacao": int,
                    "jogadores_comuns": list
                },
                ...
            }
        """
        sorteios = self._carregar_historico()
        stats_times = defaultdict(lambda: {
            "vezes_criado": 0,
            "vezes_vencedor": 0,
            "pontuacoes": [],
            "jogadores": defaultdict(int)
        })
        
        for sorteio in sorteios:
            times = sorteio.get('times', [])
            pontuacoes = sorteio.get('pontuacoes', [])
            
            if pontuacoes:
                max_pontuacao = max(pontuacoes)
                
                for time_idx, time_data in enumerate(times):
                    time_key = f"time_{time_idx + 1}"
                    stats_times[time_key]['vezes_criado'] += 1
                    stats_times[time_key]['pontuacoes'].append(pontuacoes[time_idx])
                    
                    if pontuacoes[time_idx] == max_pontuacao:
                        stats_times[time_key]['vezes_vencedor'] += 1
                    
                    for jogador in time_data.get('jogadores', []):
                        nome = jogador.get('nome')
                        if nome:
                            stats_times[time_key]['jogadores'][nome] += 1
        
        # Formatar resultado
        resultado = {}
        for time_key, dados in stats_times.items():
            vezes = dados['vezes_criado']
            if vezes > 0:
                pontuacoes = dados['pontuacoes']
                jogadores_top = sorted(
                    dados['jogadores'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                
                resultado[time_key] = {
                    "vezes_criado": vezes,
                    "vezes_vencedor": dados['vezes_vencedor'],
                    "win_rate": round((dados['vezes_vencedor'] / vezes) * 100, 1),
                    "pontuacao_media": round(sum(pontuacoes) / vezes, 1),
                    "melhor_pontuacao": max(pontuacoes),
                    "pior_pontuacao": min(pontuacoes),
                    "jogadores_comuns": [{"nome": nome, "vezes": vezes} for nome, vezes in jogadores_top]
                }
        
        return resultado
    
    def calcular_estatisticas_sorteios(self) -> Dict:
        """
        Calcula estatísticas gerais dos sorteios
        
        Returns:
            {
                "total_sorteios": int,
                "media_jogadores": float,
                "media_diferenca": float,
                "melhor_balanceamento": int,
                "pior_balanceamento": int,
                "tendencia_balanceamento": str,
                "ultimo_sorteio": dict,
                "sorteios_ultimas_24h": int
            }
        """
        sorteios = self._carregar_historico()
        
        if not sorteios:
            return {
                "total_sorteios": 0,
                "media_jogadores": 0,
                "media_diferenca": 0,
                "melhor_balanceamento": None,
                "pior_balanceamento": None,
                "tendencia_balanceamento": "N/A",
                "ultimo_sorteio": None,
                "sorteios_ultimas_24h": 0
            }
        
        diferenças = [s.get('diferenca', 0) for s in sorteios]
        total_jogadores = [s.get('total_jogadores', 0) for s in sorteios]
        
        # Verificar últimos 24h
        from datetime import datetime, timedelta
        agora = datetime.now()
        ultima_24h_count = 0
        
        for sorteio in sorteios:
            data_str = sorteio.get('data', '')
            try:
                data_sorteio = datetime.fromisoformat(data_str)
                if (agora - data_sorteio).total_seconds() < 86400:
                    ultima_24h_count += 1
            except:
                pass
        
        # Calcular tendência
        if len(diferenças) >= 5:
            ultimas_5 = diferenças[-5:]
            media_ultimas = sum(ultimas_5) / len(ultimas_5)
            media_anterior = sum(diferenças[:-5]) / len(diferenças[:-5]) if len(diferenças) > 5 else media_ultimas
            
            if media_ultimas < media_anterior:
                tendencia = "Melhorando ↓"
            elif media_ultimas > media_anterior:
                tendencia = "Piorando ↑"
            else:
                tendencia = "Estável →"
        else:
            tendencia = "Dados insuficientes"
        
        return {
            "total_sorteios": len(sorteios),
            "media_jogadores": round(sum(total_jogadores) / len(total_jogadores), 1) if total_jogadores else 0,
            "media_diferenca": round(sum(diferenças) / len(diferenças), 1) if diferenças else 0,
            "melhor_balanceamento": min(diferenças) if diferenças else None,
            "pior_balanceamento": max(diferenças) if diferenças else None,
            "tendencia_balanceamento": tendencia,
            "ultimo_sorteio": sorteios[-1] if sorteios else None,
            "sorteios_ultimas_24h": ultima_24h_count
        }
    
    def get_comparacao_players(self, nome1: str, nome2: str) -> Dict:
        """
        Compara estatísticas entre dois jogadores
        
        Returns:
            Dict com comparação head-to-head
        """
        stats = self.calcular_stats_jogadores()
        
        player1 = stats.get(nome1, {})
        player2 = stats.get(nome2, {})
        
        return {
            "player1": {"nome": nome1, **player1},
            "player2": {"nome": nome2, **player2},
            "diferenca_win_rate": round((player1.get('win_rate', 0) - player2.get('win_rate', 0)), 1),
            "melhor_player": nome1 if player1.get('win_rate', 0) > player2.get('win_rate', 0) else nome2
        }
    
    def get_combos_vencedores(self) -> List[Dict]:
        """
        Retorna os melhores combos de jogadores (que mais venceram juntos)
        
        Returns:
            Lista dos top combos
        """
        sorteios = self._carregar_historico()
        combos = defaultdict(int)
        
        if not sorteios:
            return []
        
        pontuacoes = [s.get('pontuacoes', []) for s in sorteios]
        
        for sorteio_idx, sorteio in enumerate(sorteios):
            times = sorteio.get('times', [])
            somas = sorteio.get('pontuacoes', [])
            
            if somas:
                max_pontuacao = max(somas)
                
                for time_idx, time_data in enumerate(times):
                    if somas[time_idx] == max_pontuacao:
                        # Vencedor!
                        nomes = sorted([
                            j.get('nome') for j in time_data.get('jogadores', [])
                        ])
                        combo_key = tuple(nomes)
                        combos[combo_key] += 1
        
        # Ordenar e retornar
        top_combos = sorted(combos.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [
            {"jogadores": list(combo), "vezes_vencedor": vezes}
            for combo, vezes in top_combos
        ]
