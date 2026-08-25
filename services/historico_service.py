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
        """Carrega dados brutos do arquivo"""
        if os.getenv("DATABASE_URL"):
            return load_json_data("historico", [])
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados no arquivo"""
        if os.getenv("DATABASE_URL"):
            save_json_data("historico", dados)
            return
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
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
        
        sorteio = {
            "id": len(dados) + 1,
            "data": datetime.now().isoformat(),
            "num_times": num_times,
            "total_jogadores": sum(len(time) for time in times),
            "times": [
                {
                    "numero": idx + 1,
                    "jogadores": [j.para_dict() for j in time],
                    "soma": somas[idx]
                }
                for idx, time in enumerate(times)
            ],
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
        return next((s for s in sorteios if s.get('id') == sorteio_id), None)

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
                soma_time = sum(int(j.get('nivel', 0) or 0) for j in jogadores)
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
        """Deleta um sorteio"""
        dados = self._carregar_raw()
        original_len = len(dados)
        dados = [s for s in dados if s.get('id') != sorteio_id]
        
        if len(dados) < original_len:
            # Reindexar IDs
            for idx, sorteio in enumerate(dados, 1):
                sorteio['id'] = idx
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
