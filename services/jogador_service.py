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


def formatar_nome_perfil(nome: str) -> str:
    """
    Formata o nome para exibição no card de perfil segundo as seguintes regras:
    1. Se o primeiro nome tiver mais de 10 letras, fica reduzido às 10 primeiras letras.
    2. Se não houver sobrenome, retorna o primeiro nome (limitado a 10 letras).
    3. Se houver sobrenome:
       - Soma-se a quantidade de caracteres do primeiro nome + espaço + sobrenome.
       - Se o total for maior que 12 caracteres, o sobrenome é reduzido para as 2 primeiras letras + ponto (ex: 'Ur.').
       - Se o total for até 12 caracteres, o sobrenome é mantido completo.
    Exemplos:
      'Guilherme Urbano' -> 'Guilherme Ur.' (9 + 1 + 6 = 16 > 12 -> 'Ur.')
      'guilherme urbano' -> 'guilherme ur.'
      'João Pedro' -> 'João Pedro' (4 + 1 + 5 = 10 <= 12)
      'Gui Urbano' -> 'Gui Urbano' (3 + 1 + 6 = 10 <= 12)
    """
    if not nome:
        return ""
    partes = [p for p in nome.strip().split() if p]
    if not partes:
        return ""

    # 1. Primeiro nome (máximo 10 letras)
    primeiro_nome = partes[0]
    if len(primeiro_nome) > 10:
        primeiro_nome = primeiro_nome[:10]

    # Se só tem 1 palavra
    if len(partes) == 1:
        return primeiro_nome

    # 2. Processar sobrenome e preposição (se houver)
    preposicoes = {"de", "da", "do", "das", "dos", "e"}
    sobrenome_idx = 1
    pref = ""
    if partes[1].lower() in preposicoes and len(partes) > 2:
        pref = partes[1] + " "
        sobrenome_idx = 2

    sobrenome = partes[sobrenome_idx]
    
    # Nome completo montado sem abreviar o sobrenome
    nome_completo_tentativo = f"{primeiro_nome} {pref}{sobrenome}"

    # Se a soma total (nome + sobrenome) passar de 12 letras, reduz sobrenome para 2 letras + '.'
    if len(nome_completo_tentativo) > 12:
        if len(sobrenome) > 2:
            sobrenome_abrev = sobrenome[:2] + "."
        else:
            sobrenome_abrev = sobrenome
        return f"{primeiro_nome} {pref}{sobrenome_abrev}".strip()

    return nome_completo_tentativo




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
        """Garante que qualquer jogador vinculado a um usuário reflita sempre a foto atualizada do perfil do usuário."""
        if not dados:
            return dados
        try:
            from services.auth_service import AuthService
            usuarios = AuthService()._carregar()
            user_by_id = {u.get("id"): u for u in usuarios if u.get("id")}
            user_by_name = {u.get("nome", "").strip().lower(): u for u in usuarios if u.get("nome")}
            user_by_username = {u.get("username", "").strip().lower(): u for u in usuarios if u.get("username")}

            for item in dados:
                owner_id = item.get("owner_user_id") or item.get("user_id")
                nome_key = (item.get("nome") or "").strip().lower()
                u = user_by_id.get(owner_id) or user_by_name.get(nome_key) or user_by_username.get(nome_key)
                if u is not None:
                    u_foto = u.get("foto_url", "") or ""
                    item["foto_url"] = u_foto
                    item["foto"] = u_foto
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
        nova_foto = foto_url if foto_url is not None else (getattr(jogador_existente, 'foto_url', None) or getattr(jogador_existente, 'foto', None) or dados[indice].get('foto_url', ''))

        dict_atualizado = jogador_atualizado.para_dict()
        dict_atualizado["foto_url"] = nova_foto or ""
        dict_atualizado["foto"] = nova_foto or ""
        dados[indice] = dict_atualizado
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


