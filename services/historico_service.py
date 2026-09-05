"""
Serviço de Histórico de Sorteios
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from models.jogadores import Jogador
from services.db import load_json_data, save_json_data


class HistoricoService:
    """Serviço para gerenciar histórico de sorteios"""
    
    def __init__(self, arquivo: str = "data/historico.json"):
        """
        Inicializa o serviço
        
        Args:
            arquivo: Caminho do arquivo JSON
        """
        self.arquivo = arquivo
        self._garantir_arquivo()
    
    def _garantir_arquivo(self) -> None:
        """Garante que o arquivo existe"""
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar([])
    
    def _carregar_raw(self) -> List[dict]:
        """Carrega dados brutos do histórico"""
        return load_json_data("historico", [])
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados no histórico e invalida estatísticas"""
        save_json_data("historico", dados)
        from services.jogador_stats_service import JogadorStatsService
        JogadorStatsService.invalidar_cache_stats()
    
    def adicionar_sorteio(self, times: List[List[Jogador]], somas: List[int], num_times: int, diferenca: int) -> Dict:
        """
        Adiciona um novo sorteio ao histórico
        
        Args:
            times: Lista de times
            somas: Lista de pontuações
            num_times: Número de times
            diferenca: Diferença entre times
            
        Returns:
            Dicionário do sorteio adicionado
        """
        dados = self._carregar_raw()
        
        times_processados = []
        for idx, time in enumerate(times):
            jogadores_raw = time.get('jogadores', []) if isinstance(time, dict) else time
            jogadores_dict = [j.para_dict() if hasattr(j, 'para_dict') else (j if isinstance(j, dict) else {'nome': str(j)}) for j in jogadores_raw]
            soma_val = somas[idx] if idx < len(somas) else 0
            times_processados.append({
                "numero": idx + 1,
                "jogadores": jogadores_dict,
                "soma": soma_val
            })

        total_j = sum(len(t["jogadores"]) for t in times_processados)

        novo_id = max([int(s.get("id", 0) or 0) for s in dados], default=0) + 1
        sorteio = {
            "id": novo_id,
            "data": datetime.now().isoformat(),
            "rascunho": False,
            "oficial": True,
            "num_times": num_times,
            "total_jogadores": total_j,
            "times": times_processados,
            "diferenca": diferenca,
            "pontuacoes": somas
        }
        
        dados.append(sorteio)
        self._salvar(dados)
        return sorteio

    def substituir_sorteio(self, sorteio_id: int, times: List[List[Jogador]], somas: List[int], num_times: int, diferenca: int) -> Dict:
        """
        Substitui os dados de um sorteio existente mantendo seu ID.
        Ideal para quando o juiz altera a seleção ou refaz o sorteio antes de registrar resultados.
        """
        dados = self._carregar_raw()
        sorteio_id_int = int(sorteio_id)
        
        for idx, s in enumerate(dados):
            if int(s.get('id', 0) or 0) == sorteio_id_int:
                sorteio_atualizado = {
                    "id": sorteio_id_int,
                    "data": datetime.now().isoformat(),
                    "rascunho": s.get('rascunho', True),
                    "oficial": s.get('oficial', False),
                    "num_times": num_times,
                    "total_jogadores": sum(len(time) for time in times),
                    "times": [
                        {
                            "numero": i + 1,
                            "jogadores": [j.para_dict() for j in time],
                            "soma": somas[i]
                        }
                        for i, time in enumerate(times)
                    ],
                    "diferenca": diferenca,
                    "pontuacoes": somas
                }
                dados[idx] = sorteio_atualizado
                self._salvar(dados)
                return sorteio_atualizado

        return self.adicionar_sorteio(times, somas, num_times, diferenca)
    
    def listar_sorteios(self) -> List[Dict]:
        """Lista todos os sorteios"""
        return self._carregar_raw()
    
    def obter_sorteio(self, sorteio_id: int) -> Optional[Dict]:
        """Obtém um sorteio por ID"""
        sorteios = self.listar_sorteios()
        return next((s for s in sorteios if str(s.get('id')) == str(sorteio_id)), None)

    def atualizar_times_sorteio(self, sorteio_id: int, times: List[Dict]) -> Optional[Dict]:
        """Atualiza os times de um sorteio e recalcula metadados derivados."""
        dados = self._carregar_raw()

        for idx, sorteio in enumerate(dados):
            if int(sorteio.get('id', 0) or 0) != int(sorteio_id):
                continue

            pontuacoes = []
            total_jogadores = 0
            for time in times:
                jogadores = time.get('jogadores', []) or []
                soma_time = round(sum(float(j.get('nivel', 0) or 0) for j in jogadores), 2)
                pontuacoes.append(soma_time)
                total_jogadores += len(jogadores)

            diferenca = 0
            if pontuacoes:
                diferenca = max(pontuacoes) - min(pontuacoes)

            sorteio['times'] = times
            sorteio['pontuacoes'] = pontuacoes
            sorteio['diferenca'] = diferenca
            sorteio['num_times'] = len(times)
            sorteio['total_jogadores'] = total_jogadores
            sorteio['data_atualizacao'] = datetime.now().isoformat()

            dados[idx] = sorteio
            self._salvar(dados)
            return sorteio

        return None
    
    def deletar_sorteio(self, sorteio_id: int) -> bool:
        """Deleta um sorteio sem reindexar IDs dos sorteios restantes"""
        dados = self._carregar_raw()
        original_len = len(dados)
        sorteio_id_int = int(sorteio_id)
        dados = [s for s in dados if int(s.get('id', 0) or 0) != sorteio_id_int]
        
        if len(dados) < original_len:
            self._salvar(dados)
            return True
        return False
    
    def obter_estatisticas(self) -> Dict:
        """Calcula estatísticas dos sorteios"""
        sorteios = self.listar_sorteios()
        
        if not sorteios:
            return {
                "total_sorteios": 0,
                "media_jogadores": 0,
                "media_diferenca": 0,
                "melhor_balanceamento": None,
                "times_mais_frequentes": {}
            }
        
        diferenças = [s.get('diferenca', 0) for s in sorteios]
        total_jogadores = [s.get('total_jogadores', 0) for s in sorteios]
        
        # Contar frequência de jogadores em cada time
        jogadores_times = {}
        for sorteio in sorteios:
            for time_data in sorteio.get('times', []):
                for jogador in time_data.get('jogadores', []):
                    nome = jogador.get('nome')
                    if nome:
                        if nome not in jogadores_times:
                            jogadores_times[nome] = 0
                        jogadores_times[nome] += 1
        
        # Ordenar por frequência
        top_jogadores = sorted(jogadores_times.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_sorteios": len(sorteios),
            "media_jogadores": sum(total_jogadores) / len(total_jogadores) if total_jogadores else 0,
            "media_diferenca": sum(diferenças) / len(diferenças) if diferenças else 0,
            "melhor_balanceamento": min(diferenças) if diferenças else None,
            "pior_balanceamento": max(diferenças) if diferenças else None,
            "jogadores_frequentes": [{"nome": nome, "vezes": vezes} for nome, vezes in top_jogadores]
        }
