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
    
    def __init__(self, arquivo: str = "data/partidas.json"):
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
        """Carrega dados de partidas"""
        return load_json_data("partidas", [])
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados de partidas e invalida estatísticas"""
        save_json_data("partidas", dados)
        from services.jogador_stats_service import JogadorStatsService
        JogadorStatsService.invalidar_cache_stats()

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
    
    def registrar_resultado(self, sorteio_id: int, time_vencedor: Optional[int],
                           gols_times: List[int], notas: str = "",
                           times_desempenho: Optional[List[Dict]] = None,
                           card_campeao_url: Optional[str] = None) -> Dict:
        """
        Registra o resultado de uma partida
        
        Args:
            sorteio_id: ID do sorteio
            time_vencedor: Número do time vencedor (1, 2, etc)
            gols_times: Lista com gols de cada time
            notas: Observações sobre a partida
            times_desempenho: Lista com vitorias/empates/derrotas por time
            card_campeao_url: URL da foto/card do time campeão com moldura
            
        Returns:
            Dicionário com a partida registrada
        """
        partidas = self._carregar_raw()
        
        existente = next((p for p in partidas if int(p.get("sorteio_id", 0) or 0) == int(sorteio_id)), None)
        if existente:
            existente["time_vencedor"] = time_vencedor
            existente["gols_times"] = gols_times
            existente["notas"] = notas
            existente["times_desempenho"] = times_desempenho or []
            if card_campeao_url:
                existente["card_campeao_url"] = card_campeao_url
            existente["atualizado_em"] = datetime.now().isoformat()
            partida = existente
        else:
            ultimo_id = max((int(p.get("id", 0) or 0) for p in partidas), default=0)
            partida = {
                "id": ultimo_id + 1,
                "sorteio_id": sorteio_id,
                "data": datetime.now().isoformat(),
                "time_vencedor": time_vencedor,
                "gols_times": gols_times,
                "notas": notas,
                "times_desempenho": times_desempenho or [],
                "card_campeao_url": card_campeao_url or ""
            }
            partidas.append(partida)

        self._salvar(partidas)
        return partida
    
    def obter_partidas_sorteio(self, sorteio_id: int) -> List[Dict]:
        """Obtém todas as partidas de um sorteio"""
        partidas = self._carregar_raw()
        try:
            s_id_int = int(sorteio_id)
        except (ValueError, TypeError):
            s_id_int = None
        return [
            p for p in partidas
            if (s_id_int is not None and int(p.get('sorteio_id', 0) or 0) == s_id_int)
            or str(p.get('sorteio_id')) == str(sorteio_id)
        ]

    def atualizar_foto_campeao(self, sorteio_id: int, card_campeao_url: str) -> Dict:
        """Atualiza a foto/card do time campeão de um sorteio existente ou cria registro."""
        partidas = self._carregar_raw()
        sorteio_id_int = int(sorteio_id)
        existente = next((p for p in partidas if int(p.get("sorteio_id", 0) or 0) == sorteio_id_int), None)
        
        if existente:
            existente["card_campeao_url"] = card_campeao_url
            existente["atualizado_em"] = datetime.now().isoformat()
            self._salvar(partidas)
            return existente
        else:
            ultimo_id = max((int(p.get("id", 0) or 0) for p in partidas), default=0)
            partida = {
                "id": ultimo_id + 1,
                "sorteio_id": sorteio_id_int,
                "data": datetime.now().isoformat(),
                "time_vencedor": None,
                "gols_times": [],
                "notas": "Atualizado pelo Admin",
                "times_desempenho": [],
                "card_campeao_url": card_campeao_url
            }
            partidas.append(partida)
            self._salvar(partidas)
            return partida
    
    def listar_partidas(self, limite: int = 10) -> List[Dict]:
        """Lista as últimas partidas"""
        partidas = self._carregar_raw()
        return sorted(partidas, key=lambda x: x.get('data', ''), reverse=True)[:limite]

    def deletar_partida_do_sorteio(self, sorteio_id: int) -> bool:
        """Deleta partidas/resultados vinculados a um sorteio_id"""
        partidas = self._carregar_raw()
        sorteio_id_int = int(sorteio_id)
        filtradas = [
            p for p in partidas
            if int(p.get('sorteio_id', 0) or 0) != sorteio_id_int and int(p.get('id', 0) or 0) != sorteio_id_int
        ]
        if len(filtradas) != len(partidas):
            self._salvar(filtradas)
            return True
        return False

    def editar_resultado_partida(self, sorteio_id: int, times_desempenho: List[Dict]) -> Dict:
        """
        Edita os resultados de desempenho (vitórias, empates, derrotas, gols) dos times
        de um sorteio existente e recalcula o time vencedor. Suporta dinamicamente de 2 a 4 times.
        """
        partidas = self._carregar_raw()
        try:
            sorteio_id_int = int(sorteio_id)
        except (ValueError, TypeError):
            sorteio_id_int = None

        existente = next(
            (
                p for p in partidas
                if (sorteio_id_int is not None and int(p.get("sorteio_id", 0) or 0) == sorteio_id_int)
                or (sorteio_id_int is not None and int(p.get("id", 0) or 0) == sorteio_id_int)
                or str(p.get("sorteio_id")) == str(sorteio_id)
            ),
            None
        )

        desempenho_formatado = []
        for item in times_desempenho:
            desempenho_formatado.append({
                "time_numero": int(item.get("time_numero", 0)),
                "vitorias": int(item.get("vitorias", 0) or 0),
                "empates": int(item.get("empates", 0) or 0),
                "derrotas": int(item.get("derrotas", 0) or 0),
                "gols": int(item.get("gols", 0) or 0),
            })
        desempenho_formatado.sort(key=lambda x: x["time_numero"])

        maiores_vitorias = max((item["vitorias"] for item in desempenho_formatado), default=0)
        lideres = [
            item["time_numero"]
            for item in desempenho_formatado
            if maiores_vitorias > 0 and item["vitorias"] == maiores_vitorias
        ]
        time_vencedor = lideres[0] if len(lideres) == 1 else None
        gols_times = [item["gols"] for item in desempenho_formatado]

        if not existente:
            novo_id = max([int(p.get("id", 0) or 0) for p in partidas], default=0) + 1
            existente = {
                "id": novo_id,
                "sorteio_id": sorteio_id_int if sorteio_id_int is not None else sorteio_id,
                "data": datetime.now().isoformat(),
                "time_vencedor": time_vencedor,
                "gols_times": gols_times,
                "notas": "",
                "times_desempenho": desempenho_formatado,
                "jogadores_detalhes": []
            }
            partidas.append(existente)
        else:
            existente["times_desempenho"] = desempenho_formatado
            existente["time_vencedor"] = time_vencedor
            existente["gols_times"] = gols_times
            existente["atualizado_em"] = datetime.now().isoformat()

        self._salvar(partidas)
        return existente

