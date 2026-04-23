"""
Serviço de Ranking de Times - NaTrave
Gerencia ranking de times baseado em performance
"""
import json
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class RankingService:
    """Serviço de ranking de times"""
    
    def __init__(self):
        self.historico_path = 'historico.json'
        self.partidas_path = 'data/partidas.json'
        self.ranking_cache = {}

    def _resolver_caminho_existente(self, caminhos: List[str]) -> Optional[str]:
        """Retorna o primeiro caminho existente para manter compatibilidade entre versões."""
        for caminho in caminhos:
            if os.path.exists(caminho):
                return caminho
        return None
    
    def _carregar_historico(self) -> List[dict]:
        """Carregar histórico de sorteios"""
        caminho = self._resolver_caminho_existente([
            self.historico_path,
            'data/historico.json'
        ])

        if not caminho:
            return []
        
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _carregar_partidas(self) -> List[dict]:
        """Carregar histórico de partidas"""
        caminho = self._resolver_caminho_existente([
            self.partidas_path,
            'partidas.json'
        ])

        if not caminho:
            return []
        
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _gerar_assinatura_time(self, jogadores: List[dict]) -> str:
        """
        Gerar assinatura única para um time
        
        Args:
            jogadores: Lista de jogadores do time
            
        Returns:
            String com assinatura do time
        """
        nomes_ordenados = sorted([j.get('nome', '') for j in jogadores])
        return '|'.join(nomes_ordenados)

    def _normalizar_jogadores(self, jogadores: List) -> List[Dict]:
        """Normaliza lista de jogadores para o formato dict esperado pelo template."""
        normalizados = []
        for jogador in jogadores:
            if isinstance(jogador, dict):
                normalizados.append(jogador)
            elif isinstance(jogador, str):
                normalizados.append({'nome': jogador, 'nivel': 0, 'tipo': 'desconhecido'})
            else:
                normalizados.append({'nome': str(jogador), 'nivel': 0, 'tipo': 'desconhecido'})
        return normalizados
    
    def calcular_ranking_geral(self, limite: int = 20) -> List[Dict]:
        """
        Calcular ranking de times baseado em histórico geral
        
        Args:
            limite: Número máximo de times a retornar
            
        Returns:
            Lista de times ordenados por ranking
        """
        historico = self._carregar_historico()
        partidas = self._carregar_partidas()
        
        # Dict para armazenar stats dos times
        times_stats = {}
        
        # Processar histórico (contagem de criação)
        for sorteio in historico:
            times = sorteio.get('times', [])
            pontuacoes = sorteio.get('pontuacoes', [])
            
            for idx, time in enumerate(times):
                time_normalizado = self._normalizar_jogadores(time)
                assinatura = self._gerar_assinatura_time(time_normalizado)
                
                if assinatura not in times_stats:
                    times_stats[assinatura] = {
                        'jogadores': time_normalizado,
                        'assinatura': assinatura,
                        'criado': 0,
                        'vitorias': 0,
                        'derrotas': 0,
                        'total_sorteios': 0,
                        'pontuacao_total': 0,
                        'melhor_pontuacao': 0,
                        'pior_pontuacao': float('inf'),
                        'partidas_registradas': []
                    }
                
                times_stats[assinatura]['criado'] += 1
                times_stats[assinatura]['total_sorteios'] += 1
                
                # Registrar pontuação
                if idx < len(pontuacoes):
                    pont = pontuacoes[idx]
                    times_stats[assinatura]['pontuacao_total'] += pont
                    times_stats[assinatura]['melhor_pontuacao'] = max(
                        times_stats[assinatura]['melhor_pontuacao'], 
                        pont
                    )
                    times_stats[assinatura]['pior_pontuacao'] = min(
                        times_stats[assinatura]['pior_pontuacao'],
                        pont
                    )
        
        # Processar partidas (vitórias/derrotas)
        for partida in partidas:
            sorteio_id = partida.get('sorteio_id')
            time_vencedor = partida.get('time_vencedor')
            
            # Encontrar o sorteio correspondente
            sorteio_correspondente = None
            for sorteio in historico:
                if sorteio.get('id') == sorteio_id:
                    sorteio_correspondente = sorteio
                    break
            
            if sorteio_correspondente:
                times = sorteio_correspondente.get('times', [])
                
                for idx, time in enumerate(times):
                    time_normalizado = self._normalizar_jogadores(time)
                    assinatura = self._gerar_assinatura_time(time_normalizado)
                    
                    if assinatura in times_stats:
                        if idx + 1 == time_vencedor:  # Times são 1-indexed nas partidas
                            times_stats[assinatura]['vitorias'] += 1
                        else:
                            times_stats[assinatura]['derrotas'] += 1
        
        # Calcular scores e ordenar
        ranking = []
        for assinatura, stats in times_stats.items():
            total_jogos = stats['vitorias'] + stats['derrotas']
            taxa_vitoria = stats['vitorias'] / total_jogos if total_jogos > 0 else 0
            pontuacao_media = stats['pontuacao_total'] / stats['total_sorteios'] if stats['total_sorteios'] > 0 else 0
            
            # Score: combinação de criação, taxa de vitória e pontuação média
            score = (
                stats['criado'] * 10 +  # Peso: quantas vezes foi criado
                taxa_vitoria * 500 +    # Peso: taxa de vitória
                pontuacao_media * 5     # Peso: pontuação média
            )
            
            ranking.append({
                'assinatura': assinatura,
                'jogadores': stats['jogadores'],
                'score': score,
                'criado': stats['criado'],
                'vitorias': stats['vitorias'],
                'derrotas': stats['derrotas'],
                'total_sorteios': stats['total_sorteios'],
                'taxa_vitoria': taxa_vitoria,
                'pontuacao_media': pontuacao_media,
                'melhor_pontuacao': stats['melhor_pontuacao'],
                'pior_pontuacao': stats['pior_pontuacao'] if stats['pior_pontuacao'] != float('inf') else 0
            })
        
        # Ordenar por score
        ranking.sort(key=lambda x: x['score'], reverse=True)
        
        return ranking[:limite]
    
    def calcular_ranking_periodo(self, dias: int = 30, limite: int = 20) -> List[Dict]:
        """
        Calcular ranking de times apenas para um período
        
        Args:
            dias: Número de dias para considerar
            limite: Número máximo de times a retornar
            
        Returns:
            Lista de times ordenados por ranking
        """
        historico = self._carregar_historico()
        
        # Filtrar por data
        data_limite = datetime.now() - timedelta(days=dias)
        historico_filtrado = []
        
        for sorteio in historico:
            try:
                data_sorteio = datetime.fromisoformat(sorteio.get('data', ''))
                if data_sorteio >= data_limite:
                    historico_filtrado.append(sorteio)
            except:
                historico_filtrado.append(sorteio)  # Incluir se não conseguir parse
        
        # Processar similar ao método anterior, mas com histórico filtrado
        times_stats = {}
        
        for sorteio in historico_filtrado:
            times = sorteio.get('times', [])
            pontuacoes = sorteio.get('pontuacoes', [])
            
            for idx, time in enumerate(times):
                time_normalizado = self._normalizar_jogadores(time)
                assinatura = self._gerar_assinatura_time(time_normalizado)
                
                if assinatura not in times_stats:
                    times_stats[assinatura] = {
                        'jogadores': time_normalizado,
                        'assinatura': assinatura,
                        'criado': 0,
                        'vitorias': 0,
                        'derrotas': 0,
                        'total_sorteios': 0,
                        'pontuacao_total': 0,
                        'melhor_pontuacao': 0,
                        'pior_pontuacao': float('inf')
                    }
                
                times_stats[assinatura]['criado'] += 1
                times_stats[assinatura]['total_sorteios'] += 1
                
                if idx < len(pontuacoes):
                    pont = pontuacoes[idx]
                    times_stats[assinatura]['pontuacao_total'] += pont
                    times_stats[assinatura]['melhor_pontuacao'] = max(
                        times_stats[assinatura]['melhor_pontuacao'], 
                        pont
                    )
                    times_stats[assinatura]['pior_pontuacao'] = min(
                        times_stats[assinatura]['pior_pontuacao'],
                        pont
                    )
        
        # Calcular scores
        ranking = []
        for assinatura, stats in times_stats.items():
            pontuacao_media = stats['pontuacao_total'] / stats['total_sorteios'] if stats['total_sorteios'] > 0 else 0
            
            score = stats['criado'] * 20 + pontuacao_media * 5
            
            ranking.append({
                'assinatura': assinatura,
                'jogadores': stats['jogadores'],
                'score': score,
                'criado': stats['criado'],
                'vitorias': stats['vitorias'],
                'derrotas': stats['derrotas'],
                'total_sorteios': stats['total_sorteios'],
                'taxa_vitoria': 0,
                'pontuacao_media': pontuacao_media,
                'melhor_pontuacao': stats['melhor_pontuacao'],
                'pior_pontuacao': stats['pior_pontuacao'] if stats['pior_pontuacao'] != float('inf') else 0
            })
        
        ranking.sort(key=lambda x: x['score'], reverse=True)
        
        return ranking[:limite]
    
    def obter_estatisticas_ranking(self) -> Dict:
        """
        Obter estatísticas gerais do ranking
        
        Returns:
            Dict com estatísticas
        """
        ranking = self.calcular_ranking_geral(100)
        
        if not ranking:
            return {
                'total_times': 0,
                'melhor_time': None,
                'pontuacao_media_geral': 0,
                'taxa_vitoria_media': 0,
                'times_mais_criados': []
            }
        
        # Calcular médias
        pontuacao_media = sum(t['pontuacao_media'] for t in ranking) / len(ranking)
        taxa_vitoria_media = sum(t['taxa_vitoria'] for t in ranking) / len(ranking)
        
        # Top 5 mais criados
        times_mais_criados = sorted(ranking, key=lambda x: x['criado'], reverse=True)[:5]
        
        return {
            'total_times': len(ranking),
            'melhor_time': ranking[0] if ranking else None,
            'pontuacao_media_geral': pontuacao_media,
            'taxa_vitoria_media': taxa_vitoria_media,
            'times_mais_criados': times_mais_criados
        }
    
    def formatar_time_para_exibicao(self, time_dict: Dict) -> str:
        """
        Formatar time para exibição legível
        
        Args:
            time_dict: Dict com informações do time
            
        Returns:
            String formatada
        """
        jogadores = time_dict.get('jogadores', [])
        nomes = [j.get('nome', '?') for j in jogadores]
        return ' + '.join(nomes)
