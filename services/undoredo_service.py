"""
Serviço de Undo/Redo para Sorteios
"""
import json
import os
from typing import List, Dict, Optional, Tuple
from services.db import load_json_data, save_json_data


class UndoRedoService:
    """Serviço para gerenciar pilha de sorteios (undo/redo)"""
    
    def __init__(self, arquivo: str = "sorteios_stack.json"):
        """
        Inicializa o serviço
        
        Args:
            arquivo: Caminho do arquivo JSON
        """
        self.arquivo = arquivo
        self.max_historico = 10  # Guardar máximo 10 sorteios
        self._garantir_arquivo()
    
    def _garantir_arquivo(self) -> None:
        """Garante que o arquivo existe"""
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar({"pilha": [], "indice_atual": -1})

    def _normalizar_dados(self, dados) -> Dict:
        """Normaliza estrutura legado/lista para o formato esperado de pilha."""
        if isinstance(dados, dict):
            pilha = dados.get("pilha", [])
            if not isinstance(pilha, list):
                pilha = []

            indice_atual = dados.get("indice_atual", len(pilha) - 1)
            if not isinstance(indice_atual, int):
                indice_atual = len(pilha) - 1

            if not pilha:
                indice_atual = -1
            else:
                indice_atual = max(-1, min(indice_atual, len(pilha) - 1))

            return {"pilha": pilha, "indice_atual": indice_atual}

        # Formato legado: arquivo/db armazenado apenas como lista
        if isinstance(dados, list):
            return {
                "pilha": dados,
                "indice_atual": len(dados) - 1 if dados else -1,
            }

        return {"pilha": [], "indice_atual": -1}
    
    def _carregar_raw(self) -> Dict:
        """Carrega dados brutos"""
        if os.getenv("DATABASE_URL"):
            dados = load_json_data("sorteios_stack", {"pilha": [], "indice_atual": -1})
            dados = self._normalizar_dados(dados)
            return dados
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
                dados_normalizados = self._normalizar_dados(dados)

                # Migra automaticamente arquivo legado para estrutura nova
                if dados != dados_normalizados:
                    self._salvar(dados_normalizados)

                return dados_normalizados
        except (json.JSONDecodeError, FileNotFoundError):
            return {"pilha": [], "indice_atual": -1}
    
    def _salvar(self, dados: Dict) -> None:
        """Salva dados"""
        if os.getenv("DATABASE_URL"):
            save_json_data("sorteios_stack", dados)
            return
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
    def adicionar_sorteio(self, sorteio_data: Dict) -> Tuple[int, int]:
        """
        Adiciona um novo sorteio à pilha
        
        Args:
            sorteio_data: Dados do sorteio (times, somas, etc)
            
        Returns:
            Tupla (posicao_atual, total_sorteios)
        """
        dados = self._carregar_raw()
        pilha = dados.get("pilha", [])
        indice_atual = dados.get("indice_atual", -1)
        
        # Se não estamos no final, remover tudo após o índice atual
        # (Ao fazer um novo sorteio depois de undo, removemos o redo)
        if indice_atual < len(pilha) - 1:
            pilha = pilha[:indice_atual + 1]
        
        # Adicionar novo sorteio
        pilha.append(sorteio_data)
        indice_atual += 1
        
        # Manter apenas os últimos N sorteios
        if len(pilha) > self.max_historico:
            pilha = pilha[-self.max_historico:]
            indice_atual = len(pilha) - 1
        
        dados["pilha"] = pilha
        dados["indice_atual"] = indice_atual
        self._salvar(dados)
        
        return (indice_atual, len(pilha))
    
    def pode_undo(self) -> bool:
        """Verifica se pode fazer undo"""
        dados = self._carregar_raw()
        return dados.get("indice_atual", -1) > 0
    
    def pode_redo(self) -> bool:
        """Verifica se pode fazer redo"""
        dados = self._carregar_raw()
        pilha = dados.get("pilha", [])
        indice_atual = dados.get("indice_atual", -1)
        return indice_atual < len(pilha) - 1
    
    def undo(self) -> Optional[Dict]:
        """
        Volta para o sorteio anterior
        
        Returns:
            Dados do sorteio anterior ou None
        """
        dados = self._carregar_raw()
        indice_atual = dados.get("indice_atual", -1)
        
        if indice_atual <= 0:
            return None
        
        indice_atual -= 1
        dados["indice_atual"] = indice_atual
        self._salvar(dados)
        
        pilha = dados.get("pilha", [])
        return pilha[indice_atual] if indice_atual < len(pilha) else None
    
    def redo(self) -> Optional[Dict]:
        """
        Avança para o próximo sorteio
        
        Returns:
            Dados do sorteio seguinte ou None
        """
        dados = self._carregar_raw()
        pilha = dados.get("pilha", [])
        indice_atual = dados.get("indice_atual", -1)
        
        if indice_atual >= len(pilha) - 1:
            return None
        
        indice_atual += 1
        dados["indice_atual"] = indice_atual
        self._salvar(dados)
        
        return pilha[indice_atual]
    
    def obter_atual(self) -> Optional[Dict]:
        """Obtém o sorteio atual"""
        dados = self._carregar_raw()
        pilha = dados.get("pilha", [])
        indice_atual = dados.get("indice_atual", -1)
        
        if indice_atual < 0 or indice_atual >= len(pilha):
            return None
        
        return pilha[indice_atual]
    
    def obter_historico(self) -> Tuple[List[Dict], int]:
        """
        Obtém histórico de sorteios com índice atual
        
        Returns:
            Tupla (lista_sorteios, indice_atual)
        """
        dados = self._carregar_raw()
        pilha = dados.get("pilha", [])
        indice_atual = dados.get("indice_atual", -1)
        
        return (pilha, indice_atual)
    
    def limpar(self) -> None:
        """Limpa toda a pilha de sorteios"""
        self._salvar({"pilha": [], "indice_atual": -1})
    
    def obter_status(self) -> Dict:
        """Obtém status do undo/redo"""
        dados = self._carregar_raw()
        pilha = dados.get("pilha", [])
        indice_atual = dados.get("indice_atual", -1)
        
        return {
            "total_sorteios": len(pilha),
            "sorteio_atual": indice_atual + 1,
            "pode_undo": indice_atual > 0,
            "pode_redo": indice_atual < len(pilha) - 1,
            "sorteios_apos": len(pilha) - indice_atual - 1
        }
