"""
Rotas do Fluxo do Juiz
- Criar partida, finalizar partida, seleção de jogadores
"""
from flask import Blueprint, request, render_template, redirect, url_for, session
from functools import wraps
import logging

from services.jogador_service import JogadorService
from services.juiz_partida_service import JuizPartidaService
from services.historico_service import HistoricoService
from services.partida_service import PartidaService

juiz_bp = Blueprint('juiz', __name__)
logger = logging.getLogger(__name__)

jogador_service = JogadorService()
juiz_partida_service = JuizPartidaService()
historico_service = HistoricoService()
partida_service = PartidaService()


# ============================================================
# HELPERS
# ============================================================

def _usuario_logado():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(session.get('user_id'))
    }


def _is_juiz():
    return session.get('role') == 'juiz'


def juiz_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login_page'))
        if not _is_juiz():
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


def _sincronizar_fluxo_juiz():
    """Sincroniza estado do fluxo com dados persistidos"""
    estado = juiz_partida_service.obter_estado()
    partida_atual = estado.get('partida_atual') or {}

    if not partida_atual:
        return estado

    sorteio_id = partida_atual.get('sorteio_id')
    votacao_partida_id = partida_atual.get('votacao_partida_id')

    if sorteio_id and not partida_atual.get('resultado_registrado'):
        resultado = _obter_resultado_sorteio(sorteio_id)
        if resultado:
            juiz_partida_service.marcar_resultado_registrado(sorteio_id, resultado.get('id'))
            estado = juiz_partida_service.obter_estado()
            partida_atual = estado.get('partida_atual') or {}
            votacao_partida_id = partida_atual.get('votacao_partida_id')

    if votacao_partida_id:
        from services.votacao_service import VotacaoService
        votacao_service = VotacaoService()
        partida_votacao = votacao_service.obter_partida(votacao_partida_id)
        
        if partida_votacao and partida_votacao.get('status') == 'aberta' and estado.get('status') != 'votacao_aberta':
            juiz_partida_service.marcar_votacao_aberta(
                partida_votacao.get('sorteio_id'),
                partida_votacao.get('id')
            )
            estado = juiz_partida_service.obter_estado()
        elif partida_votacao and partida_votacao.get('status') != 'aberta':
            juiz_partida_service.finalizar_partida(_resumo_encerramento_para_juiz(partida_votacao))
            jogador_service.limpar_presenca()
            estado = juiz_partida_service.obter_estado()

    return estado


def _obter_resultado_sorteio(sorteio_id):
    """Obtém resultado da última partida de um sorteio"""
    partidas = partida_service.obter_partidas_sorteio(sorteio_id)
    if not partidas:
        return None
    partidas_ordenadas = sorted(partidas, key=lambda item: (item.get('data', ''), item.get('id', 0)), reverse=True)
    return partidas_ordenadas[0] if partidas_ordenadas else None


def _resumo_encerramento_para_juiz(partida):
    """Cria resumo de encerramento compatível com o serviço"""
    if not partida:
        return None
    ranking = partida.get('ranking') or {}
    return {
        'titulo': partida.get('titulo'),
        'sorteio_id': partida.get('sorteio_id'),
        'partida_id': partida.get('id'),
        'encerrado_em': partida.get('encerrado_em'),
        'resultado_resumido': partida.get('resultado_resumido', []),
        'melhor_jogador': ranking.get('melhor_jogador'),
        'melhor_time': ranking.get('melhor_time'),
        'total_votos': ranking.get('total_votos', 0),
        'pendentes': ranking.get('participantes_pendentes', []),
        'ranking_top5': (ranking.get('ranking_jogadores') or [])[:5],
    }


def _destino_fluxo_juiz(estado):
    """Determina para onde o juiz deve ir no fluxo"""
    partida_atual = (estado or {}).get('partida_atual') or {}
    status = (estado or {}).get('status') or 'idle'

    if status == 'selecionando':
        return None

    sorteio_id = partida_atual.get('sorteio_id')
    votacao_partida_id = partida_atual.get('votacao_partida_id')

    if status == 'sorteada' and sorteio_id:
        return url_for('partida.ver_sorteio', sorteio_id=sorteio_id)
    if status in {'resultado_registrado', 'votacao_aberta'} and sorteio_id:
        return url_for('admin.admin_page', sorteio_id=sorteio_id)
    if votacao_partida_id:
        return url_for('admin.admin_page')
    return None


# ============================================================
# FLUXO PRINCIPAL DO JUIZ
# ============================================================

