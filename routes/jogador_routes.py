"""
Rotas de Jogadores
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session, send_file
from services.jogador_service import JogadorService
from services.balanceamento import BalanceadorTimes
from services.historico_service import HistoricoService
from services.stats_service import StatsService
from services.export_service import ExportService
from services.partida_service import PartidaService
from services.favorito_service import FavoritoService
from services.undoredo_service import UndoRedoService
from services.qrcode_service import QRCodeService
import io

jogador_bp = Blueprint('jogador', __name__)
jogador_service = JogadorService()
historico_service = HistoricoService()
stats_service = StatsService()
export_service = ExportService()
partida_service = PartidaService()
favorito_service = FavoritoService()
undoredo_service = UndoRedoService()
qrcode_service = QRCodeService()


@jogador_bp.route('/')
def index():
    """Página inicial com lista de jogadores"""
    jogadores = jogador_service.listar()
    return render_template(
        'index.html',
        jogadores=jogadores,
        total_jogadores=len(jogadores)
    )


@jogador_bp.route('/api/jogadores', methods=['GET'])
def listar_jogadores_api():
    """API: Lista todos os jogadores"""
    jogadores = jogador_service.listar()
    return jsonify([j.para_dict() for j in jogadores])


@jogador_bp.route('/api/jogadores', methods=['POST'])
def criar_jogador_api():
    """API: Cria novo jogador"""
    try:
        dados = request.get_json()
        jogador = jogador_service.criar(
            nome=dados.get('nome'),
            nivel=int(dados.get('nivel', 5)),
            tipo=dados.get('tipo', 'avulso'),
            posicao=dados.get('posicao', 'linha')
        )
        return jsonify({
            'sucesso': True,
            'jogador': jogador.para_dict(),
            'mensagem': 'Jogador criado com sucesso'
        }), 201
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': 'Erro ao criar jogador'}), 500


@jogador_bp.route('/add', methods=['POST'])
def adicionar_jogador():
    """Formulário: Adiciona novo jogador"""
    try:
        nome = request.form.get('nome', '').strip()
        nivel = int(request.form.get('nivel', 5))
        tipo = request.form.get('tipo', 'avulso')
        posicao = request.form.get('posicao', 'linha')
        
        jogador_service.criar(nome, nivel, tipo, posicao)
        return redirect(url_for('jogador.index'))
    except ValueError as e:
        return f"Erro: {str(e)}", 400
    except Exception as e:
        return "Erro ao adicionar jogador", 500


@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['GET'])
def obter_jogador(jogador_id):
    """API: Obtém jogador por ID"""
    jogador = jogador_service.obter_por_id(jogador_id)
    if not jogador:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    return jsonify(jogador.para_dict())


@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['PUT'])
def atualizar_jogador(jogador_id):
    """API: Atualiza jogador"""
    try:
        dados = request.get_json()
        jogador = jogador_service.atualizar(
            jogador_id,
            nome=dados.get('nome'),
            nivel=int(dados.get('nivel', 5))
        )
        if not jogador:
            return jsonify({'erro': 'Jogador não encontrado'}), 404
        return jsonify({
            'sucesso': True,
            'jogador': jogador.para_dict(),
            'mensagem': 'Jogador atualizado com sucesso'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': 'Erro ao atualizar jogador'}), 500


@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['DELETE'])
def deletar_jogador(jogador_id):
    """API: Deleta jogador"""
    sucesso = jogador_service.deletar(jogador_id)
    if not sucesso:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    return jsonify({'sucesso': True, 'mensagem': 'Jogador deletado com sucesso'})


@jogador_bp.route('/delete/<jogador_id>')
def deletar_jogador_form(jogador_id):
    """Formulário: Deleta jogador"""
    jogador_service.deletar(jogador_id)
    return redirect(url_for('jogador.index'))


@jogador_bp.route('/selecionar')
def selecionar_jogadores():
    """Página para selecionar jogadores para o jogo"""
    todos_jogadores = jogador_service.listar()
    fixos = jogador_service.listar_por_tipo("fixo")
    avulsos = jogador_service.listar_por_tipo("avulso")
    presentes = jogador_service.listar_presentes()
    
    return render_template(
        'selecionar.html',
        todos_jogadores=todos_jogadores,
        fixos=fixos,
        avulsos=avulsos,
        presentes=presentes,
        total_presentes=len(presentes),
        total_jogadores=len(todos_jogadores)
    )


@jogador_bp.route('/api/presenca', methods=['POST'])
def atualizar_presenca():
    """API: Marca jogadores como presentes"""
    try:
        dados = request.get_json()
        jogador_ids = dados.get('jogador_ids', [])
        
        if len(jogador_ids) not in [10, 15, 20]:
            return jsonify({
                'sucesso': False,
                'erro': f'Selecione exatamente 10, 15 ou 20 jogadores. Selecionados: {len(jogador_ids)}'
            }), 400
        
        jogador_service.marcar_presenca(jogador_ids)
        
        return jsonify({
            'sucesso': True,
            'total_presentes': len(jogador_ids),
            'mensagem': f'{len(jogador_ids)} jogadores selecionados com sucesso'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/presenca/limpar', methods=['POST'])
def limpar_presenca():
    """API: Limpa seleção de presença"""
    try:
        jogador_service.limpar_presenca()
        return jsonify({
            'sucesso': True,
            'mensagem': 'Seleção limpa'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/sortear')
def sortear():
    """Página com times sorteados"""
    presentes = jogador_service.listar_presentes()
    
    try:
        times, somas, tem_aviso, aviso_msg = BalanceadorTimes.sortear_multiplos_times_com_goleiros(presentes)
        num_times = len(times)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico
        sorteio = historico_service.adicionar_sorteio(times, somas, num_times, diferenca)
        sorteio_id = sorteio.get('id')
        
        return render_template(
            'times.html',
            jogadores=presentes,
            times=times,
            somas=somas,
            num_times=num_times,
            diferenca=diferenca,
            melhor_time=melhor_time,
            sorteio_id=sorteio_id,
            tem_aviso=tem_aviso,
            aviso_msg=aviso_msg
        )
    except ValueError as e:
        todos_jogadores = jogador_service.listar()
        return render_template(
            'index.html',
            jogadores=todos_jogadores,
            erro=str(e)
        )


@jogador_bp.route('/api/times')
def sortear_api():
    """API: Sorteia times"""
    try:
        presentes = jogador_service.listar_presentes()
        times, somas, tem_aviso, aviso_msg = BalanceadorTimes.sortear_multiplos_times_com_goleiros(presentes)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico
        sorteio = historico_service.adicionar_sorteio(times, somas, len(times), diferenca)
        
        # Formatar times para JSON
        times_json = []
        for idx, time in enumerate(times):
            times_json.append({
                'numero': idx + 1,
                'jogadores': [j.para_dict() for j in time],
                'soma': somas[idx]
            })
        
        # Adicionar à pilha de undo/redo
        sorteio_data = {
            'sorteio_id': sorteio.get('id'),
            'times': times_json,
            'num_times': len(times),
            'somas': somas,
            'diferenca': diferenca,
            'melhor_time': melhor_time,
            'tem_aviso': tem_aviso,
            'aviso_msg': aviso_msg
        }
        undoredo_service.adicionar_sorteio(sorteio_data)
        
        return jsonify({
            'sucesso': True,
            'sorteio_id': sorteio.get('id'),
            'times': times_json,
            'num_times': len(times),
            'diferenca': diferenca,
            'melhor_time': melhor_time,
            'tem_aviso': tem_aviso,
            'aviso_msg': aviso_msg
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400


@jogador_bp.route('/historico')
def historico():
    """Página com histórico de sorteios"""
    sorteios = historico_service.listar_sorteios()
    # Reverter ordem (mais recente primeiro)
    sorteios = list(reversed(sorteios))
    
    return render_template(
        'historico.html',
        sorteios=sorteios
    )


@jogador_bp.route('/sorteio/<int:sorteio_id>')
def ver_sorteio(sorteio_id):
    """Visualiza um sorteio específico do histórico"""
    sorteio = historico_service.obter_sorteio(sorteio_id)
    
    if not sorteio:
        return render_template('historico.html', sorteios=[], erro="Sorteio não encontrado"), 404
    
    return render_template(
        'sorteio_detalhe.html',
        sorteio=sorteio
    )


@jogador_bp.route('/api/historico')
def api_historico():
    """API: Retorna histórico de sorteios"""
    sorteios = historico_service.listar_sorteios()
    # Reverter ordem (mais recente primeiro)
    sorteios = list(reversed(sorteios))
    
    return jsonify({
        'sucesso': True,
        'sorteios': sorteios
    })


@jogador_bp.route('/api/estatisticas')
def api_estatisticas():
    """API: Retorna estatísticas gerais"""
    stats = historico_service.obter_estatisticas()
    
    return jsonify({
        'sucesso': True,
        'estatisticas': stats
    })


@jogador_bp.route('/estatisticas')
def estatisticas():
    """Página com estatísticas gerais"""
    stats = historico_service.obter_estatisticas()
    
    return render_template(
        'estatisticas.html',
        stats=stats
    )


# ============================================================
# NOVOS ENDPOINTS DE ESTATÍSTICAS AVANÇADAS
# ============================================================

@jogador_bp.route('/api/stats/players', methods=['GET'])
def api_stats_players():
    """API: Estatísticas detalhadas por jogador"""
    stats = stats_service.calcular_stats_jogadores()
    
    # Ordenar por win_rate (decrescente)
    stats_ordenadas = dict(
        sorted(
            stats.items(),
            key=lambda x: x[1].get('win_rate', 0),
            reverse=True
        )
    )
    
    return jsonify(stats_ordenadas)


@jogador_bp.route('/api/stats/times', methods=['GET'])
def api_stats_times():
    """API: Estatísticas de times"""
    stats = stats_service.calcular_stats_times()
    
    # Ordenar por win_rate (decrescente)
    stats_ordenadas = dict(
        sorted(
            stats.items(),
            key=lambda x: x[1].get('win_rate', 0),
            reverse=True
        )
    )
    
    return jsonify(stats_ordenadas)


@jogador_bp.route('/api/stats/geral', methods=['GET'])
def api_stats_geral():
    """API: Estatísticas gerais"""
    stats = stats_service.calcular_estatisticas_sorteios()
    return jsonify(stats)


@jogador_bp.route('/api/stats/combos', methods=['GET'])
def api_stats_combos():
    """API: Melhores combos vencedores"""
    combos = stats_service.get_combos_vencedores()
    return jsonify(combos)


@jogador_bp.route('/api/stats/comparacao/<player1>/<player2>', methods=['GET'])
def api_stats_comparacao(player1, player2):
    """API: Comparação entre dois jogadores"""
    comparacao = stats_service.get_comparacao_players(player1, player2)
    return jsonify(comparacao)


@jogador_bp.route('/stats/players', methods=['GET'])
def stats_players():
    """Página com estatísticas de jogadores"""
    stats = stats_service.calcular_stats_jogadores()
    
    # Ordenar por win_rate
    stats_ordenadas = sorted(
        [{"nome": nome, **dados} for nome, dados in stats.items()],
        key=lambda x: x.get('win_rate', 0),
        reverse=True
    )
    
    return render_template(
        'stats_players.html',
        stats=stats_ordenadas
    )


@jogador_bp.route('/stats/times', methods=['GET'])
def stats_times_page():
    """Página com estatísticas de times"""
    stats = stats_service.calcular_stats_times()
    
    # Ordenar por win_rate
    stats_ordenadas = sorted(
        [{"time_key": key, **dados} for key, dados in stats.items()],
        key=lambda x: x.get('win_rate', 0),
        reverse=True
    )
    
    return render_template(
        'stats_times.html',
        stats=stats_ordenadas
    )


@jogador_bp.route('/stats/combos', methods=['GET'])
def stats_combos_page():
    """Página com melhores combos"""
    combos = stats_service.get_combos_vencedores()
    
    return render_template(
        'stats_combos.html',
        combos=combos
    )


@jogador_bp.route('/charts', methods=['GET'])
def charts():
    """Página com gráficos e visualizações"""
    return render_template('charts.html')


# ============================================================
# EXPORTAÇÃO DE DADOS
# ============================================================

@jogador_bp.route('/export/sorteio/csv', methods=['GET'])
def export_sorteio_csv():
    """Exporta o último sorteio realizado em CSV"""
    if 'ultimo_sorteio' not in session:
        return jsonify({'erro': 'Nenhum sorteio realizado'}), 400
    
    sorteio_data = session['ultimo_sorteio']
    
    # Converter dados de volta para objetos Jogador
    times_json = sorteio_data.get('times', [])
    somas = sorteio_data.get('somas', [])
    diferenca = sorteio_data.get('diferenca', 0)
    
    csv_content = export_service.exportar_sorteio_csv(
        times_json, somas, diferenca
    )
    
    return send_file(
        io.BytesIO(csv_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'sorteio_{sorteio_data.get("id")}.csv'
    )


@jogador_bp.route('/export/sorteio/txt', methods=['GET'])
def export_sorteio_txt():
    """Exporta o último sorteio em texto simples"""
    if 'ultimo_sorteio' not in session:
        return jsonify({'erro': 'Nenhum sorteio realizado'}), 400
    
    sorteio_data = session['ultimo_sorteio']
    
    # Converter dados
    times_json = sorteio_data.get('times', [])
    somas = sorteio_data.get('somas', [])
    diferenca = sorteio_data.get('diferenca', 0)
    
    txt_content = export_service.exportar_sorteio_texto(
        times_json, somas, diferenca
    )
    
    return send_file(
        io.BytesIO(txt_content.encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'sorteio_{sorteio_data.get("id")}.txt'
    )


@jogador_bp.route('/export/historico/csv', methods=['GET'])
def export_historico_csv():
    """Exporta o histórico completo em CSV"""
    sorteios = historico_service.listar_sorteios()
    
    csv_content = export_service.exportar_historico_csv(sorteios)
    
    return send_file(
        io.BytesIO(csv_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='historico_sorteios.csv'
    )


@jogador_bp.route('/export/estatisticas/csv', methods=['GET'])
def export_estatisticas_csv():
    """Exporta estatísticas em CSV"""
    stats = historico_service.obter_estatisticas()
    
    csv_content = export_service.exportar_estatisticas_csv(stats)
    
    return send_file(
        io.BytesIO(csv_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='estatisticas_sorteios.csv'
    )


@jogador_bp.route('/api/export/sorteio', methods=['POST'])
def api_export_sorteio_data():
    """API para armazenar dados do último sorteio na sessão"""
    data = request.get_json()
    session['ultimo_sorteio'] = data
    session.modified = True
    return jsonify({'sucesso': True, 'mensagem': 'Sorteio armazenado para exportação'})


# ============================================================
# MODO COMPETITIVO - PARTIDAS E CAMPEONATO
# ============================================================

@jogador_bp.route('/resultado_partida/<int:sorteio_id>')
def resultado_partida_page(sorteio_id):
    """Página para registrar resultado de uma partida"""
    sorteio = historico_service.obter_sorteio(sorteio_id)
    
    if not sorteio:
        return render_template('historico.html', sorteios=[], erro="Sorteio não encontrado"), 404
    
    return render_template(
        'resultado_partida.html',
        sorteio=sorteio,
        sorteio_id=sorteio_id
    )


@jogador_bp.route('/api/partida/registrar', methods=['POST'])
def registrar_resultado_partida():
    """API: Registra resultado de uma partida"""
    try:
        dados = request.get_json()
        
        sorteio_id = dados.get('sorteio_id')
        time_vencedor = dados.get('time_vencedor')
        gols_times = dados.get('gols_times', [])
        notas = dados.get('notas', '')
        
        # Validar dados
        if not sorteio_id or not time_vencedor:
            return jsonify({
                'sucesso': False,
                'erro': 'Sorteio ID e Time Vencedor são obrigatórios'
            }), 400
        
        if not gols_times:
            return jsonify({
                'sucesso': False,
                'erro': 'Registre gols de todos os times'
            }), 400
        
        partida = partida_service.registrar_resultado(
            sorteio_id, time_vencedor, gols_times, notas
        )
        
        return jsonify({
            'sucesso': True,
            'partida': partida,
            'mensagem': 'Resultado registrado com sucesso!'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/campeonato')
def campeonato_page():
    """Página do campeonato com ranking"""
    campeonato = partida_service.obter_campeonato()
    placar_geral = partida_service.obter_placar_geral()
    ultimas_partidas = partida_service.listar_partidas(limite=10)
    
    return render_template(
        'campeonato.html',
        campeonato=campeonato,
        placar_geral=placar_geral,
        ultimas_partidas=ultimas_partidas
    )


@jogador_bp.route('/api/campeonato')
def api_campeonato():
    """API: Retorna dados do campeonato"""
    campeonato = partida_service.obter_campeonato()
    placar_geral = partida_service.obter_placar_geral()
    
    return jsonify({
        'sucesso': True,
        'campeonato': campeonato,
        'placar_geral': placar_geral
    })


# ============================================================
# FAVORITAMENTO DE TIMES
# ============================================================

@jogador_bp.route('/api/favoritar-time', methods=['POST'])
def api_favoritar_time():
    """API: Favorita um time"""
    try:
        dados = request.get_json()
        
        sorteio_id = dados.get('sorteio_id')
        time_numero = dados.get('time_numero')
        jogadores = dados.get('jogadores', [])
        pontuacao = dados.get('pontuacao', 0)
        nome = dados.get('nome', '')
        
        if not sorteio_id or not time_numero or not jogadores:
            return jsonify({
                'sucesso': False,
                'erro': 'Dados incompletos'
            }), 400
        
        favorito = favorito_service.favoritar_time(
            sorteio_id, time_numero, jogadores, pontuacao, nome
        )
        
        return jsonify({
            'sucesso': True,
            'favorito': favorito,
            'mensagem': 'Time favoritado com sucesso!'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/favoritos')
def listar_favoritos_page():
    """Página com times favoritos"""
    favoritos = favorito_service.listar_favoritos()
    stats = favorito_service.obter_estatisticas_favoritos()
    
    return render_template(
        'favoritos.html',
        favoritos=favoritos,
        stats=stats
    )


@jogador_bp.route('/api/favoritos')
def api_listar_favoritos():
    """API: Lista todos os favoritos"""
    favoritos = favorito_service.listar_favoritos()
    
    return jsonify({
        'sucesso': True,
        'favoritos': favoritos
    })


@jogador_bp.route('/api/favorito/<int:fav_id>/remover', methods=['DELETE'])
def api_remover_favorito(fav_id):
    """API: Remove um favorito"""
    sucesso = favorito_service.remover_favorito(fav_id)
    
    if sucesso:
        return jsonify({
            'sucesso': True,
            'mensagem': 'Favorito removido com sucesso'
        })
    else:
        return jsonify({
            'sucesso': False,
            'erro': 'Favorito não encontrado'
        }), 404


@jogador_bp.route('/api/favorito/<int:fav_id>/renomear', methods=['POST'])
def api_renomear_favorito(fav_id):
    """API: Renomeia um favorito"""
    try:
        dados = request.get_json()
        novo_nome = dados.get('nome', '')
        
        if not novo_nome:
            return jsonify({
                'sucesso': False,
                'erro': 'Nome não pode ser vazio'
            }), 400
        
        favorito = favorito_service.renomear_favorito(fav_id, novo_nome)
        
        if favorito:
            return jsonify({
                'sucesso': True,
                'favorito': favorito,
                'mensagem': 'Favorito renomeado com sucesso'
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Favorito não encontrado'
            }), 404
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/favorito/<int:fav_id>/usar', methods=['POST'])
def api_usar_favorito(fav_id):
    """API: Marca favorito como usado"""
    sucesso = favorito_service.incrementar_uso(fav_id)
    
    if sucesso:
        favorito = favorito_service.obter_favorito(fav_id)
        return jsonify({
            'sucesso': True,
            'favorito': favorito,
            'mensagem': 'Favorito utilizado'
        })
    else:
        return jsonify({
            'sucesso': False,
            'erro': 'Favorito não encontrado'
        }), 404


# ============================================================
# UNDO / REDO - SORTEIOS
# ============================================================

@jogador_bp.route('/api/sorteio/undo', methods=['POST'])
def api_undo_sorteio():
    """API: Desfaz o sorteio (volta ao anterior)"""
    sorteio = undoredo_service.undo()
    status = undoredo_service.obter_status()
    
    if sorteio:
        return jsonify({
            'sucesso': True,
            'sorteio': sorteio,
            'status': status,
            'mensagem': f'Voltou para sorteio #{status["sorteio_atual"]}'
        })
    else:
        return jsonify({
            'sucesso': False,
            'erro': 'Nenhum sorteio anterior disponível',
            'status': status
        }), 400


@jogador_bp.route('/api/sorteio/redo', methods=['POST'])
def api_redo_sorteio():
    """API: Refaz o sorteio (avança para o próximo)"""
    sorteio = undoredo_service.redo()
    status = undoredo_service.obter_status()
    
    if sorteio:
        return jsonify({
            'sucesso': True,
            'sorteio': sorteio,
            'status': status,
            'mensagem': f'Avançou para sorteio #{status["sorteio_atual"]}'
        })
    else:
        return jsonify({
            'sucesso': False,
            'erro': 'Nenhum sorteio posterior disponível',
            'status': status
        }), 400


@jogador_bp.route('/api/sorteio/status', methods=['GET'])
def api_status_sorteio():
    """API: Retorna status do undo/redo"""
    status = undoredo_service.obter_status()
    sorteio_atual = undoredo_service.obter_atual()
    
    return jsonify({
        'sucesso': True,
        'status': status,
        'sorteio_atual': sorteio_atual
    })


@jogador_bp.route('/api/sorteio/adicionar-stack', methods=['POST'])
def api_adicionar_stack():
    """API: Adiciona sorteio à pilha de undo/redo"""
    try:
        sorteio_data = request.get_json()
        
        indice, total = undoredo_service.adicionar_sorteio(sorteio_data)
        status = undoredo_service.obter_status()
        
        return jsonify({
            'sucesso': True,
            'status': status,
            'mensagem': f'Sorteio {indice + 1} de {total} adicionado à pilha'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ============================================================
# QR CODE - COMPARTILHAMENTO
# ============================================================

@jogador_bp.route('/api/qrcode/sorteio/<int:sorteio_id>', methods=['GET'])
def api_qrcode_sorteio(sorteio_id):
    """API: Gera QR code de um sorteio"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        
        if not sorteio:
            return jsonify({'sucesso': False, 'erro': 'Sorteio não encontrado'}), 404
        
        # Preparar dados para QR code
        sorteio_data = {
            'id': sorteio_id,
            'times': sorteio.get('times', []),
            'pontuacoes': sorteio.get('pontuacoes', []),
            'num_times': sorteio.get('num_times', 0)
        }
        
        # Gerar QR code
        url, qr_bytes = qrcode_service.gerar_qr_sorteio(sorteio_data)
        
        return send_file(
            io.BytesIO(qr_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name=f'qrcode_sorteio_{sorteio_id}.png'
        )
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/compartilhado', methods=['GET'])
def compartilhado_page():
    """Página para exibir sorteio compartilhado via QR code"""
    try:
        dados_b64 = request.args.get('sorteio')
        
        if not dados_b64:
            return render_template('compartilhado_vazio.html'), 400
        
        # Decodificar dados
        sorteio_data = qrcode_service.decodificar_sorteio(dados_b64)
        
        return render_template(
            'compartilhado.html',
            sorteio=sorteio_data
        )
    except ValueError as e:
        return render_template('compartilhado_vazio.html', erro=str(e)), 400
    except Exception as e:
        return render_template('compartilhado_vazio.html', erro='Erro ao decodificar'), 500


@jogador_bp.route('/api/qrcode/link-compartilhamento/<int:sorteio_id>', methods=['GET'])
def api_link_compartilhamento(sorteio_id):
    """API: Gera link de compartilhamento"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        
        if not sorteio:
            return jsonify({'sucesso': False, 'erro': 'Sorteio não encontrado'}), 404
        
        # Preparar dados
        sorteio_data = {
            'id': sorteio_id,
            'times': sorteio.get('times', []),
            'pontuacoes': sorteio.get('pontuacoes', []),
            'num_times': sorteio.get('num_times', 0),
            'data': sorteio.get('data', '')
        }
        
        # Gerar URL e QR code
        url_base = request.host_url.rstrip('/')
        url_compartilhamento, qr_bytes = qrcode_service.gerar_qr_sorteio(sorteio_data, url_base)
        
        # Codificar QR code em base64 para retornar como JSON
        import base64
        qr_b64 = base64.b64encode(qr_bytes).decode()
        
        return jsonify({
            'sucesso': True,
            'sorteio_id': sorteio_id,
            'url': url_compartilhamento,
            'qr_code': f'data:image/png;base64,{qr_b64}'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
