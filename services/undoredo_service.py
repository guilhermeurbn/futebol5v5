"""
Serviço de Undo/Redo para Sorteios
"""
import json
import os
from typing import List, Dict, Optional, Tuple
from services.db import load_json_data, save_json_data


class UndoRedoService:
    """Serviço para gerenciar pilha de sorteios (undo/redo)"""
    
    def __init__(self, arquivo: str = "data/sorteios_stack.json"):
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
    
    def _obter_clube_codigo(self, clube_codigo: Optional[str] = None) -> str:
        if clube_codigo and str(clube_codigo).strip():
            c = str(clube_codigo).strip()
            return c.zfill(3) if c.isdigit() else c
        try:
            from flask import g, session
            if hasattr(g, 'clube_codigo') and g.clube_codigo:
                c = str(g.clube_codigo).strip()
                return c.zfill(3) if c.isdigit() else c
            if session.get('clube_codigo'):
                c = str(session.get('clube_codigo')).strip()
                return c.zfill(3) if c.isdigit() else c
        except Exception:
            pass
        return "001"

    def _carregar_todos(self) -> Dict:
        if os.getenv("DATABASE_URL"):
            raw = load_json_data("sorteios_stack", {})
        else:
            try:
                with open(self.arquivo, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                raw = {}
        if not isinstance(raw, dict):
            raw = {}
        if "pilha" in raw or "indice_atual" in raw or isinstance(raw, list):
            raw = {"001": self._normalizar_dados(raw)}
        return raw

    def _carregar_raw(self, clube_codigo: Optional[str] = None) -> Dict:
        cod = self._obter_clube_codigo(clube_codigo)
        todos = self._carregar_todos()
        clube_stack = todos.get(cod)
        return self._normalizar_dados(clube_stack)
    
    def _salvar(self, dados: Dict, clube_codigo: Optional[str] = None) -> None:
        cod = self._obter_clube_codigo(clube_codigo)
        todos = self._carregar_todos()
        todos[cod] = self._normalizar_dados(dados)
        if os.getenv("DATABASE_URL"):
            save_json_data("sorteios_stack", todos)
            return
        os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)
    
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