def sincronizar_dados_e_partidas() -> dict:
    """
    Sincroniza todos os nomes de jogadores e usuários alterados em todas as tabelas
    e históricos de partidas (partidas, votacoes_partidas, historico).
    Garante que partidas antigas registradas sob um nome anterior ou primeiro nome
    sejam vinculadas e atualizadas para o nome atual do perfil.
    """
    from services.auth_service import AuthService
    from services.jogador_service import JogadorService
    from services.votacao_service import VotacaoService
    from services.jogador_stats_service import JogadorStatsService
    from services.db import load_json_data, save_json_data
    import unicodedata

    def norm(txt: str) -> str:
        if not txt:
            return ""
        s = unicodedata.normalize("NFKD", str(txt).strip().casefold())
        return "".join(c for c in s if not unicodedata.combining(c))

    auth_svc = AuthService()
    usuarios = auth_svc._carregar()
    jog_svc = JogadorService()
    jogadores_raw = jog_svc._carregar_raw()
    partidas = load_json_data("partidas", []) or []
    vot_svc = VotacaoService()
    vot_dados = vot_svc._carregar()
    vot_partidas = vot_dados.get("partidas", []) if isinstance(vot_dados, dict) else []

    user_aliases_map = {}
    user_canonical_name = {}
    user_jogador_id_map = {}

    for u in usuarios:
        uid = str(u.get("id") or "")
        nome = (u.get("nome") or "").strip()
        username = (u.get("username") or "").strip()
        if not uid or not (nome or username):
            continue
        
        c_name = nome or username
        user_canonical_name[uid] = c_name
        aliases = {norm(nome), norm(username)}
        aliases.discard("")
        user_aliases_map[uid] = aliases

    # Vincular conta prévia do usuário principal (@guilherme -> Guilherme urbano)
    gui_main_id = "18c652b0-330e-4e0d-9c5d-eb9a27b889a2"
    gui_old_id = "09142ace-266e-4d33-96db-8b92ed6144c8"
    if gui_main_id in user_canonical_name:
        user_canonical_name[gui_old_id] = user_canonical_name[gui_main_id]
        if gui_main_id in user_aliases_map:
            user_aliases_map[gui_main_id].update({norm("guilherme"), norm("guilherme urbano"), norm("guilherme_urbano")})
            user_aliases_map[gui_old_id] = user_aliases_map[gui_main_id]

    # Coletar aliases de jogadores.json e mapear jogador_id
    for j in jogadores_raw:
        if isinstance(j, dict):
            jid = str(j.get("id") or "")
            owner_id = str(j.get("owner_user_id") or j.get("user_id") or "")
            j_nome = (j.get("nome") or "").strip()
            if owner_id and owner_id in user_canonical_name:
                if jid:
                    user_jogador_id_map[owner_id] = jid
                if j_nome:
                    user_aliases_map[owner_id].add(norm(j_nome))

    if gui_main_id in user_jogador_id_map:
        user_jogador_id_map[gui_old_id] = user_jogador_id_map[gui_main_id]

    # Coletar aliases de partidas.json
    for p in partidas:
        if isinstance(p, dict):
            for det in p.get("jogadores_detalhes", []) or []:
                if isinstance(det, dict):
                    uid = str(det.get("user_id") or det.get("owner_user_id") or "")
                    dname = (det.get("nome") or "").strip()
                    if uid and uid in user_aliases_map and dname:
                        user_aliases_map[uid].add(norm(dname))

    # Coletar aliases de votacoes_partidas.json
    for vp in vot_partidas:
        if isinstance(vp, dict):
            for part in vp.get("participantes", []) or []:
                if isinstance(part, dict):
                    uid = str(part.get("user_id") or part.get("owner_user_id") or "")
                    pname = (part.get("jogador_nome") or part.get("nome_usuario") or part.get("nome") or "").strip()
                    if uid and uid in user_aliases_map and pname:
                        user_aliases_map[uid].add(norm(pname))
            for rj in ((vp.get("ranking") or {}).get("ranking_jogadores") or []):
                if isinstance(rj, dict):
                    uid = str(rj.get("user_id") or rj.get("owner_user_id") or "")
                    rname = (rj.get("jogador_nome") or rj.get("nome") or "").strip()
                    if uid and uid in user_aliases_map and rname:
                        user_aliases_map[uid].add(norm(rname))

    def resolver_user_id(p_nome: str, p_user_id: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if p_user_id and str(p_user_id) in user_canonical_name:
            uid_str = str(p_user_id)
            return uid_str, user_canonical_name[uid_str], user_jogador_id_map.get(uid_str)
        
        norm_p = norm(p_nome)
        if not norm_p:
            return None, None, None
        
        for uid, aliases in user_aliases_map.items():
            if norm_p in aliases or any(a == norm_p for a in aliases):
                return uid, user_canonical_name[uid], user_jogador_id_map.get(uid)
        return None, None, None

    alterou_partidas = False
    alterou_votacoes = False
    alterou_historico = False

    # 1. Atualizar partidas.json
    partidas = load_json_data("partidas", []) or []
    for p in partidas:
        if not isinstance(p, dict):
            continue
        for det in p.get("jogadores_detalhes", []) or []:
            if isinstance(det, dict):
                p_nome = det.get("nome", "")
                p_uid = det.get("user_id") or det.get("owner_user_id")
                found_uid, canonical, found_jid = resolver_user_id(p_nome, p_uid)
                if found_uid and canonical:
                    if det.get("nome") != canonical:
                        det["nome"] = canonical
                        alterou_partidas = True
                    if not det.get("user_id"):
                        det["user_id"] = found_uid
                        alterou_partidas = True
                    if not det.get("owner_user_id"):
                        det["owner_user_id"] = found_uid
                        alterou_partidas = True
                    if found_jid and not det.get("jogador_id"):
                        det["jogador_id"] = found_jid
                        alterou_partidas = True

    if alterou_partidas:
        save_json_data("partidas", partidas)

    # 2. Atualizar votacoes.json / votacoes_partidas
    vot_svc = VotacaoService()
    vot_dados = vot_svc._carregar()
    vot_partidas = vot_dados.get("partidas", []) if isinstance(vot_dados, dict) else []

    for vp in vot_partidas:
        if not isinstance(vp, dict):
            continue
        for part in vp.get("participantes", []) or []:
            if isinstance(part, dict):
                p_nome = part.get("jogador_nome") or part.get("nome_usuario") or part.get("nome", "")
                p_uid = part.get("user_id") or part.get("owner_user_id")
                found_uid, canonical, found_jid = resolver_user_id(p_nome, p_uid)
                if found_uid and canonical:
                    if part.get("jogador_nome") != canonical:
                        part["jogador_nome"] = canonical
                        alterou_votacoes = True
                    if part.get("nome_usuario") != canonical:
                        part["nome_usuario"] = canonical
                        alterou_votacoes = True
                    if not part.get("user_id"):
                        part["user_id"] = found_uid
                        alterou_votacoes = True
                    if found_jid and not part.get("jogador_id"):
                        part["jogador_id"] = found_jid
                        alterou_votacoes = True
        
        # Atualizar votos individuais
        for voto in (vp.get("votos", []) or []):
            if isinstance(voto, dict):
                for voto_j in (voto.get("votos", []) or []):
                    if isinstance(voto_j, dict):
                        p_nome = voto_j.get("jogador_nome", "")
                        p_uid = voto_j.get("user_id") or voto_j.get("owner_user_id")
                        found_uid, canonical, found_jid = resolver_user_id(p_nome, p_uid)
                        if found_uid and canonical:
                            if voto_j.get("jogador_nome") != canonical:
                                voto_j["jogador_nome"] = canonical
                                alterou_votacoes = True
                            if found_jid and not voto_j.get("jogador_id"):
                                voto_j["jogador_id"] = found_jid
                                alterou_votacoes = True

        ranking_info = vp.get("ranking")
        if ranking_info and isinstance(ranking_info, dict):
            for rj in ranking_info.get("ranking_jogadores", []) or []:
                if isinstance(rj, dict):
                    p_nome = rj.get("jogador_nome") or rj.get("nome", "")
                    p_uid = rj.get("user_id") or rj.get("owner_user_id")
                    found_uid, canonical, found_jid = resolver_user_id(p_nome, p_uid)
                    if found_uid and canonical:
                        if rj.get("jogador_nome") != canonical:
                            rj["jogador_nome"] = canonical
                            alterou_votacoes = True
                        if not rj.get("user_id"):
                            rj["user_id"] = found_uid
                            alterou_votacoes = True
                        if found_jid and not rj.get("jogador_id"):
                            rj["jogador_id"] = found_jid
                            alterou_votacoes = True

        # Se a partida estiver encerrada, re-apurar ranking para recalcular notas limpas
        if vp.get("status") == "encerrada":
            try:
                vp["ranking"] = vot_svc._apurar_ranking(vp)
                alterou_votacoes = True
            except Exception:
                pass

    if alterou_votacoes:
        vot_svc._salvar(vot_dados)

    # 3. Atualizar historico.json
    historico = load_json_data("historico", []) or []
    for h in historico:
        if not isinstance(h, dict):
            continue
        for t in h.get("times", []) or []:
            if isinstance(t, dict):
                for jog in t.get("jogadores", []) or []:
                    if isinstance(jog, dict):
                        p_nome = jog.get("nome", "")
                        p_uid = jog.get("owner_user_id") or jog.get("user_id")
                        found_uid, canonical, found_jid = resolver_user_id(p_nome, p_uid)
                        if found_uid and canonical:
                            if jog.get("nome") != canonical:
                                jog["nome"] = canonical
                                alterou_historico = True
                            if not jog.get("owner_user_id"):
                                jog["owner_user_id"] = found_uid
                                alterou_historico = True
                            if found_jid and not jog.get("jogador_id"):
                                jog["jogador_id"] = found_jid
                                alterou_historico = True

    if alterou_historico:
        save_json_data("historico", historico)

    from services.db import clear_db_cache
    clear_db_cache()
    JogadorStatsService.invalidar_cache_stats()

    return {
        "sucesso": True,
        "alterou_partidas": alterou_partidas,
        "alterou_votacoes": alterou_votacoes,
        "alterou_historico": alterou_historico
    }

