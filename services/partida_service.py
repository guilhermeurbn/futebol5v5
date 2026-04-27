"""
Serviço de Partidas e Resultados Competitivos
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from services.db import load_json_data, save_json_data


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
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar([])
    
    def _carregar_raw(self) -> List[dict]:
        """Carrega dados brutos"""
        if os.getenv("DATABASE_URL"):
            return load_json_data("partidas", [])
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados"""
        if os.getenv("DATABASE_URL"):
            save_json_data("partidas", dados)
            return
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def _garantir_stats_time(self, placar: Dict, time_numero: int) -> None:
        """Garante estrutura padrão de estatísticas para um time."""
        chave = f"time_{time_numero}"
        if chave not in placar:
            placar[chave] = {"vitórias": 0, "empates": 0, "derrotas": 0}

    def _diferenca_placar(self, gols_times: List[int]) -> int:
        """Calcula a maior diferença de gols entre quaisquer dois times."""
        if len(gols_times) < 2:
            return 0
        diferencas = []
        for i, gols_a in enumerate(gols_times):
            for gols_b in gols_times[i + 1:]:
                diferencas.append(abs(gols_a - gols_b))
        return max(diferencas, default=0)
    
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
                diferenca = self._diferenca_placar(gols)
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
            desempenho = partida.get('times_desempenho') or []
            if desempenho:
                for item in desempenho:
                    time_numero = int(item.get('time_numero', 0) or 0)
                    if time_numero <= 0:
                        continue
                    self._garantir_stats_time(placar, time_numero)
                    chave = f"time_{time_numero}"
                    placar[chave]["vitórias"] += int(item.get('vitorias', 0) or 0)
                    placar[chave]["empates"] += int(item.get('empates', 0) or 0)
                    placar[chave]["derrotas"] += int(item.get('derrotas', 0) or 0)
                continue

            time_venc = partida.get('time_vencedor')
            num_times = len(partida.get('gols_times', []))

            for i in range(1, num_times + 1):
                self._garantir_stats_time(placar, i)

            if not time_venc:
                for i in range(1, num_times + 1):
                    placar[f"time_{i}"]["empates"] += 1
                continue

            for i in range(1, num_times + 1):
                time_key = f"time_{i}"
                if i == time_venc:
                    placar[time_key]["vitórias"] += 1
                else:
                    placar[time_key]["derrotas"] += 1
        
        return placar
