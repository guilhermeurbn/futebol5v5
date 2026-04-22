"""
Serviço de Balanceamento de Times
"""
from typing import Tuple, List, Dict
from models.jogadores import Jogador


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

