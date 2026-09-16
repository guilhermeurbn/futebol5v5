"""
Serviço de Evolução de Nível (Rating) do NaTrave

Aplica evolução inteligente e dinâmica do nível/rating dos jogadores com base nas votações de cada rodada.

Regras de Evolução (Dinâmica + Bônus Top 5):
--------------------------------------------
1. Mínimo de votos: Apenas atualiza se o jogador recebeu votos de pelo menos 40% dos participantes.
   Caso contrário, mantém-se inalterado ("votos_insuficientes").
2. Nota da partida: Média dos votos recebidos normalizada para a escala de 10.
3. Fórmula de mistura: NovaNotaCalculada = (NivelAtual * 0.50) + (NotaDaPartida * 0.50).
4. Velocidade de evolução dinâmica:
   - |Diferenca| < 0.08  -> Variação base = 0.0 (manteve)
   - 0.08 <= |Diferenca| < 0.35 -> Variação base = +0.10 ou -0.08
   - 0.35 <= |Diferenca| < 0.75 -> Variação base = +0.20 ou -0.15
   - |Diferenca| >= 0.75 -> Variação base = +0.30 ou -0.20
5. Bônus Top 5 da Rodada (Destaques da Quadra):
   - Top 1: +0.08
   - Top 2: +0.07
   - Top 3: +0.06
   - Top 4: +0.05
   - Top 5: +0.04
6. Tetos de segurança e limites globais:
   - Variação máxima positiva por rodada: +0.40
   - Variação máxima negativa por rodada: -0.25
   - Nível limitado estritamente entre 1.0 e 10.0.
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------- lógica pura ------------------------------

def calcular_novo_nivel(
    nivel_atual: float,
    notas_recebidas: List[float],
    total_jogadores_partida: int,
    bonus_destaque: float = 0.0,
) -> Tuple[float, str]:
    """
    Calcula o novo nível do jogador com base nos votos recebidos e eventuais bônus de destaque (Top 5).
    Retorna (novo_nivel_preciso, tendencia).
    nivel_atual recebido aqui deve ser o nivel_preciso (alta precisão).
    """
    # Regra 1: Quantidade mínima de votos (40% dos participantes)
    minimo_votos = int(total_jogadores_partida * 0.4)
    num_votos = len(notas_recebidas)
    
    if num_votos < minimo_votos or num_votos == 0:
        return nivel_atual, "votos_insuficientes"
        
    # Regra 2: Calcular a nota da partida
    media = sum(notas_recebidas) / num_votos
    if max(notas_recebidas) <= 5.0:
        nota_partida = media * 2.0
    else:
        nota_partida = media
        
    # Regra 3: Misturar histórico com desempenho atual (50% histórico, 50% atual)
    nova_nota_calculada = (nivel_atual * 0.50) + (nota_partida * 0.50)
    diferenca = nova_nota_calculada - nivel_atual
    abs_diferenca = abs(diferenca)
    
    # Regra 4: Velocidade de evolução dinâmica e perceptível
    if abs_diferenca < 0.08:
        alteracao_base = 0.0
    elif abs_diferenca < 0.35:
        alteracao_base = 0.10 if diferenca > 0 else -0.08
    elif abs_diferenca < 0.75:
        alteracao_base = 0.20 if diferenca > 0 else -0.15
    else:
        alteracao_base = 0.30 if diferenca > 0 else -0.20
        
    # Regra 5: Aplicar bônus do Top 5 da rodada
    alteracao_real = alteracao_base + (bonus_destaque if diferenca >= -0.15 else (bonus_destaque * 0.5))
    
    # Regra 6: Tetos de segurança por rodada
    alteracao_real = max(-0.25, min(0.40, alteracao_real))
        
    # Calcular o novo nível preciso
    novo_nivel_preciso = round(nivel_atual + alteracao_real, 4)
    novo_nivel_preciso = max(1.0, min(10.0, novo_nivel_preciso))
    
    novo_nivel_arredondado = round(novo_nivel_preciso, 1)
    nivel_atual_arredondado = round(nivel_atual, 1)
    
    if novo_nivel_arredondado > nivel_atual_arredondado:
        tendencia = "subiu"
    elif novo_nivel_arredondado < nivel_atual_arredondado:
        tendencia = "desceu"
    else:
        tendencia = "manteve"
        
    return novo_nivel_preciso, tendencia


# ---------------------- aplicação integrada ----------------------

def _encontrar_jogador(jogador_service, nome: str, jogador_id: Optional[str] = None):
    """Encontra o objeto Jogador mesmo quando o nome da conta difere do nome cadastrado."""
    if jogador_id:
        j = jogador_service.obter_por_id(jogador_id)
        if j:
            return j

    j = jogador_service.obter_por_nome(nome)
    if j:
        return j

    todos = jogador_service.obter_todos()
    nome_norm = (nome or "").strip().lower()

    # 1. Busca exata case-insensitive
    for jog in todos:
        if (getattr(jog, "nome", "") or "").strip().lower() == nome_norm:
            return jog

    # 2. Busca pelo vínculo com User (owner_user_id)
    try:
        from services.auth_service import AuthService
        auth_svc = AuthService()
        user = auth_svc.obter_por_nome(nome) or auth_svc.obter_por_username(nome)
        if user:
            uid = user.get("id")
            for jog in todos:
                if getattr(jog, "owner_user_id", None) == uid:
                    return jog
    except Exception:
        pass

    # 3. Busca por substring ou primeiro e último nome
    partes = [p for p in nome_norm.split() if len(p) > 2]
    for jog in todos:
        j_nome = (getattr(jog, "nome", "") or "").strip().lower()
        if nome_norm in j_nome or j_nome in nome_norm:
            return jog
        if partes and all(p in j_nome for p in [partes[0], partes[-1]]):
            return jog

    return None


def aplicar_evolucao_pos_votacao(
    ranking_jogadores: List[Dict],
    jogador_service,
    sorteio_id: Optional[int] = None,
) -> List[Dict]:
    """Aplica evolução de nível para todos os jogadores do ranking encerrado com bônus para o Top 5."""
    resultados: List[Dict] = []
    
    total_jogadores_partida = 10
    try:
        from services.historico_service import HistoricoService
        _historico_svc = HistoricoService()
        sorteio = _historico_svc.obter_sorteio(sorteio_id) if sorteio_id else None
        if sorteio:
            total_jogadores_partida = sorteio.get("total_jogadores") or sum(
                len(t.get("jogadores", [])) for t in sorteio.get("times", [])
            )
    except Exception as e:
        logger.warning("Não foi possível carregar o sorteio #%s para total_jogadores: %s", sorteio_id, e)
        
    if total_jogadores_partida <= 0:
        total_jogadores_partida = len(ranking_jogadores) if ranking_jogadores else 10

    # Tabela de bônus para o Top 5 mais votados da rodada
    bonus_top5_tabela = [0.08, 0.07, 0.06, 0.05, 0.04]

    for posicao, item in enumerate(ranking_jogadores):
        nome = (item.get("jogador_nome") or "").strip()
        if not nome:
            continue

        jogador = _encontrar_jogador(jogador_service, nome, item.get("jogador_id"))
        if not jogador:
            logger.debug("Evolução: jogador '%s' não encontrado, pulando.", nome)
            continue

        # Extrair notas brutas recebidas
        notas_recebidas = item.get("notas_lista", [])
        if not notas_recebidas and item.get("votos"):
            notas_recebidas = [float(item.get("nota_media", 0))] * int(item.get("votos", 0))

        # Obter ratings atuais
        nivel_atual = float(jogador.nivel)
        nivel_preciso_atual = float(getattr(jogador, "nivel_preciso", None) or jogador.nivel)

        # Bônus se estiver no Top 5
        bonus_destaque = bonus_top5_tabela[posicao] if posicao < len(bonus_top5_tabela) else 0.0

        # Calcular novo rating preciso
        novo_nivel_preciso, tendencia = calcular_novo_nivel(
            nivel_atual=nivel_preciso_atual,
            notas_recebidas=notas_recebidas,
            total_jogadores_partida=total_jogadores_partida,
            bonus_destaque=bonus_destaque,
        )

        novo_nivel_arredondado = round(novo_nivel_preciso, 1)
        motivo = f"votacao_sorteio_{sorteio_id}" if sorteio_id else "votacao"
        nota_media = round(sum(notas_recebidas)/len(notas_recebidas), 2) if notas_recebidas else 0.0

        if novo_nivel_preciso != nivel_preciso_atual:
            jogador_service.aplicar_evolucao_nivel(
                jogador_id=jogador.id,
                novo_nivel=novo_nivel_arredondado,
                motivo=motivo,
                nivel_anterior=nivel_atual,
                nota_media=nota_media,
                novo_nivel_preciso=novo_nivel_preciso,
            )
            logger.info(
                "Evolução: %s %.1f (preciso %.4f) → %.1f (preciso %.4f) (%s) [votos=%d, media=%.2f, bonus_top=%s]",
                nome, nivel_atual, nivel_preciso_atual, novo_nivel_arredondado, novo_nivel_preciso,
                tendencia, len(notas_recebidas), nota_media, bonus_destaque
            )

        resultados.append({
            "nome": nome,
            "jogador_id": jogador.id,
            "nivel_anterior": nivel_atual,
            "nivel_novo": novo_nivel_arredondado,
            "tendencia": tendencia,
            "nota_media_votacao": nota_media,
            "num_votos": len(notas_recebidas),
            "posicao_rodada": posicao + 1,
            "bonus_top5": bonus_destaque,
        })

    return resultados
