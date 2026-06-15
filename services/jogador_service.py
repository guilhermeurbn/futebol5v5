"""
Serviço de Jogadores - Gerenciamento de dados
"""
import json
import os
from typing import List, Tuple, Optional
from models.jogadores import Jogador
from services.db import load_json_data, save_json_data


class JogadorService:
    """Serviço para gerenciar jogadores - com suporte a Postgres via db.py"""
    
    def __init__(self, arquivo: str = "data/jogadores.json"):
        """
        Inicializa o serviço
        
        Args:
            arquivo: Caminho do arquivo JSON (fallback se sem Postgres)
        """
        self.arquivo = arquivo
        self.namespace = "jogadores"
        self._garantir_arquivo()
    
    def _garantir_arquivo(self) -> None:
        """Garante que o arquivo existe como fallback"""
        if not os.path.exists(self.arquivo):
            with open(self.arquivo, "w", encoding="utf-8") as f:
                json.dump([], f)
    
    def _carregar_raw(self) -> List[dict]:
        """Carrega dados brutos do banco de dados ou arquivo local"""
        data = load_json_data(self.namespace, None)
        if data is not None:
            return data if isinstance(data, list) else []
        
        # Fallback: carrega do arquivo local se banco falhar
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados no banco de dados (Postgres ou arquivo local)"""
        save_json_data(self.namespace, dados)
    
    
    def listar(self) -> List[Jogador]:
        """Lista todos os jogadores"""
        dados = self._carregar_raw()
        return [Jogador.do_dict(item) for item in dados]

    def listar_por_usuario(self, user_id: str) -> List[Jogador]:
        """Lista apenas jogadores vinculados ao usuário."""
        if not user_id:
            return []
        return [Jogador.do_dict(item) for item in self._carregar_raw() if item.get("owner_user_id") == user_id]
    
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
        for item in self._carregar_raw():
            if item.get("id") != jogador_id:
                continue
            if user_id and item.get("owner_user_id") != user_id:
                return None
            return Jogador.do_dict(item)
        return None
    
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
        # Validar nível (float 0.0-10.0)
        try:
            nivel = round(float(nivel), 2)
        except (TypeError, ValueError):
            raise ValueError(f"Nível inválido: deve ser um número, recebido: {nivel}")
        if not (0.0 <= nivel <= 10.0):
            raise ValueError(f"Nível deve estar entre 0.0 e 10.0, recebido: {nivel}")
        
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
    
    def atualizar(
        self,
        jogador_id: str,
        nome: Optional[str] = None,
        nivel: Optional[int] = None,
        tipo: Optional[str] = None,
        posicao: Optional[str] = None,
    ) -> Optional[Jogador]:
        """
        Atualiza um jogador com campos opcionais.

        Args:
            jogador_id: ID do jogador
            nome: Novo nome (opcional)
            nivel: Novo nível (opcional)
            tipo: 'fixo' ou 'avulso' (opcional)
            posicao: 'linha' ou 'goleiro' (opcional)

        Returns:
            Jogador atualizado ou None
        """
        dados = self._carregar_raw()
        indice = next((i for i, item in enumerate(dados) if item.get("id") == jogador_id), None)
        if indice is None:
            return None

        jogador_existente = Jogador.do_dict(dados[indice])

        # Validate optional fields
        novo_nome = nome.strip() if isinstance(nome, str) and nome.strip() else jogador_existente.nome

        if nivel is not None:
            try:
                novo_nivel = round(float(nivel), 2)
            except (TypeError, ValueError):
                raise ValueError(f"Nível inválido: deve ser um número, recebido: {nivel}")
            if not (0.0 <= novo_nivel <= 10.0):
                raise ValueError(f"Nível deve estar entre 0.0 e 10.0, recebido: {novo_nivel}")
        else:
            novo_nivel = jogador_existente.nivel

        novo_tipo = jogador_existente.tipo
        if tipo is not None:
            if tipo not in ("fixo", "avulso"):
                raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
            novo_tipo = tipo

        nova_posicao = jogador_existente.posicao
        if posicao is not None:
            if posicao not in ("linha", "goleiro"):
                raise ValueError("Posição deve ser 'linha' ou 'goleiro'")
            nova_posicao = posicao

        jogador_atualizado = Jogador(
            nome=novo_nome,
            nivel=novo_nivel,
            tipo=novo_tipo,
            posicao=nova_posicao,
            presente=jogador_existente.presente,
            id=jogador_id,
            criado_em=jogador_existente.criado_em,
            owner_user_id=jogador_existente.owner_user_id,
            historico_nivel=jogador_existente.historico_nivel or [],
        )

        dados[indice] = jogador_atualizado.para_dict()
        self._salvar(dados)
        return jogador_atualizado

    def obter_por_nome(self, nome: str) -> Optional['Jogador']:
        """Busca jogador pelo nome exato (case-insensitive)."""
        nome_clean = nome.strip().lower()
        for item in self._carregar_raw():
            if item.get("nome", "").strip().lower() == nome_clean:
                return Jogador.do_dict(item)
        return None

    def aplicar_evolucao_nivel(
        self,
        jogador_id: str,
        novo_nivel: float,
        motivo: str = "votacao",
        nivel_anterior: Optional[float] = None,
        nota_media: Optional[float] = None,
    ) -> Optional['Jogador']:
        """Aplica evolução de nível baseada em votação e registra histórico."""
        from datetime import datetime
        dados = self._carregar_raw()
        indice = next((i for i, item in enumerate(dados) if item.get("id") == jogador_id), None)
        if indice is None:
            return None

        item = dados[indice]
        nivel_ant = nivel_anterior if nivel_anterior is not None else float(item.get("nivel", 5))
        novo_nivel_clamped = round(max(0.0, min(10.0, float(novo_nivel))), 2)

        historico = list(item.get("historico_nivel") or [])
        historico.append({
            "ts": datetime.now().isoformat(),
            "nivel_anterior": nivel_ant,
            "nivel_novo": novo_nivel_clamped,
            "motivo": motivo,
            "nota_media": nota_media,
        })
        historico = historico[-50:]  # manter últimos 50 registros

        item["nivel"] = novo_nivel_clamped
        item["historico_nivel"] = historico
        dados[indice] = item
        self._salvar(dados)
        return Jogador.do_dict(item)
    
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
        return len(self._carregar_raw())
    
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

        if all(bool(item.get("presente")) == (item.get("id") in ids_set) for item in dados):
            return True
        
        dados_atualizados = [
            {**item, "presente": item.get("id") in ids_set}
            for item in dados
        ]
        
        self._salvar(dados_atualizados)
        return True
    
    def limpar_presenca(self) -> bool:
        """
        Marca todos como ausentes
        
        Returns:
            True se atualizado
        """
        dados = self._carregar_raw()
        if not any(item.get("presente") for item in dados):
            return True

        self._salvar([{**item, "presente": False} for item in dados])
        return True
    
    def contar_presentes(self) -> int:
        """Retorna número de jogadores presentes"""
        return sum(1 for item in self._carregar_raw() if item.get("presente"))
