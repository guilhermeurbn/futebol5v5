"""
Serviço de Jogadores - Gerenciamento de dados
"""
import json
import os
from typing import List, Tuple, Optional
from models.jogadores import Jogador


class JogadorService:
    """Serviço para gerenciar jogadores"""
    
    def __init__(self, arquivo: str = "jogadores.json"):
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
        """Carrega dados brutos do arquivo"""
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados no arquivo"""
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    
    def listar(self) -> List[Jogador]:
        """Lista todos os jogadores"""
        dados = self._carregar_raw()
        return [Jogador.do_dict(item) for item in dados]
    
    def listar_para_dict(self) -> List[dict]:
        """Lista todos os jogadores como dicionários"""
        return self._carregar_raw()
    
    def obter_por_id(self, jogador_id: str) -> Optional[Jogador]:
        """Obtém um jogador por ID"""
        jogadores = self.listar()
        return next((j for j in jogadores if j.id == jogador_id), None)
    
    def criar(self, nome: str, nivel: int, tipo: str = "avulso", posicao: str = "linha") -> Jogador:
        """
        Cria um novo jogador
        
        Args:
            nome: Nome do jogador
            nivel: Nível de habilidade (1-10)
            tipo: 'fixo' ou 'avulso'
            posicao: 'linha' ou 'goleiro'
            
        Returns:
            Jogador criado
        """
        jogador = Jogador(nome=nome.strip(), nivel=nivel, tipo=tipo, posicao=posicao)
        dados = self._carregar_raw()
        dados.append(jogador.para_dict())
        self._salvar(dados)
        return jogador
    
    def atualizar(self, jogador_id: str, nome: str, nivel: int) -> Optional[Jogador]:
        """
        Atualiza um jogador
        
        Args:
            jogador_id: ID do jogador
            nome: Novo nome
            nivel: Novo nível
            
        Returns:
            Jogador atualizado ou None
        """
        jogador_existente = self.obter_por_id(jogador_id)
        if not jogador_existente:
            return None
        
        jogador_atualizado = Jogador(
            nome=nome.strip(),
            nivel=nivel,
            id=jogador_id,
            criado_em=jogador_existente.criado_em
        )
        
        dados = self._carregar_raw()
        dados = [
            jogador_atualizado.para_dict() if item["id"] == jogador_id else item
            for item in dados
        ]
        self._salvar(dados)
        return jogador_atualizado
    
    def deletar(self, jogador_id: str) -> bool:
        """
        Deleta um jogador
        
        Args:
            jogador_id: ID do jogador
            
        Returns:
            True se deletado, False se não encontrado
        """
        dados = self._carregar_raw()
        dados_filtrados = [j for j in dados if j["id"] != jogador_id]
        
        if len(dados_filtrados) == len(dados):
            return False
        
        self._salvar(dados_filtrados)
        return True
    
    def contar(self) -> int:
        """Retorna número de jogadores"""
        return len(self.listar())
    
    def listar_presentes(self) -> List[Jogador]:
        """Lista apenas jogadores marcados como presentes"""
        return [j for j in self.listar() if j.presente]
    
    def listar_por_tipo(self, tipo: str) -> List[Jogador]:
        """
        Lista jogadores por tipo
        
        Args:
            tipo: 'fixo' ou 'avulso'
            
        Returns:
            Lista de jogadores do tipo
        """
        if tipo not in ["fixo", "avulso"]:
            raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
        
        return [j for j in self.listar() if j.tipo == tipo]
    
    def marcar_presenca(self, jogador_ids: List[str]) -> bool:
        """
        Marca jogadores como presentes (desseleciona os demais)
        
        Args:
            jogador_ids: Lista de IDs dos jogadores presentes
            
        Returns:
            True se atualizado
        """
        dados = self._carregar_raw()
        ids_set = set(jogador_ids)
        
        for item in dados:
            item["presente"] = item["id"] in ids_set
        
        self._salvar(dados)
        return True
    
    def limpar_presenca(self) -> bool:
        """
        Marca todos como ausentes
        
        Returns:
            True se atualizado
        """
        dados = self._carregar_raw()
        for item in dados:
            item["presente"] = False
        self._salvar(dados)
        return True
    
    def contar_presentes(self) -> int:
        """Retorna número de jogadores presentes"""
        return len(self.listar_presentes())
