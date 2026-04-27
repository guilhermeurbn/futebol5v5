"""
Serviço de Balanceamento de Times

NOVO MODELO: Goleiros contam como jogadores normais (4 linha + 1 goleiro = 5 do time)
- Time tem exatamente 5 jogadores
- Pontuação é a soma de todos os 5 (linha + goleiro)
- Simulated Annealing distribui todos os jogadores igualmente
"""
from typing import Tuple, List
from models.jogadores import Jogador
import random
import math


class BalanceadorTimes:
    """Serviço para balancear times"""
    
    TAMANHO_TIME = 5  # 5 jogadores por time

    @staticmethod
    def _soma_time(time: List[Jogador]) -> int:
        return sum(j.nivel for j in time)

    @staticmethod
    def _contar_goleiros(time: List[Jogador]) -> int:
        return sum(1 for j in time if j.posicao == "goleiro")

    @staticmethod
    def _limites_goleiros(num_goleiros: int, num_times: int) -> Tuple[int, int]:
        if num_times <= 0:
            return 0, 0
        minimo = num_goleiros // num_times
        maximo = math.ceil(num_goleiros / num_times)
        return minimo, maximo

    @staticmethod
    def _calcular_energia_balanceada(times: List[List[Jogador]], num_goleiros: int) -> float:
        """
        Calcula energia combinando equilíbrio de nível e distribuição válida de goleiros.

        A penalidade de goleiros é propositalmente alta para impedir distribuições
        "estranhas" como um time com 2 goleiros enquanto outro fica sem, quando isso
        não é necessário.
        """
        if not times:
            return 0

        somas = [BalanceadorTimes._soma_time(time) for time in times]
        diferenca = max(somas) - min(somas)
        media = sum(somas) / len(somas)
        dispersao = sum(abs(soma - media) for soma in somas)

        minimo_goleiros, maximo_goleiros = BalanceadorTimes._limites_goleiros(num_goleiros, len(times))
        penalidade = 0

        for time in times:
            if len(time) != BalanceadorTimes.TAMANHO_TIME:
                penalidade += abs(len(time) - BalanceadorTimes.TAMANHO_TIME) * 5000

            qtd_goleiros = BalanceadorTimes._contar_goleiros(time)
            if qtd_goleiros < minimo_goleiros:
                penalidade += (minimo_goleiros - qtd_goleiros) * 2000
            if qtd_goleiros > maximo_goleiros:
                penalidade += (qtd_goleiros - maximo_goleiros) * 2000

        return penalidade + (diferenca * 100) + dispersao

    @staticmethod
    def _refinar_times_com_restricoes(times: List[List[Jogador]], num_goleiros: int, iteracoes: int = 4000) -> List[List[Jogador]]:
        """
        Refina os times completos com Simulated Annealing, preservando o tamanho
        de cada time por meio de trocas 1x1 e punindo distribuições ruins de goleiros.
        """
        if len(times) < 2:
            return [time[:] for time in times]

        times_trabalho = [time[:] for time in times]
        energia_atual = BalanceadorTimes._calcular_energia_balanceada(times_trabalho, num_goleiros)
        melhor_energia = energia_atual
        melhores_times = [time[:] for time in times_trabalho]

        temperatura = 120.0
        temperatura_minima = 0.01
        taxa_resfriamento = 0.995
        iteracao = 0

        while temperatura > temperatura_minima and iteracao < iteracoes:
            time1, time2 = random.sample(range(len(times_trabalho)), 2)
            idx1 = random.randint(0, len(times_trabalho[time1]) - 1)
            idx2 = random.randint(0, len(times_trabalho[time2]) - 1)

            times_trabalho[time1][idx1], times_trabalho[time2][idx2] = (
                times_trabalho[time2][idx2],
                times_trabalho[time1][idx1],
            )

            energia_nova = BalanceadorTimes._calcular_energia_balanceada(times_trabalho, num_goleiros)
            delta_energia = energia_nova - energia_atual

            if delta_energia < 0 or random.random() < math.exp(-delta_energia / temperatura):
                energia_atual = energia_nova
                if energia_atual < melhor_energia:
                    melhor_energia = energia_atual
                    melhores_times = [time[:] for time in times_trabalho]
            else:
                times_trabalho[time1][idx1], times_trabalho[time2][idx2] = (
                    times_trabalho[time2][idx2],
                    times_trabalho[time1][idx1],
                )

            temperatura *= taxa_resfriamento
            iteracao += 1

        return melhores_times

    @staticmethod
    def separar_goleiros(jogadores: List[Jogador]) -> Tuple[List[Jogador], List[Jogador]]:
        """Compatibilidade: separa jogadores de linha e goleiros."""
        linha = [j for j in jogadores if j.posicao == "linha"]
        goleiros = [j for j in jogadores if j.posicao == "goleiro"]
        return linha, goleiros

    @staticmethod
    def validar_jogadores_com_goleiros(jogadores: List[Jogador]) -> Tuple[bool, str]:
        """Compatibilidade: mantém assinatura antiga de validação com goleiros."""
        return BalanceadorTimes.validar_jogadores(jogadores)
    
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
    def simulated_annealing(jogadores: List[Jogador], num_times: int, iteracoes: int = 2000) -> List[List[Jogador]]:
        """
        Usa Simulated Annealing para distribuir jogadores de forma ótima
        
        Args:
            jogadores: Lista de TODOS os jogadores (linha + goleiros)
            num_times: Número de times
            iteracoes: Número máximo de iterações
            
        Returns:
            Lista de times equilibrados (cada time com 5 jogadores)
        """
        # Inicializar com distribuição aleatória sem mutar a lista original
        jogadores = jogadores[:]
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
        Sorteia múltiplos times equilibrados (alias para compatibilidade)
        Goleiros agora contam como jogadores normais
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (lista_de_times, lista_somas_niveis)
        """
        times, somas, _, _ = BalanceadorTimes.sortear_multiplos_times_com_goleiros(jogadores)
        return times, somas
    
    @staticmethod
    def sortear_multiplos_times_com_goleiros(jogadores: List[Jogador]) -> Tuple[List[List[Jogador]], List[int], bool, str]:
        """
        Sorteia múltiplos times com goleiros usando Simulated Annealing
        
        NOVO: Goleiros contam como jogadores normais!
        REGRA: Cada time tem exatamente 5 jogadores
               - Se goleiros <= times: máximo 1 por time
               - Se goleiros > times: alguns times terão 2+ goleiros
        
        Exemplos:
        - 3 goleiros + 7 linha (2 times): Time 1 = 2 goleiros + 3 linha, Time 2 = 1 goleiro + 4 linha
        - 2 goleiros + 8 linha (2 times): Time 1 = 1 goleiro + 4 linha, Time 2 = 1 goleiro + 4 linha
        - 1 goleiro + 9 linha (2 times): Time 1 = 1 goleiro + 4 linha, Time 2 = 0 goleiros + 5 linha
        
        Args:
            jogadores: Lista de jogadores (linha + goleiros misturados)
            
        Returns:
            Tupla (lista_de_times, lista_somas_totais, tem_aviso, mensagem_aviso)
        """
        # Validação básica
        valido, msg = BalanceadorTimes.validar_jogadores(jogadores)
        if not valido:
            raise ValueError(msg)
        
        # Separar goleiros e linha
        linha = [j for j in jogadores if j.posicao == "linha"]
        goleiros = [j for j in jogadores if j.posicao == "goleiro"]
        
        num_times = BalanceadorTimes.calcular_numero_times(len(jogadores))
        tamanho_time = BalanceadorTimes.TAMANHO_TIME
        
        # Verificar desvios de goleiros para exibir contexto ao usuário
        tem_aviso = len(goleiros) != num_times
        aviso_msg = ""
        
        if len(goleiros) > num_times:
            excesso = len(goleiros) - num_times
            aviso_msg = f"⚠️ {excesso} goleiro(s) a mais que time(s). Alguns times terão 2+ goleiros."
        elif len(goleiros) < num_times:
            falta = num_times - len(goleiros)
            aviso_msg = f"⚠️ Faltam {falta} goleiro(s) para fechar 1 por time. O sistema vai equilibrar os níveis mesmo com time(s) sem goleiro."
        
        # Ordenar por nível (decrescente)
        linha_ordenada = sorted(linha, key=lambda x: x.nivel, reverse=True)
        goleiros_ordenados = sorted(goleiros, key=lambda x: x.nivel, reverse=True)
        
        # 1. Distribuir goleiros round-robin entre times
        times = [[] for _ in range(num_times)]
        for idx, goleiro in enumerate(goleiros_ordenados):
            times[idx % num_times].append(goleiro)
        
        # 2. Completar os times com jogadores de linha, sempre reforçando o time
        # atualmente mais fraco para compensar inclusive o peso dos goleiros.
        for jogador_linha in linha_ordenada:
            candidatos = [
                idx for idx, time in enumerate(times)
                if len(time) < tamanho_time
            ]
            candidatos.sort(
                key=lambda idx: (
                    BalanceadorTimes._soma_time(times[idx]),
                    len(times[idx]),
                    BalanceadorTimes._contar_goleiros(times[idx]),
                    idx,
                )
            )
            times[candidatos[0]].append(jogador_linha)

        # 3. Refinar os times completos considerando nível total e distribuição
        # de goleiros ao mesmo tempo.
        times = BalanceadorTimes._refinar_times_com_restricoes(times, len(goleiros))
        
        # Calcular somas (todos os jogadores contam)
        somas = [sum(j.nivel for j in time) for time in times]
        
        return times, somas, tem_aviso, aviso_msg
    
    @staticmethod
    def sortear_times(jogadores: List[Jogador]) -> Tuple[List[Jogador], List[Jogador], int, int]:
        """
        Sorteia 2 times equilibrados (deprecated - use sortear_multiplos_times_com_goleiros)
        Goleiros contam como jogadores normais
        
        Args:
            jogadores: Lista de jogadores
            
        Returns:
            Tupla (time1, time2, soma1, soma2)
        """
        try:
            times, somas, _, _ = BalanceadorTimes.sortear_multiplos_times_com_goleiros(jogadores)
            if len(times) >= 2:
                return times[0], times[1], somas[0], somas[1]
            else:
                return times[0], [], somas[0], 0
        except ValueError:
            raise
    
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
    def obter_melhor_time(somas: List[int]) -> str:
        """
        Retorna qual é o melhor time (maior pontuação)
        
        Args:
            somas: Lista com soma de cada time
            
        Returns:
            String com "Time X"
        """
        if not somas:
            return ""
        
        idx_melhor = somas.index(max(somas))
        return f"Time {idx_melhor + 1}"
    
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
