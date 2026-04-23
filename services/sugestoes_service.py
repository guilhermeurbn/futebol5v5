"""
Serviço de Sugestões Inteligentes - NaTrave
Fornece recomendações inteligentes de jogadores para melhor balanceamento e diversidade
"""
import json
import os
from collections import Counter
from statistics import mean, stdev
from pathlib import Path


class SugestoesService:
    """Serviço de sugestões inteligentes de jogadores"""
    
    def __init__(self):
        self.historico_path = 'historico.json'
        self.stats_cache = None
    
    def _carregar_historico(self):
        """Carregar histórico de sorteios"""
        if not os.path.exists(self.historico_path):
            return []
        
        try:
            with open(self.historico_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _carregar_stats(self):
        """Carregar arquivo de estatísticas"""
        stats_path = 'data/stats.json'
        if not os.path.exists(stats_path):
            return {}
        
        try:
            with open(stats_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def obter_sugestoes_nivel(self, jogadores_selecionados: list, todos_jogadores: list, num_sugestoes: int = 5) -> list:
        """
        Sugerir jogadores baseado no nível para melhor balanceamento
        
        Args:
            jogadores_selecionados: Lista de jogadores já selecionados
            todos_jogadores: Lista de todos os jogadores disponíveis
            num_sugestoes: Número de sugestões a retornar
            
        Returns:
            Lista de jogadores sugeridos
        """
        if not jogadores_selecionados or not todos_jogadores:
            return []
        
        # Calcular nível médio dos jogadores selecionados
        niveis_selecionados = [j.get('nivel', 5) for j in jogadores_selecionados]
        nivel_medio = mean(niveis_selecionados) if niveis_selecionados else 5
        
        # Encontrar jogadores não selecionados com nível próximo
        nomes_selecionados = {j.get('nome', '').lower() for j in jogadores_selecionados}
        candidatos = []
        
        for jogador in todos_jogadores:
            if jogador.get('nome', '').lower() not in nomes_selecionados:
                nivel = jogador.get('nivel', 5)
                # Penalizar jogadores muito fora do nível médio
                diferenca = abs(nivel - nivel_medio)
                score = 100 - (diferenca * 20)  # Score de 0-100
                
                candidatos.append({
                    'nome': jogador.get('nome', ''),
                    'nivel': nivel,
                    'tipo': jogador.get('tipo', 'avulso'),
                    'posicao': jogador.get('posicao', 'linha'),
                    'score': max(0, score),
                    'motivo': f'Nível {nivel} (próximo a {nivel_medio:.1f})'
                })
        
        # Ordenar por score e retornar top
        candidatos.sort(key=lambda x: x['score'], reverse=True)
        return candidatos[:num_sugestoes]
    
    def obter_sugestoes_diversidade(self, jogadores_selecionados: list, todos_jogadores: list, num_sugestoes: int = 5) -> list:
        """
        Sugerir jogadores para aumentar diversidade (menos repetições)
        
        Args:
            jogadores_selecionados: Lista de jogadores já selecionados
            todos_jogadores: Lista de todos os jogadores disponíveis
            num_sugestoes: Número de sugestões a retornar
            
        Returns:
            Lista de jogadores sugeridos
        """
        historico = self._carregar_historico()
        if not historico:
            # Sem histórico, usar sugestões por nível
            return self.obter_sugestoes_nivel(jogadores_selecionados, todos_jogadores, num_sugestoes)
        
        # Contar frequência de cada jogador em sorteios recentes (últimos 20)
        frequencia = Counter()
        for sorteio in historico[-20:]:
            for time in sorteio.get('times', []):
                for jogador in time:
                    frequencia[jogador.get('nome', '').lower()] += 1
        
        # Encontrar jogadores com menor frequência
        nomes_selecionados = {j.get('nome', '').lower() for j in jogadores_selecionados}
        candidatos = []
        
        for jogador in todos_jogadores:
            nome_lower = jogador.get('nome', '').lower()
            if nome_lower not in nomes_selecionados:
                # Score baseado em frequência (menos frequente = maior score)
                freq = frequencia.get(nome_lower, 0)
                score = 100 - (freq * 10)
                
                candidatos.append({
                    'nome': jogador.get('nome', ''),
                    'nivel': jogador.get('nivel', 5),
                    'tipo': jogador.get('tipo', 'avulso'),
                    'posicao': jogador.get('posicao', 'linha'),
                    'score': max(0, score),
                    'motivo': f'Menos utilizado ({freq} vezes recentes)'
                })
        
        candidatos.sort(key=lambda x: x['score'], reverse=True)
        return candidatos[:num_sugestoes]
    
    def obter_sugestoes_vencedoras(self, jogadores_selecionados: list, todos_jogadores: list, num_sugestoes: int = 5) -> list:
        """
        Sugerir jogadores que fazem parte de combinações vencedoras
        
        Args:
            jogadores_selecionados: Lista de jogadores já selecionados
            todos_jogadores: Lista de todos os jogadores disponíveis
            num_sugestoes: Número de sugestões a retornar
            
        Returns:
            Lista de jogadores sugeridos
        """
        historico = self._carregar_historico()
        if not historico:
            return self.obter_sugestoes_nivel(jogadores_selecionados, todos_jogadores, num_sugestoes)
        
        # Contar vitórias por jogador (apenas de times vencedores)
        vitorias = Counter()
        total_participacoes = Counter()
        
        for sorteio in historico[-30:]:  # Últimos 30 sorteios
            # Encontrar time vencedor
            pontuacoes = sorteio.get('pontuacoes', [])
            times = sorteio.get('times', [])
            
            if pontuacoes and times and len(pontuacoes) > 0:
                try:
                    idx_melhor = pontuacoes.index(max(pontuacoes))
                    time_vencedor = times[idx_melhor] if idx_melhor < len(times) else None
                    
                    if time_vencedor:
                        for jogador in time_vencedor:
                            nome_lower = jogador.get('nome', '').lower()
                            vitorias[nome_lower] += 1
                            total_participacoes[nome_lower] += 1
                except:
                    pass
            
            # Contar participação
            for time in times:
                for jogador in time:
                    total_participacoes[jogador.get('nome', '').lower()] += 1
        
        # Calcular taxa de vitória
        nomes_selecionados = {j.get('nome', '').lower() for j in jogadores_selecionados}
        candidatos = []
        
        for jogador in todos_jogadores:
            nome_lower = jogador.get('nome', '').lower()
            if nome_lower not in nomes_selecionados and total_participacoes.get(nome_lower, 0) > 0:
                taxa_vitoria = vitorias.get(nome_lower, 0) / total_participacoes.get(nome_lower, 1)
                score = taxa_vitoria * 100
                
                candidatos.append({
                    'nome': jogador.get('nome', ''),
                    'nivel': jogador.get('nivel', 5),
                    'tipo': jogador.get('tipo', 'avulso'),
                    'posicao': jogador.get('posicao', 'linha'),
                    'score': score,
                    'motivo': f'Vence {taxa_vitoria*100:.0f}% das vezes'
                })
        
        if not candidatos:
            return self.obter_sugestoes_nivel(jogadores_selecionados, todos_jogadores, num_sugestoes)
        
        candidatos.sort(key=lambda x: x['score'], reverse=True)
        return candidatos[:num_sugestoes]
    
    def obter_sugestoes_melhores_duplas(self, jogadores_selecionados: list, todos_jogadores: list, num_sugestoes: int = 5) -> list:
        """
        Sugerir jogadores baseado em duplas/trios vencedores
        
        Args:
            jogadores_selecionados: Lista de jogadores já selecionados
            todos_jogadores: Lista de todos os jogadores disponíveis
            num_sugestoes: Número de sugestões a retornar
            
        Returns:
            Lista de jogadores sugeridos
        """
        historico = self._carregar_historico()
        if not historico or len(jogadores_selecionados) < 2:
            return self.obter_sugestoes_nivel(jogadores_selecionados, todos_jogadores, num_sugestoes)
        
        nomes_selecionados_lower = [j.get('nome', '').lower() for j in jogadores_selecionados]
        duplas_vencedoras = Counter()
        
        for sorteio in historico[-20:]:
            pontuacoes = sorteio.get('pontuacoes', [])
            times = sorteio.get('times', [])
            
            if pontuacoes and times:
                try:
                    idx_melhor = pontuacoes.index(max(pontuacoes))
                    time_vencedor = times[idx_melhor] if idx_melhor < len(times) else None
                    
                    if time_vencedor and len(time_vencedor) >= 2:
                        # Buscar duplas que contêm jogadores selecionados
                        nomes_time_lower = [j.get('nome', '').lower() for j in time_vencedor]
                        for nome_selecionado in nomes_selecionados_lower:
                            if nome_selecionado in nomes_time_lower:
                                # Encontrar companheiros de time
                                for nome_companheiro in nomes_time_lower:
                                    if nome_companheiro != nome_selecionado:
                                        dupla = tuple(sorted([nome_selecionado, nome_companheiro]))
                                        duplas_vencedoras[dupla] += 1
                except:
                    pass
        
        # Encontrar jogadores que mais aparecem em duplas vencedoras
        candidatos_set = set()
        for (j1, j2) in duplas_vencedoras.keys():
            if j1 not in nomes_selecionados_lower:
                candidatos_set.add(j1)
            if j2 not in nomes_selecionados_lower:
                candidatos_set.add(j2)
        
        nomes_selecionados = {j.get('nome', '').lower() for j in jogadores_selecionados}
        candidatos = []
        
        for jogador in todos_jogadores:
            nome_lower = jogador.get('nome', '').lower()
            if nome_lower in candidatos_set:
                # Contar quantas duplas vencedoras tem este jogador
                count = sum(1 for (j1, j2) in duplas_vencedoras if j1 == nome_lower or j2 == nome_lower)
                
                candidatos.append({
                    'nome': jogador.get('nome', ''),
                    'nivel': jogador.get('nivel', 5),
                    'tipo': jogador.get('tipo', 'avulso'),
                    'posicao': jogador.get('posicao', 'linha'),
                    'score': count * 20,
                    'motivo': f'Bom parceiro dos times vencedores'
                })
        
        if not candidatos:
            return self.obter_sugestoes_diversidade(jogadores_selecionados, todos_jogadores, num_sugestoes)
        
        candidatos.sort(key=lambda x: x['score'], reverse=True)
        return candidatos[:num_sugestoes]
    
    def obter_sugestoes_combinadas(self, jogadores_selecionados: list, todos_jogadores: list, num_sugestoes: int = 5) -> dict:
        """
        Obter sugestões combinadas usando múltiplas estratégias
        
        Args:
            jogadores_selecionados: Lista de jogadores já selecionados
            todos_jogadores: Lista de todos os jogadores disponíveis
            num_sugestoes: Número de sugestões por estratégia
            
        Returns:
            Dict com sugestões por categoria
        """
        return {
            'nivel': self.obter_sugestoes_nivel(jogadores_selecionados, todos_jogadores, num_sugestoes),
            'diversidade': self.obter_sugestoes_diversidade(jogadores_selecionados, todos_jogadores, num_sugestoes),
            'vencedores': self.obter_sugestoes_vencedoras(jogadores_selecionados, todos_jogadores, num_sugestoes),
            'duplas': self.obter_sugestoes_melhores_duplas(jogadores_selecionados, todos_jogadores, num_sugestoes)
        }
    
    def validar_sugestao(self, jogador_sugestao: dict, jogadores_selecionados: list) -> bool:
        """
        Validar se uma sugestão é válida
        
        Args:
            jogador_sugestao: Jogador sugerido
            jogadores_selecionados: Jogadores já selecionados
            
        Returns:
            True se sugestão é válida, False caso contrário
        """
        nome_sugestao_lower = jogador_sugestao.get('nome', '').lower()
        nomes_selecionados_lower = {j.get('nome', '').lower() for j in jogadores_selecionados}
        
        # Validação: não duplicar
        if nome_sugestao_lower in nomes_selecionados_lower:
            return False
        
        # Validação: sugestão deve ter campos necessários
        campos_necessarios = ['nome', 'nivel', 'posicao', 'tipo']
        if not all(campo in jogador_sugestao for campo in campos_necessarios):
            return False
        
        return True
