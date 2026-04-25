"""
Serviço de Partidas e Resultados Competitivos
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class PartidaService:
    """Serviço para gerenciar partidas e resultados competitivos"""
    
    def __init__(self, arquivo: str = "partidas.json"):
        """
        Inicializa o serviço
        
        Args:
            arquivo: Caminho do arquivo JSON
        """
        self.arquivo = arquivo
        self._garantir_arquivo()
    
    def _garantir_arquivo(self) -> None:
        """Garante que o arquivo existe"""
        if not os.path.exists(self.arquivo):
            self._salvar([])
    
    def _carregar_raw(self) -> List[dict]:
        """Carrega dados brutos"""
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados"""
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
    def registrar_resultado(self, sorteio_id: int, time_vencedor: int,
                           gols_times: List[int], notas: str = "",
                           times_desempenho: Optional[List[Dict]] = None) -> Dict:
        """
        Registra o resultado de uma partida
        
        Args:
            sorteio_id: ID do sorteio
            time_vencedor: Número do time vencedor (1, 2, etc)
            gols_times: Lista com gols de cada time
            notas: Observações sobre a partida
            times_desempenho: Lista com vitorias/empates/derrotas por time
            
        Returns:
            Dicionário com a partida registrada
        """
        partidas = self._carregar_raw()
        
        partida = {
            "id": len(partidas) + 1,
            "sorteio_id": sorteio_id,
            "data": datetime.now().isoformat(),
            "time_vencedor": time_vencedor,
            "gols_times": gols_times,
            "notas": notas,
            "times_desempenho": times_desempenho or []
        }
        
        partidas.append(partida)
        self._salvar(partidas)
        return partida
    
    def obter_partidas_sorteio(self, sorteio_id: int) -> List[Dict]:
        """Obtém todas as partidas de um sorteio"""
        partidas = self._carregar_raw()
        return [p for p in partidas if p.get('sorteio_id') == sorteio_id]
    
    def obter_campeonato(self) -> Dict:
        """
        Calcula estatísticas de campeonato
        
        Returns:
            {
                "times_vencedores": {...},
                "jogadores_campeoes": [...],
                "maior_placar": {...},
                "total_partidas": int
            }
        """
        partidas = self._carregar_raw()
        
        if not partidas:
            return {
                "times_vencedores": {},
                "jogadores_campeoes": [],
                "maior_placar": None,
                "total_partidas": 0
            }
        
        # Contar vitórias por time vencedor
        times_vitoriosos = {}
        for partida in partidas:
            time_venc = partida.get('time_vencedor')
            if time_venc:
                times_vitoriosos[time_venc] = times_vitoriosos.get(time_venc, 0) + 1
        
        # Encontrar maior placar
        maior_placar = None
        maior_diferenca = 0
        for partida in partidas:
            gols = partida.get('gols_times', [])
            if len(gols) >= 2:
                diferenca = abs(gols[0] - gols[1])
                if diferenca > maior_diferenca:
                    maior_diferenca = diferenca
                    maior_placar = {
                        "gols": gols,
                        "data": partida.get('data'),
                        "diferenca": diferenca
                    }
        
        return {
            "times_vencedores": times_vitoriosos,
            "maior_placar": maior_placar,
            "total_partidas": len(partidas),
            "maior_diferenca": maior_diferenca
        }
    
    def listar_partidas(self, limite: int = 10) -> List[Dict]:
        """Lista as últimas partidas"""
        partidas = self._carregar_raw()
        return sorted(partidas, key=lambda x: x.get('data', ''), reverse=True)[:limite]
    
    def obter_placar_geral(self) -> Dict:
        """
        Retorna o placar geral de um campeonato
        
        Returns:
            {
                "time_1": {"vitórias": 0, "derrotas": 0},
                "time_2": {"vitórias": 0, "derrotas": 0},
                ...
            }
        """
        partidas = self._carregar_raw()
        placar = {}
        
        for partida in partidas:
            time_venc = partida.get('time_vencedor')
            num_times = len(partida.get('gols_times', []))
            
            # Inicializar times se não existem
            for i in range(1, num_times + 1):
                time_key = f"time_{i}"
                if time_key not in placar:
                    placar[time_key] = {"vitórias": 0, "derrotas": 0}
            
            # Contar vitória/derrota
            for i in range(1, num_times + 1):
                time_key = f"time_{i}"
                if i == time_venc:
                    placar[time_key]["vitórias"] += 1
                else:
                    placar[time_key]["derrotas"] += 1
        
        return placar