@juiz_bp.route('/jogar', methods=['GET'])
@juiz_required
def jogar_page():
    """Hub principal do fluxo do juiz"""
    try:
        estado_fluxo = _sincronizar_fluxo_juiz()
        destino = _destino_fluxo_juiz(estado_fluxo)
        
        if destino:
            return redirect(destino)

        todos_jogadores = jogador_service.listar()
        
        if estado_fluxo.get('status') == 'selecionando':
            fixos = [j for j in todos_jogadores if j.tipo == "fixo"]
            avulsos = [j for j in todos_jogadores if j.tipo == "avulso"]
            presentes = [j for j in todos_jogadores if j.presente]
            
            return render_template(
                'juiz_criar_partida.html',
                todos_jogadores=todos_jogadores,
                fixos=fixos,
                avulsos=avulsos,
                presentes=presentes,
                total_presentes=len(presentes),
                total_jogadores=len(todos_jogadores),
                usuario=_usuario_logado()
            )

        ultima_partida = estado_fluxo.get('ultima_partida_encerrada')
        return render_template(
            'juiz_home.html',
            todos_jogadores=todos_jogadores,
            total_jogadores=len(todos_jogadores),
            ultima_partida=ultima_partida,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao carregar página do juiz: {str(e)}")
        return render_template('juiz_home.html', erro='Erro ao carregar página'), 500


# ============================================================
# CRIAR PARTIDA
# ============================================================

@juiz_bp.route('/jogar/criar-partida', methods=['POST'])
@juiz_required
def juiz_criar_partida():
    """Inicia criação de partida"""
    try:
        jogador_service.limpar_presenca()
        juiz_partida_service.iniciar_partida(session.get('user_id'))
        
        todos_jogadores = jogador_service.listar()
        fixos = [j for j in todos_jogadores if j.tipo == "fixo"]
        avulsos = [j for j in todos_jogadores if j.tipo == "avulso"]
        presentes = [j for j in todos_jogadores if j.presente]

        return render_template(
            'juiz_criar_partida.html',
            todos_jogadores=todos_jogadores,
            fixos=fixos,
            avulsos=avulsos,
            presentes=presentes,
            total_presentes=len(presentes),
            total_jogadores=len(todos_jogadores),
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao criar partida: {str(e)}")
        return render_template('juiz_home.html', erro='Erro ao criar partida'), 500


# ============================================================
# FINALIZAR PARTIDA
# ============================================================

@juiz_bp.route('/jogar/finalizar', methods=['POST'])
@juiz_required
def juiz_finalizar_partida():
    """Finaliza manualmente a partida quando não houve votação"""
    try:
        estado = juiz_partida_service.obter_estado()
        partida_atual = estado.get('partida_atual') or {}
        
        if not partida_atual:
            return redirect(url_for('juiz.jogar_page', erro='Nenhuma partida ativa para finalizar'))

        # Só permite finalizar se o resultado foi registrado
        if not partida_atual.get('resultado_registrado'):
            return redirect(url_for('juiz.jogar_page', erro='Resultado não registrado; não é possível finalizar'))

        sorteio_id = partida_atual.get('sorteio_id')
        resultado = _obter_resultado_sorteio(sorteio_id) if sorteio_id else None

        # Construir resumo
        import datetime
        resumo = {
            'titulo': f"Partida (sorteio {sorteio_id})" if sorteio_id else 'Partida',
            'sorteio_id': sorteio_id,
            'partida_id': resultado.get('id') if resultado else None,
            'encerrado_em': datetime.datetime.now().isoformat(),
            'resultado_resumido': [],
            'melhor_jogador': None,
            'melhor_time': None,
            'total_votos': 0,
            'pendentes': [],
            'ranking_top5': []
        }

        if resultado:
            gols = resultado.get('gols_times', []) or []
            desempenho = resultado.get('times_desempenho', []) or []
            resumo_res = []
            
            for idx, gols_time in enumerate(gols, start=1):
                item_des = next((t for t in desempenho if int(t.get('time_numero', 0) or 0) == idx), {})
                resumo_res.append({
                    'time_numero': idx,
                    'gols': int(gols_time or 0),
                    'vitorias': int(item_des.get('vitorias', 0) or 0),
                    'empates': int(item_des.get('empates', 0) or 0),
                    'derrotas': int(item_des.get('derrotas', 0) or 0),
                    'resultado': (
                        'vitoria' if (resultado.get('time_vencedor') and int(resultado.get('time_vencedor')) == idx)
                        else 'empate' if not resultado.get('time_vencedor') else 'derrota'
                    )
                })
            resumo['resultado_resumido'] = resumo_res

        juiz_partida_service.finalizar_partida(resumo)
        jogador_service.limpar_presenca()
        
        return redirect(url_for('juiz.jogar_page'))
    except Exception as e:
        logger.error(f"Erro ao finalizar partida: {str(e)}")
        return redirect(url_for('juiz.jogar_page', erro='Erro ao finalizar'))
