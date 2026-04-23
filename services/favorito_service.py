"""
Serviço de Favoritamento de Times
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class FavoritoService:
    """Serviço para gerenciar times favoritos"""
    
    def __init__(self, arquivo: str = "favoritos.json"):
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
    
    def favoritar_time(self, sorteio_id: int, time_numero: int, 
                      jogadores: List[Dict], pontuacao: int, 
                      nome: str = "") -> Dict:
        """
        Favorita um time específico de um sorteio
        
        Args:
            sorteio_id: ID do sorteio
            time_numero: Número do time (1, 2, etc)
            jogadores: Lista de jogadores do time
            pontuacao: Pontuação total do time
            nome: Nome descritivo do time favorito (opcional)
            
        Returns:
            Dicionário com o time favoritado
        """
        favoritos = self._carregar_raw()
        
        # Gerar nome automático se não fornecido
        if not nome:
            nomes = [j.get('nome') for j in jogadores[:3]]
            nome = " + ".join(nomes)
        
        favorito = {
            "id": len(favoritos) + 1,
            "data": datetime.now().isoformat(),
            "sorteio_id": sorteio_id,
            "time_numero": time_numero,
            "nome": nome,
            "pontuacao": pontuacao,
            "jogadores": jogadores,
            "vezes_utilizado": 0
        }
        
        favoritos.append(favorito)
        self._salvar(favoritos)
        return favorito
    
    def listar_favoritos(self) -> List[Dict]:
        """Lista todos os times favoritos"""
        favoritos = self._carregar_raw()
        # Ordenar por data (mais recentes primeiro)
        return sorted(favoritos, key=lambda x: x.get('data', ''), reverse=True)
    
    def obter_favorito(self, fav_id: int) -> Optional[Dict]:
        """Obtém um favorito específico"""
        favoritos = self._carregar_raw()
        for fav in favoritos:
            if fav.get('id') == fav_id:
                return fav
        return None
    
    def remover_favorito(self, fav_id: int) -> bool:
        """Remove um favorito"""
        favoritos = self._carregar_raw()
        favoritos_filtrado = [f for f in favoritos if f.get('id') != fav_id]
        
        if len(favoritos_filtrado) < len(favoritos):
            self._salvar(favoritos_filtrado)
            return True
        return False
    
    def renomear_favorito(self, fav_id: int, novo_nome: str) -> Optional[Dict]:
        """Renomeia um favorito"""
        favoritos = self._carregar_raw()
        
        for fav in favoritos:
            if fav.get('id') == fav_id:
                fav['nome'] = novo_nome
                self._salvar(favoritos)
                return fav
        return None
    
    def incrementar_uso(self, fav_id: int) -> bool:
        """Incrementa contador de vezes utilizado"""
        favoritos = self._carregar_raw()
        
        for fav in favoritos:
            if fav.get('id') == fav_id:
                fav['vezes_utilizado'] = fav.get('vezes_utilizado', 0) + 1
                self._salvar(favoritos)
                return True
        return False
    
    def obter_estatisticas_favoritos(self) -> Dict:
        """Retorna estatísticas dos favoritos"""
        favoritos = self._carregar_raw()
        
        if not favoritos:
            return {
                "total_favoritos": 0,
                "mais_usado": None,
                "pontuacao_media": 0,
                "favoritos_por_pontuacao": []
            }
        
        total = len(favoritos)
        soma_pontuacao = sum(f.get('pontuacao', 0) for f in favoritos)
        
        # Encontrar mais usado
        mais_usado = max(favoritos, key=lambda x: x.get('vezes_utilizado', 0))
        
        # Ordenar por pontuação
        por_pontuacao = sorted(
            favoritos, 
            key=lambda x: x.get('pontuacao', 0), 
            reverse=True
        )
        
        return {
            "total_favoritos": total,
            "mais_usado": {
                "id": mais_usado.get('id'),
                "nome": mais_usado.get('nome'),
                "vezes_utilizado": mais_usado.get('vezes_utilizado', 0),
                "pontuacao": mais_usado.get('pontuacao')
            },
            "pontuacao_media": round(soma_pontuacao / total, 1),
            "pontuacao_maxima": max(f.get('pontuacao', 0) for f in favoritos),
            "pontuacao_minima": min(f.get('pontuacao', 0) for f in favoritos),
            "favoritos_por_pontuacao": [
                {
                    "id": f.get('id'),
                    "nome": f.get('nome'),
                    "pontuacao": f.get('pontuacao'),
                    "vezes_utilizado": f.get('vezes_utilizado', 0)
                }
                for f in por_pontuacao[:10]
            ]
        }
