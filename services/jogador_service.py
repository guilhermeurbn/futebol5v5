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

    def listar_por_usuario(self, user_id: str) -> List[Jogador]:
        """Lista apenas jogadores vinculados ao usuário."""
        if not user_id:
            return []
        return [j for j in self.listar() if j.owner_user_id == user_id]
    
    def listar_para_dict(self) -> List[dict]:
        """Lista todos os jogadores como dicionários"""
        return self._carregar_raw()

    def listar_dict_por_usuario(self, user_id: str) -> List[dict]:
        """Lista jogadores em dict de um usuário específico."""
        if not user_id:
            return []
        return [j for j in self._carregar_raw() if j.get("owner_user_id") == user_id]
    
    def obter_por_id(self, jogador_id: str, user_id: Optional[str] = None) -> Optional[Jogador]:
        """Obtém um jogador por ID"""
        jogadores = self.listar()
        if user_id:
            return next((j for j in jogadores if j.id == jogador_id and j.owner_user_id == user_id), None)
        return next((j for j in jogadores if j.id == jogador_id), None)
    
    def criar(
        self,
        nome: str,
        nivel: int,
        tipo: str = "avulso",
        posicao: str = "linha",
        owner_user_id: Optional[str] = None
    ) -> Jogador:
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
        jogador = Jogador(
            nome=nome.strip(),
            nivel=nivel,
            tipo=tipo,
            posicao=posicao,
            owner_user_id=owner_user_id
        )
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
            tipo=jogador_existente.tipo,
            posicao=jogador_existente.posicao,
            presente=jogador_existente.presente,
            id=jogador_id,
            criado_em=jogador_existente.criado_em,
            owner_user_id=jogador_existente.owner_user_id
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
