"""
Serviço de Evolução de Nível (Rating)

Aplica evolução gradual do nível/rating de cada jogador (0.00–10.00)
com base nas notas mediadas nas votações encerradas.

Algoritmo inteligente:
─────────────────────
• Requer mínimo de 3 votos para qualquer alteração.
• delta = (nota_media_votação − nível_atual) × taxa_aprendizado
• taxa_aprendizado padrão = 0.15  (evolução suave por rodada)
• Só aplica se |delta| ≥ 0.01  (evita micro-ruído desnecessário)
• Arredonda resultado a 2 casas decimais.
• Clamp final: 0.00 – 10.00.
• Resultado registrado no historico_nivel do jogador.

Exemplos:
  jogador nível 7.00, nota_media 9.00  → delta = +0.30  → 7.30
  jogador nível 7.00, nota_media 6.00  → delta = -0.15  → 6.85
  jogador nível 7.00, nota_media 7.05  → delta = +0.01  → 7.01
  jogador nível 7.00, nota_media 7.03  → delta = 0.005 ≈ 0.00 → sem alteração
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ────────────────────── constantes tunáveis ──────────────────────
TAXA_APRENDIZADO: float = 0.15   # velocidade de convergência por rodada
MIN_VOTOS: int = 3               # mínimo de votos para aplicar mudança
NIVEL_MIN: float = 0.0
NIVEL_MAX: float = 10.0


# ────────────────────── lógica pura ──────────────────────────────

def calcular_novo_nivel(
    nivel_atual: float,
    nota_media: float,
    num_votos: int,
    taxa: float = TAXA_APRENDIZADO,
    min_votos: int = MIN_VOTOS,
) -> Tuple[float, str]:
    """Calcula o novo nível e retorna (novo_nivel, tendencia).

    tendencia é uma das strings:
      'subiu'              – nível aumentou
      'desceu'             – nível diminuiu
      'manteve'            – sem alteração significativa
      'votos_insuficientes'– menos de min_votos votos
    """
    if num_votos < min_votos:
        return nivel_atual, "votos_insuficientes"

    gap = nota_media - nivel_atual
    delta = round(gap * taxa, 2)

    if abs(delta) < 0.01:
        return nivel_atual, "manteve"

    novo = round(max(NIVEL_MIN, min(NIVEL_MAX, nivel_atual + delta)), 2)
    tendencia = "subiu" if delta > 0 else "desceu"
    return novo, tendencia


# ────────────────────── aplicação integrada ──────────────────────

def aplicar_evolucao_pos_votacao(
    ranking_jogadores: List[Dict],
    jogador_service,
    sorteio_id: Optional[int] = None,
) -> List[Dict]:
    """Aplica evolução de nível para todos os jogadores do ranking encerrado.

    Args:
        ranking_jogadores: lista de dicts do _apurar_ranking (jogador_nome,
                           nota_media, votos).
        jogador_service:   instância de JogadorService.
        sorteio_id:        ID do sorteio, para contexto do histórico.

    Returns:
        Lista de resultados por jogador:
        [{"nome", "jogador_id", "nivel_anterior", "nivel_novo",
          "tendencia", "nota_media_votacao", "num_votos"}]
    """
    resultados: List[Dict] = []

    for item in ranking_jogadores:
        nome = (item.get("jogador_nome") or "").strip()
        nota_media = float(item.get("nota_media", 0) or 0)
        num_votos = int(item.get("votos", 0) or 0)

        if not nome:
            continue

        jogador = jogador_service.obter_por_nome(nome)
        if not jogador:
            logger.debug("Evolução: jogador '%s' não encontrado, pulando.", nome)
            continue

        nivel_atual = float(jogador.nivel)
        novo_nivel, tendencia = calcular_novo_nivel(nivel_atual, nota_media, num_votos)

        motivo = f"votacao_sorteio_{sorteio_id}" if sorteio_id else "votacao"

        if novo_nivel != nivel_atual:
            jogador_service.aplicar_evolucao_nivel(
                jogador_id=jogador.id,
                novo_nivel=novo_nivel,
                motivo=motivo,
                nivel_anterior=nivel_atual,
                nota_media=nota_media,
            )
            logger.info(
                "Evolução: %s %.2f → %.2f (%s) [nota_media=%.2f, votos=%d]",
                nome, nivel_atual, novo_nivel, tendencia, nota_media, num_votos,
            )

        resultados.append({
            "nome": nome,
            "jogador_id": jogador.id,
            "nivel_anterior": nivel_atual,
            "nivel_novo": novo_nivel,
            "tendencia": tendencia,
            "nota_media_votacao": nota_media,
            "num_votos": num_votos,
        })

    return resultados
