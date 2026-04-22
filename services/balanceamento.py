"""
Serviço de Balanceamento de Times
"""
from typing import Tuple, List, Dict
from models.jogadores import Jogador
import random
import math


class BalanceadorTimes:
    """Serviço para balancear times"""
    
    TAMANHO_TIME = 5  # 5 jogadores por time
    
    @staticmethod
    def validar_jogadores(jogadores: List[Jogador]) -> Tuple[bool, str]:
        """
        Valida se os jogadores são válidos para sorteio
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (válido, mensagem)
        """
        if len(jogadores) < BalanceadorTimes.TAMANHO_TIME:
            return False, f"Precisa de ao menos {BalanceadorTimes.TAMANHO_TIME} jogadores. Atual: {len(jogadores)}"
        
        if len(jogadores) % BalanceadorTimes.TAMANHO_TIME != 0:
            return False, f"Número de jogadores deve ser múltiplo de {BalanceadorTimes.TAMANHO_TIME}. Você tem {len(jogadores)}"
        
        return True, ""
    
    @staticmethod
    def calcular_numero_times(num_jogadores: int) -> int:
        """
        Calcula número de times baseado na quantidade de jogadores
        
        Args:
            num_jogadores: Quantidade de jogadores
            
        Returns:
            Número de times (sempre múltiplo de 5)
        """
        return num_jogadores // BalanceadorTimes.TAMANHO_TIME
    
    @staticmethod
    def separar_goleiros(jogadores: List[Jogador]) -> Tuple[List[Jogador], List[Jogador]]:
        """
        Separa jogadores de linha de goleiros
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (jogadores_linha, goleiros)
        """
        linha = [j for j in jogadores if j.posicao == "linha"]
        goleiros = [j for j in jogadores if j.posicao == "goleiro"]
        return linha, goleiros
    
    @staticmethod
    def validar_jogadores_com_goleiros(jogadores: List[Jogador]) -> Tuple[bool, str]:
        """
        Valida jogadores considerando goleiros
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (válido, mensagem)
        """
        linha, goleiros = BalanceadorTimes.separar_goleiros(jogadores)
        num_times = len(jogadores) // BalanceadorTimes.TAMANHO_TIME
        
        if len(jogadores) % BalanceadorTimes.TAMANHO_TIME != 0:
            return False, f"Número de jogadores deve ser múltiplo de 5. Você tem {len(jogadores)}"
        
        if len(goleiros) < num_times:
            return False, f"Precisa de ao menos {num_times} goleiros. Você tem {len(goleiros)}"
        
        if len(linha) < num_times * 4:
            return False, f"Precisa de ao menos {num_times * 4} jogadores de linha. Você tem {len(linha)}"
        
        return True, ""
    
    @staticmethod
    def calcular_energia(times: List[List[Jogador]]) -> float:
        """
        Calcula a 'energia' de uma distribuição (quanto menos equilibrado, maior a energia)
        
        Args:
            times: Lista de times
            
        Returns:
            Energia total (diferença máxima entre times)
        """
        somas = [sum(j.nivel for j in time) for time in times]
        if not somas:
            return 0
        return max(somas) - min(somas)
    
    @staticmethod
    def simulated_annealing(jogadores: List[Jogador], num_times: int, iteracoes: int = 1000) -> List[List[Jogador]]:
        """
        Usa Simulated Annealing para distribuir jogadores de forma ótima
        
        Args:
            jogadores: Lista de jogadores de linha (sem goleiros)
            num_times: Número de times
            iteracoes: Número máximo de iterações
            
        Returns:
            Lista de times equilibrados
        """
        # Inicializar com distribuição aleatória
        random.shuffle(jogadores)
        times = [[] for _ in range(num_times)]
        for idx, jogador in enumerate(jogadores):
            times[idx % num_times].append(jogador)
        
        energia_atual = BalanceadorTimes.calcular_energia(times)
        melhor_energia = energia_atual
        melhores_times = [time[:] for time in times]
        
        temperatura = 100.0
        temperatura_minima = 0.01
        taxa_resfriamento = 0.99
        
        iteracao = 0
        while temperatura > temperatura_minima and iteracao < iteracoes:
            # Tentar uma troca aleatória
            time1, time2 = random.sample(range(num_times), 2)
            idx1, idx2 = random.randint(0, len(times[time1]) - 1), random.randint(0, len(times[time2]) - 1)
            
            # Fazer a troca
            times[time1][idx1], times[time2][idx2] = times[time2][idx2], times[time1][idx1]
            
            # Calcular nova energia
            energia_nova = BalanceadorTimes.calcular_energia(times)
            
            # Decidir se aceita a troca
            delta_energia = energia_nova - energia_atual
            if delta_energia < 0 or random.random() < math.exp(-delta_energia / temperatura):
                energia_atual = energia_nova
                if energia_atual < melhor_energia:
                    melhor_energia = energia_atual
                    melhores_times = [time[:] for time in times]
            else:
                # Desfazer a troca
                times[time1][idx1], times[time2][idx2] = times[time2][idx2], times[time1][idx1]
            
            temperatura *= taxa_resfriamento
            iteracao += 1
        
        return melhores_times
    
    @staticmethod
    def sortear_multiplos_times(jogadores: List[Jogador]) -> Tuple[List[List[Jogador]], List[int]]:
        """
        Sorteia múltiplos times equilibrados por nível
        
        Algoritmo: Snake draft estendido - alternando entre times, começando pelos melhores
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (lista_de_times, lista_somas_niveis)
            
        Exemplo:
            15 jogadores → [time1, time2, time3]
            20 jogadores → [time1, time2, time3, time4]
        """
        valido, msg = BalanceadorTimes.validar_jogadores(jogadores)
        if not valido:
            raise ValueError(msg)
        
        num_times = BalanceadorTimes.calcular_numero_times(len(jogadores))
        
        # Inicializar times vazios
        times = [[] for _ in range(num_times)]
        somas = [0] * num_times
        
        # Ordena por nível (decrescente)
        jogadores_ordenados = sorted(jogadores, key=lambda x: x.nivel, reverse=True)
        
        # Snake draft: alternando entre times
        for idx, jogador in enumerate(jogadores_ordenados):
            # Usar mod para distribuir entre times
            time_idx = idx % num_times
            times[time_idx].append(jogador)
            somas[time_idx] += jogador.nivel
        
        return times, somas
    
    @staticmethod
    def sortear_multiplos_times_com_goleiros(jogadores: List[Jogador]) -> Tuple[List[List[Jogador]], List[int]]:
        """
        Sorteia múltiplos times com goleiros usando Simulated Annealing
        
        Cada time terá:
        - 1 goleiro (não conta nas estatísticas)
        - 4 jogadores de linha (usados no balanceamento)
        
        Args:
            jogadores: Lista de jogadores (com goleiros e jogadores de linha)
            
        Returns:
            Tupla (lista_de_times, lista_somas_apenas_linha)
        """
        valido, msg = BalanceadorTimes.validar_jogadores_com_goleiros(jogadores)
        if not valido:
            raise ValueError(msg)
        
        linha, goleiros = BalanceadorTimes.separar_goleiros(jogadores)
        num_times = BalanceadorTimes.calcular_numero_times(len(jogadores))
        
        # Ordenar goleiros e jogadores de linha por nível (descendente)
        goleiros_sorted = sorted(goleiros, key=lambda x: x.nivel, reverse=True)
        
        # Usar Simulated Annealing para distribuir jogadores de linha de forma ótima
        times_linha = BalanceadorTimes.simulated_annealing(linha, num_times, iteracoes=2000)
        
        # Adicionar um goleiro por time (round-robin para balancear)
        times_final = []
        for idx, time_linha in enumerate(times_linha):
            time_com_goleiro = [goleiros_sorted[idx % len(goleiros_sorted)]] + time_linha
            times_final.append(time_com_goleiro)
        
        # Calcular somas (apenas jogadores de linha)
        somas = [sum(j.nivel for j in time if j.posicao == "linha") for time in times_final]
        
        return times_final, somas
    
    @staticmethod
    def sortear_times(jogadores: List[Jogador]) -> Tuple[List[Jogador], List[Jogador], int, int]:
        """
        Sorteia times equilibrados por nível (compatibilidade com código anterior)
        
        Algoritmo: Snake draft - alternando entre times, começando pelos melhores
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (time1, time2, soma_nivel_time1, soma_nivel_time2)
        """
        try:
            times, somas = BalanceadorTimes.sortear_multiplos_times(jogadores)
            # Para compatibilidade, retornar apenas 2 times se houver
            if len(times) >= 2:
                return times[0], times[1], somas[0], somas[1]
            else:
                return times[0], [], somas[0], 0
        except ValueError:
            # Fallback para validação antiga
            raise
    
    @staticmethod
    def calcular_diferenca(soma1: int, soma2: int) -> int:
        """
        Calcula diferença entre dois times
        
        Args:
            soma1: Soma de nível time 1
            soma2: Soma de nível time 2
            
        Returns:
            Diferença absoluta
        """
        return abs(soma1 - soma2)
    
    @staticmethod
    def calcular_diferenca_multiplos(somas: List[int]) -> int:
        """
        Calcula diferença máxima entre múltiplos times
        
        Args:
            somas: Lista de somas de níveis dos times
            
        Returns:
            Diferença entre o time mais forte e mais fraco
        """
        if not somas:
            return 0
        return max(somas) - min(somas)
    
    @staticmethod
    def obter_time_favorito(soma1: int, soma2: int) -> str:
        """
        Determina qual time está mais forte
        
        Args:
            soma1: Soma de nível time 1
            soma2: Soma de nível time 2
            
        Returns:
            "Time 1", "Time 2" ou "Equilibrado"
        """
        diff = BalanceadorTimes.calcular_diferenca(soma1, soma2)
        if diff <= 2:
            return "Equilibrado"
        return "Time 1" if soma1 > soma2 else "Time 2"
    
    @staticmethod
    def obter_melhor_time(somas: List[int]) -> str:
        """
        Determina qual é o melhor time entre múltiplos
        
        Args:
            somas: Lista de somas de níveis dos times
            
        Returns:
            Nome do time mais forte
        """
        if not somas:
            return "Nenhum"
        
        idx_maximo = somas.index(max(somas))
        return f"Time {idx_maximo + 1}"

