"""
Serviço de Jogadores - Gerenciamento de dados
"""
import json
import os
from typing import List, Tuple, Optional
from models.jogadores import Jogador
from services.db import load_json_data, save_json_data


def abreviar_nome(nome: str) -> str:
    if not nome:
        return ""
    partes = [p for p in nome.strip().split() if p]
    if len(partes) <= 1:
        return nome
    first_name = partes[0]
    last_name_initial = partes[1][0].upper()
    return f"{first_name} {last_name_initial}."


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
            dados = data if isinstance(data, list) else []
            return self._enriquecer_fotos(dados)
        
        # Fallback: carrega do arquivo local se banco falhar
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return self._enriquecer_fotos(dados)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _enriquecer_fotos(self, dados: List[dict]) -> List[dict]:
        """Garante que qualquer jogador vinculado a um usuário receba a foto do perfil se não tiver foto própria."""
        if not dados:
            return dados
        try:
            from services.auth_service import AuthService
            usuarios = AuthService()._carregar()
            user_by_id = {u.get("id"): u for u in usuarios if u.get("id")}
            user_by_name = {u.get("nome", "").strip().lower(): u for u in usuarios if u.get("nome")}
            user_by_username = {u.get("username", "").strip().lower(): u for u in usuarios if u.get("username")}

            for item in dados:
                foto = item.get("foto_url")
                if not foto:
                    owner_id = item.get("owner_user_id")
                    nome_key = (item.get("nome") or "").strip().lower()
                    u = user_by_id.get(owner_id) or user_by_name.get(nome_key) or user_by_username.get(nome_key)
                    if u and u.get("foto_url"):
                        item["foto_url"] = u.get("foto_url")
        except Exception:
            pass
        return dados
    
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
        nivel: float = 5.5,
        tipo: str = "avulso",
        posicao: str = "linha",
        owner_user_id: Optional[str] = None
    ) -> Jogador:
        """
        Cria um novo jogador
        
        Args:
            nome: Nome do jogador
            nivel: Nível de habilidade (1.0-10.0)
            tipo: 'fixo' ou 'avulso'
            posicao: 'linha' ou 'goleiro'
            
        Returns:
            Jogador criado
        """
        # Validar nível (float 1.0-10.0, múltiplos de 0.1)
        try:
            nivel = round(float(nivel), 1)
        except (TypeError, ValueError):
            raise ValueError(f"Nível inválido: deve ser um número, recebido: {nivel}")
        if not (1.0 <= nivel <= 10.0):
            raise ValueError(f"Nível deve estar entre 1.0 e 10.0, recebido: {nivel}")
        
        nome_clean = nome.strip()
        nome_lower = nome_clean.lower()
        dados = self._carregar_raw()
        for p in dados:
            if (p.get("nome") or "").strip().lower() == nome_lower:
                nome_existente = p.get("nome") or nome_clean
                raise ValueError(f"Já existe um jogador cadastrado com o nome '{nome_existente}'.")

        jogador = Jogador(
            nome=nome_clean,
            nivel=nivel,
            tipo=tipo,
            posicao=posicao,
            owner_user_id=owner_user_id
        )
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

        if isinstance(nome, str) and nome.strip():
            nome_clean = nome.strip()
            nome_lower = nome_clean.lower()
            for item in dados:
                if item.get("id") != jogador_id and (item.get("nome") or "").strip().lower() == nome_lower:
                    nome_existente = item.get("nome") or nome_clean
                    raise ValueError(f"Já existe outro jogador cadastrado com o nome '{nome_existente}'.")
            novo_nome = nome_clean
        else:
            novo_nome = jogador_existente.nome

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
        novo_nivel_preciso: Optional[float] = None,
    ) -> Optional['Jogador']:
        """Aplica evolução de nível baseada em votação e registra histórico."""
        from datetime import datetime
        dados = self._carregar_raw()
        indice = next((i for i, item in enumerate(dados) if item.get("id") == jogador_id), None)
        if indice is None:
            return None

        item = dados[indice]
        nivel_ant = nivel_anterior if nivel_anterior is not None else float(item.get("nivel", 5.5))
        novo_nivel_clamped = round(max(1.0, min(10.0, float(novo_nivel))), 1)

        # Se novo_nivel_preciso não for fornecido, usar o novo_nivel como fallback
        if novo_nivel_preciso is None:
            novo_nivel_preciso = novo_nivel_clamped
        novo_nivel_preciso_clamped = round(max(1.0, min(10.0, float(novo_nivel_preciso))), 4)

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
        item["nivel_preciso"] = novo_nivel_preciso_clamped
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
        
        # Encontrar o jogador para obter o owner_user_id
        alvo = next((j for j in dados if j["id"] == jogador_id), None)
        if not alvo:
            return False
            
        owner_user_id = alvo.get("owner_user_id")
        dados_filtrados = [j for j in dados if j["id"] != jogador_id]
        self._salvar(dados_filtrados)
        
        # Deletar o usuário associado, se houver
        if owner_user_id:
            try:
                from services.auth_service import AuthService
                auth_service = AuthService()
                user = auth_service.obter_por_id(owner_user_id)
                if user:
                    auth_service.deletar_usuario(owner_user_id)
            except Exception as e:
                pass
                
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

    def sincronizar_jogador_avulso(self, jogador_avulso_id: str, usuario_destino_id: str) -> dict:
        """
        Sincroniza/mescla um jogador avulso a uma conta de usuário cadastrado,
        atualizando também todo o histórico de sorteios, partidas e votações.
        """
        import unicodedata
        from services.auth_service import AuthService
        from services.historico_service import HistoricoService
        from services.partida_service import PartidaService
        from services.votacao_service import VotacaoService
        from services.jogador_stats_service import JogadorStatsService

        def norm(s: str) -> str:
            if not s:
                return ""
            s_clean = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
            return s_clean.strip().lower()

        dados_jogadores = self._carregar_raw()
        avulso = next((j for j in dados_jogadores if j.get("id") == jogador_avulso_id), None)
        if not avulso:
            raise ValueError("Jogador avulso não encontrado")

        auth_service = AuthService()
        usuario_destino = auth_service.obter_por_id(usuario_destino_id)
        if not usuario_destino:
            raise ValueError("Usuário de destino não encontrado")

        nome_avulso = avulso.get("nome", "")
        norm_nome_avulso = norm(nome_avulso)

        # Verificar se o usuário destino já possui um perfil de jogador
        jogadores_usuario = [j for j in dados_jogadores if j.get("owner_user_id") == usuario_destino_id]
        if jogadores_usuario:
            target_jogador = jogadores_usuario[0]
            target_id = target_jogador.get("id")
            target_nome = target_jogador.get("nome") or usuario_destino.get("nome")

            # Transferir nota (nível e histórico de evolução) do avulso para o perfil do usuário
            for idx, j in enumerate(dados_jogadores):
                if j.get("id") == target_id:
                    # Atualiza nível se o avulso tiver nível diferente de 5.5 ou se o target for 5.5
                    if avulso.get("nivel") and (float(j.get("nivel", 5.5)) == 5.5 or float(avulso.get("nivel", 5.5)) != 5.5):
                        j["nivel"] = float(avulso.get("nivel"))
                    if avulso.get("nivel_preciso") and (j.get("nivel_preciso") in [None, 5.5] or float(avulso.get("nivel_preciso", 5.5)) != 5.5):
                        j["nivel_preciso"] = float(avulso.get("nivel_preciso"))

                    # Mesclar histórico de nível
                    hist_target = list(j.get("historico_nivel") or [])
                    hist_avulso = list(avulso.get("historico_nivel") or [])
                    hist_combinado = hist_target + hist_avulso
                    hist_combinado.sort(key=lambda x: x.get("ts", ""))
                    j["historico_nivel"] = hist_combinado[-50:]
                    break

            # Remover o perfil avulso antigo da lista de jogadores
            dados_jogadores = [j for j in dados_jogadores if j.get("id") != jogador_avulso_id]
        else:
            target_id = avulso.get("id")
            target_nome = usuario_destino.get("nome") or avulso.get("nome")
            # Atualizar o perfil avulso para pertencer ao usuário
            for idx, j in enumerate(dados_jogadores):
                if j.get("id") == jogador_avulso_id:
                    dados_jogadores[idx]["owner_user_id"] = usuario_destino_id
                    dados_jogadores[idx]["tipo"] = "fixo"
                    dados_jogadores[idx]["nome"] = target_nome

        self._salvar(dados_jogadores)

        # 1. Atualizar historico.json (Sorteios)
        historico_service = HistoricoService()
        historico_dados = historico_service._carregar_raw()
        historico_alterado = False

        for sorteio in historico_dados:
            for time in sorteio.get("times", []):
                for j in time.get("jogadores", []):
                    j_id = j.get("id")
                    j_nome = j.get("nome", "")
                    if j_id == jogador_avulso_id or (norm(j_nome) == norm_nome_avulso and not j.get("owner_user_id")):
                        j["id"] = target_id
                        j["nome"] = target_nome
                        j["owner_user_id"] = usuario_destino_id
                        j["tipo"] = "fixo"
                        historico_alterado = True

        if historico_alterado:
            historico_service._salvar(historico_dados)

        # 2. Atualizar partidas.json
        partida_service = PartidaService()
        partidas_dados = partida_service._carregar_raw()
        partidas_alteradas = False

        for partida in partidas_dados:
            for detalhe in partida.get("jogadores_detalhes", []) or []:
                if norm(detalhe.get("nome", "")) == norm_nome_avulso:
                    detalhe["nome"] = target_nome
                    partidas_alteradas = True

        if partidas_alteradas:
            partida_service._salvar(partidas_dados)

        # 3. Atualizar votacoes_partidas.json (Times, Participantes para poder votar, e Resultados)
        votacao_service = VotacaoService()
        votacoes_dados = votacao_service._carregar()
        votacoes_alteradas = False

        for p_votacao in votacoes_dados.get("partidas", []):
            for time in p_votacao.get("times", []):
                for j in time.get("jogadores", []):
                    if j.get("id") == jogador_avulso_id or norm(j.get("nome", "")) == norm_nome_avulso:
                        j["id"] = target_id
                        j["nome"] = target_nome
                        j["owner_user_id"] = usuario_destino_id
                        j["tipo"] = "fixo"
                        votacoes_alteradas = True

            # Habilitar permissão para votar se o avulso estava entre os participantes
            for part in p_votacao.get("participantes", []):
                if norm(part.get("jogador_nome", "")) == norm_nome_avulso or part.get("user_id") == usuario_destino_id:
                    part["user_id"] = usuario_destino_id
                    part["username"] = usuario_destino.get("username", "")
                    part["nome_usuario"] = usuario_destino.get("nome", "")
                    part["jogador_nome"] = target_nome
                    part["externo"] = False
                    votacoes_alteradas = True

            res_apuracao = p_votacao.get("resultado_apuracao")
            if res_apuracao and isinstance(res_apuracao, dict):
                for rank_item in res_apuracao.get("ranking_jogadores", []) or []:
                    if rank_item.get("id") == jogador_avulso_id or norm(rank_item.get("nome", "")) == norm_nome_avulso:
                        rank_item["id"] = target_id
                        rank_item["nome"] = target_nome
                        votacoes_alteradas = True

        if votacoes_alteradas:
            votacao_service._salvar(votacoes_dados)

        # 4. Invalidar cache de estatísticas
        JogadorStatsService.invalidar_cache_stats()

        return {
            "sucesso": True,
            "nome_avulso": nome_avulso,
            "usuario_destino": usuario_destino.get("nome"),
            "target_jogador_id": target_id
        }

