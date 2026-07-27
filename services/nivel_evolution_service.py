"""
Serviço de Evolução de Nível (Rating) do NaTrave

Aplica evolução inteligente do nível/rating dos jogadores com base nas votações de cada partida.

As 6 Regras de Evolução:
─────────────────────────
1. Mínimo de votos: Apenas atualiza se o jogador recebeu votos de pelo menos 40% dos participantes.
   Tabela: 10 jogadores -> min 4 votos; 15 -> min 6; 20 -> min 8.
   Caso contrário, mantém-se inalterado.
2. Nota da partida: Média dos votos recebidos multiplicada por 2 (se escala original for 5) ou como está (se escala original for 10).
3. Fórmula de mistura: NovaNotaCalculada = (NivelAtual * 0.70) + (NotaDaPartida * 0.30).
4. Velocidade de evolução:
   - |Diferenca| < 0.20 -> variação = 0
   - 0.20 <= |Diferenca| < 0.80 -> variação = +0.1 ou -0.1
   - |Diferenca| >= 0.80 -> variação = +0.2 ou -0.2
5. Desaceleração de experientes (alteração máxima permitida por faixa):
   - 1.0 até 3.0: max 0.05
   - 3.1 até 7.0: max 0.10
   - 7.1 até 9.0: max 0.05
   - 9.1 até 10.0: max 0.02
6. Arredondamento e limites: Nível final arredondado para múltiplos de 0.1 e limitado entre 1.0 e 10.0.
   Utiliza nivel_preciso para acumular pequenas variações e evitar perda de evolução em faixas muito estreitas.
"""
import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ────────────────────── lógica pura ──────────────────────────────

def calcular_novo_nivel(
    nivel_atual: float,
    notas_recebidas: List[float],
    total_jogadores_partida: int,
) -> Tuple[float, str]:
    """
    Calcula o novo nível e retorna (novo_nivel_preciso, tendencia).
    nivel_atual recebido aqui deve ser o nivel_preciso (alta precisão).
    """
    # Regra 1: Quantidade mínima de votos (aproximadamente 40% dos participantes)
    minimo_votos = int(total_jogadores_partida * 0.4)
    num_votos = len(notas_recebidas)
    
    if num_votos < minimo_votos or num_votos == 0:
        return nivel_atual, "votos_insuficientes"
        
    # Regra 2: Calcular a nota da partida
    # 1. calcular a média das notas recebidas
    media = sum(notas_recebidas) / num_votos
    
    # 2. converter a nota para a escala de 10
    # Se a maior nota na lista for <= 5.0, assumimos que está na escala de 5 e multiplicamos por 2
    if max(notas_recebidas) <= 5.0:
        nota_partida = media * 2.0
    else:
        nota_partida = media
        
    # Regra 3: Misturar histórico com desempenho atual (70% histórico, 30% atual)
    nova_nota_calculada = (nivel_atual * 0.70) + (nota_partida * 0.30)
    
    # Regra 4: Limitar a velocidade de evolução
    diferenca = nova_nota_calculada - nivel_atual
    abs_diferenca = abs(diferenca)
    
    if abs_diferenca < 0.20:
        alteracao_tentativa = 0.0
    elif abs_diferenca < 0.80:
        alteracao_tentativa = 0.1 if diferenca > 0 else -0.1
    else:
        alteracao_tentativa = 0.2 if diferenca > 0 else -0.2
        
    # Regra 5: Jogadores experientes mudam mais lentamente (alteração máxima permitida)
    # Usamos o nivel_atual (que é o rating preciso antes desta partida) para decidir a faixa
    if nivel_atual <= 3.0:
        limite_alteracao = 0.05
    elif nivel_atual <= 7.0:
        limite_alteracao = 0.10
    elif nivel_atual <= 9.0:
        limite_alteracao = 0.05
    else:
        limite_alteracao = 0.02
        
    # Aplicar limite máximo da faixa
    if alteracao_tentativa != 0.0:
        alteracao_real = math.copysign(min(abs(alteracao_tentativa), limite_alteracao), alteracao_tentativa)
    else:
        alteracao_real = 0.0
        
    # Calcular o novo nível preciso
    novo_nivel_preciso = round(nivel_atual + alteracao_real, 4)
    novo_nivel_preciso = max(1.0, min(10.0, novo_nivel_preciso))
    
    # Regra 6: O nível visível (arredondado) final será obtido via round(novo_nivel_preciso, 1)
    novo_nivel_arredondado = round(novo_nivel_preciso, 1)
    nivel_atual_arredondado = round(nivel_atual, 1)
    
    if novo_nivel_arredondado > nivel_atual_arredondado:
        tendencia = "subiu"
    elif novo_nivel_arredondado < nivel_atual_arredondado:
        tendencia = "desceu"
    else:
        tendencia = "manteve"
        
    return novo_nivel_preciso, tendencia


# ────────────────────── aplicação integrada ──────────────────────

def aplicar_evolucao_pos_votacao(
    ranking_jogadores: List[Dict],
    jogador_service,
    sorteio_id: Optional[int] = None,
) -> List[Dict]:
    """Aplica evolução de nível para todos os jogadores do ranking encerrado."""
    resultados: List[Dict] = []
    
    # Tentar carregar dados do sorteio para saber total_jogadores exato
    total_jogadores_partida = 10  # fallback padrão se não encontrado
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
        
    # Caso não seja possível obter do sorteio, usar a quantidade de participantes/itens
    if total_jogadores_partida <= 0:
        total_jogadores_partida = len(ranking_jogadores) if ranking_jogadores else 10

    for item in ranking_jogadores:
        nome = (item.get("jogador_nome") or "").strip()
        if not nome:
            continue

        jogador = jogador_service.obter_por_nome(nome)
        if not jogador:
            logger.debug("Evolução: jogador '%s' não encontrado, pulando.", nome)
            continue

        # Extrair notas brutas recebidas
        notas_recebidas = item.get("notas_lista", [])
        
        # Retrocompatibilidade com testes ou dados antigos que não possuem notas_lista
        if not notas_recebidas and item.get("votos"):
            notas_recebidas = [float(item.get("nota_media", 0))] * int(item.get("votos", 0))

        # Obter ratings atuais
        nivel_atual = float(jogador.nivel)
        nivel_preciso_atual = float(getattr(jogador, "nivel_preciso", None) or jogador.nivel)

        # Calcular novo rating preciso
        novo_nivel_preciso, tendencia = calcular_novo_nivel(
            nivel_atual=nivel_preciso_atual,
            notas_recebidas=notas_recebidas,
            total_jogadores_partida=total_jogadores_partida
        )

        novo_nivel_arredondado = round(novo_nivel_preciso, 1)

        motivo = f"votacao_sorteio_{sorteio_id}" if sorteio_id else "votacao"
        nota_media = round(sum(notas_recebidas)/len(notas_recebidas), 2) if notas_recebidas else 0.0

        # Atualiza o banco se houver qualquer variação (mesmo pequena) no nível preciso
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
                "Evolução: %s %.1f (preciso %.4f) → %.1f (preciso %.4f) (%s) [votos=%d, media=%.2f]",
                nome, nivel_atual, nivel_preciso_atual, novo_nivel_arredondado, novo_nivel_preciso,
                tendencia, len(notas_recebidas), nota_media
            )

        resultados.append({
            "nome": nome,
            "jogador_id": jogador.id,
            "nivel_anterior": nivel_atual,
            "nivel_novo": novo_nivel_arredondado,
            "tendencia": tendencia,
            "nota_media_votacao": nota_media,
            "num_votos": len(notas_recebidas),
        })

    return resultados
