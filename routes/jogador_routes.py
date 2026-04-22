"""
Rotas de Jogadores
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify
from services.jogador_service import JogadorService
from services.balanceamento import BalanceadorTimes

jogador_bp = Blueprint('jogador', __name__)
jogador_service = JogadorService()


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
            tipo=dados.get('tipo', 'avulso')
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
        
        jogador_service.criar(nome, nivel, tipo)
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
        times, somas = BalanceadorTimes.sortear_multiplos_times(presentes)
        num_times = len(times)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        return render_template(
            'times.html',
            jogadores=presentes,
            times=times,
            somas=somas,
            num_times=num_times,
            diferenca=diferenca,
            melhor_time=melhor_time
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
        times, somas = BalanceadorTimes.sortear_multiplos_times(presentes)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Formatar times para JSON
        times_json = []
        for idx, time in enumerate(times):
            times_json.append({
                'numero': idx + 1,
                'jogadores': [j.para_dict() for j in time],
                'soma': somas[idx]
            })
        
        return jsonify({
            'sucesso': True,
            'times': times_json,
            'num_times': len(times),
            'diferenca': diferenca,
            'melhor_time': melhor_time
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
