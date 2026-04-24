"""
Rotas de Jogadores
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session, send_file, Response
from functools import wraps
from services.jogador_service import JogadorService
from services.balanceamento import BalanceadorTimes
from services.historico_service import HistoricoService
from services.stats_service import StatsService
from services.export_service import ExportService
from services.partida_service import PartidaService
from services.favorito_service import FavoritoService
from services.undoredo_service import UndoRedoService
from services.qrcode_service import QRCodeService
from services.sugestoes_service import SugestoesService
from services.ranking_service import RankingService
from services.auth_service import AuthService
from services.votacao_service import VotacaoService
import io
import random

jogador_bp = Blueprint('jogador', __name__)
jogador_service = JogadorService()
historico_service = HistoricoService()
stats_service = StatsService()
export_service = ExportService()
partida_service = PartidaService()
favorito_service = FavoritoService()
undoredo_service = UndoRedoService()
qrcode_service = QRCodeService()
sugestoes_service = SugestoesService()
ranking_service = RankingService()
auth_service = AuthService()
votacao_service = VotacaoService()


def _is_admin():
    return session.get('role') in ['super_admin', 'admin']


def _jogadores_visiveis():
    return jogador_service.listar()


def _jogadores_visiveis_dict():
    return jogador_service.listar_para_dict()


def _usuario_logado():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'autenticado': bool(session.get('user_id'))
    }


def _resposta_nao_autenticado():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Autenticacao obrigatoria'}), 401
    return redirect(url_for('jogador.login_page'))


def _resposta_sem_permissao():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Acesso restrito ao administrador'}), 403
    return redirect(url_for('jogador.index'))


def _resposta_somente_leitura():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Usuario com acesso somente leitura'}), 403
    return redirect(url_for('jogador.index'))


def _resposta_voto_somente_usuario():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Apenas usuarios podem votar'}), 403
    return redirect(url_for('jogador.index'))


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return _resposta_nao_autenticado()
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return _resposta_nao_autenticado()
        if not _is_admin():
            return _resposta_sem_permissao()
        return f(*args, **kwargs)
    return wrapper


@jogador_bp.app_context_processor
def inject_auth_user():
    return {'auth_user': _usuario_logado()}


@jogador_bp.before_request
def proteger_rotas():
    liberadas = {
        'jogador.login_page',
        'jogador.login_submit',
        'jogador.cadastro_page',
        'jogador.cadastro_submit',
        'jogador.compartilhado_page',
    }

    if request.endpoint in liberadas:
        return None

    if not request.endpoint:
        return None

    if request.endpoint.startswith('static'):
        return None

    if not session.get('user_id'):
        return _resposta_nao_autenticado()

    if not _is_admin():
        permitidas_escrita_usuario = {
            'jogador.logout',
            'jogador.perfil_alterar_senha',
            'jogador.votacao_salvar',
        }

        bloqueadas_leitura_usuario = {
            'jogador.selecionar_jogadores',
            'jogador.sortear',
            'jogador.sortear_api',
            'jogador.resultado_partida_page',
        }

        if request.endpoint in bloqueadas_leitura_usuario:
            return _resposta_somente_leitura()

        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and request.endpoint not in permitidas_escrita_usuario:
            return _resposta_somente_leitura()

    return None


def _obter_times_do_ultimo_sorteio_global():
    sorteios = historico_service.listar_sorteios()
    if not sorteios:
        return []
    ultimo = sorteios[-1]
    return ultimo.get('times', [])


def _montar_sorteio_exportacao(sorteio_id, times, somas, diferenca, melhor_time, tem_aviso, aviso_msg):
    """Monta um payload serializável para exportação do último sorteio."""
    times_json = []
    for idx, time in enumerate(times):
        times_json.append({
            'numero': idx + 1,
            'jogadores': [j.para_dict() for j in time],
            'soma': somas[idx]
        })

    return {
        'sorteio_id': sorteio_id,
        'times': times_json,
        'num_times': len(times),
        'somas': somas,
        'diferenca': diferenca,
        'melhor_time': melhor_time,
        'tem_aviso': tem_aviso,
        'aviso_msg': aviso_msg
    }


def _salvar_ultimo_sorteio_sessao(payload):
    session['ultimo_sorteio'] = payload
    session.modified = True


def _assinatura_times_obj(times):
    """Cria assinatura estável de composição dos times a partir de objetos Jogador."""
    times_assinatura = []
    for time in times:
        nomes = sorted(getattr(j, 'nome', str(j)).strip().lower() for j in time)
        times_assinatura.append('|'.join(nomes))
    return '||'.join(sorted(times_assinatura))


def _assinatura_times_json(times_json):
    """Cria assinatura estável de composição dos times a partir de JSON serializado."""
    times_assinatura = []
    for time in times_json:
        jogadores = time.get('jogadores', [])
        nomes = sorted(str(j.get('nome', '')).strip().lower() for j in jogadores)
        times_assinatura.append('|'.join(nomes))
    return '||'.join(sorted(times_assinatura))


def _assinaturas_recentes_stack(limite=5):
    """Retorna assinaturas dos sorteios mais recentes da pilha de undo/redo."""
    pilha, indice_atual = undoredo_service.obter_historico()
    if not pilha or indice_atual < 0:
        return set()

    inicio = max(0, indice_atual - (limite - 1))
    recentes = pilha[inicio:indice_atual + 1]
    assinaturas = set()
    for item in recentes:
        assinatura = _assinatura_times_json(item.get('times', []))
        if assinatura:
            assinaturas.add(assinatura)
    return assinaturas


def _forcar_variacao_times(times, assinaturas_bloqueadas):
    """Força uma variação simples trocando jogadores entre times quando necessário."""
    if len(times) < 2:
        return None

    base_times = [time[:] for time in times]
    tentativas = 50
    for _ in range(tentativas):
        i, j = random.sample(range(len(base_times)), 2)
        if not base_times[i] or not base_times[j]:
            continue

        idx_i = random.randrange(len(base_times[i]))
        idx_j = random.randrange(len(base_times[j]))

        novo = [time[:] for time in base_times]
        novo[i][idx_i], novo[j][idx_j] = novo[j][idx_j], novo[i][idx_i]

        assinatura_nova = _assinatura_times_obj(novo)
        if assinatura_nova not in assinaturas_bloqueadas:
            return novo

    return None


def _sortear_diferente_do_anterior(presentes, tentativas_max=8):
    """Tenta gerar um sorteio diferente dos mais recentes para evitar repetição."""
    assinaturas_bloqueadas = _assinaturas_recentes_stack(limite=5)
    if 'ultimo_sorteio' in session:
        assinatura_sessao = _assinatura_times_json(session.get('ultimo_sorteio', {}).get('times', []))
        if assinatura_sessao:
            assinaturas_bloqueadas.add(assinatura_sessao)

    tentativas_max = max(10, tentativas_max)

    resultado = None
    for _ in range(max(1, tentativas_max)):
        candidato = BalanceadorTimes.sortear_multiplos_times_com_goleiros(presentes)
        assinatura_candidato = _assinatura_times_obj(candidato[0])
        resultado = candidato

        if not assinaturas_bloqueadas:
            return candidato

        if assinatura_candidato not in assinaturas_bloqueadas:
            return candidato

    # Fallback: força uma variação para o usuário não receber exatamente a mesma composição
    if resultado:
        variacao = _forcar_variacao_times(resultado[0], assinaturas_bloqueadas)
        if variacao:
            somas = [sum(j.nivel for j in time) for time in variacao]
            return variacao, somas, resultado[2], resultado[3]

    return resultado


@jogador_bp.route('/login', methods=['GET'])
def login_page():
    if session.get('user_id'):
        return redirect(url_for('jogador.index'))
    return render_template('login.html')


@jogador_bp.route('/cadastro', methods=['GET'])
def cadastro_page():
    if session.get('user_id'):
        return redirect(url_for('jogador.index'))
    return render_template('cadastro.html')


@jogador_bp.route('/cadastro', methods=['POST'])
def cadastro_submit():
    nome = request.form.get('nome', '').strip()
    username = request.form.get('username', '').strip()
    senha = request.form.get('password', '')
    confirmar = request.form.get('confirmar_password', '')
    nivel = request.form.get('nivel', '5')
    tipo = request.form.get('tipo', 'avulso')
    posicao = request.form.get('posicao', 'linha')

    if senha != confirmar:
        return render_template('cadastro.html', erro='A confirmacao de senha nao confere'), 400

    try:
        usuario = auth_service.criar_usuario(
            username=username,
            nome=nome,
            password=senha,
            role='usuario'
        )

        # Cada usuário novo já nasce com seu próprio jogador
        jogador_service.criar(
            nome=nome,
            nivel=int(nivel),
            tipo=tipo,
            posicao=posicao,
            owner_user_id=usuario.get('id')
        )

        return render_template(
            'login.html',
            sucesso='Cadastro realizado com sucesso! Entre com seu usuario e senha.'
        )
    except ValueError as e:
        return render_template('cadastro.html', erro=str(e)), 400


@jogador_bp.route('/login', methods=['POST'])
def login_submit():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    usuario = auth_service.autenticar(username, password)

    if not usuario:
        return render_template('login.html', erro='Usuario ou senha invalidos'), 401

    session['user_id'] = usuario['id']
    session['username'] = usuario['username']
    session['nome'] = usuario['nome']
    session['role'] = usuario['role']
    session.modified = True
    return redirect(url_for('jogador.index'))


@jogador_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    return redirect(url_for('jogador.login_page'))


@jogador_bp.route('/perfil', methods=['GET'])
@login_required
def perfil_page():
    jogador_proprio = None
    if not _is_admin():
        meus = jogador_service.listar_por_usuario(session.get('user_id'))
        jogador_proprio = meus[0] if meus else None
    return render_template('perfil.html', usuario=_usuario_logado(), jogador_proprio=jogador_proprio)


@jogador_bp.route('/perfil/senha', methods=['POST'])
@login_required
def perfil_alterar_senha():
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')

    if nova_senha != confirmar_senha:
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            erro_senha='A confirmacao de senha nao confere'
        ), 400


@jogador_bp.route('/votacao', methods=['GET'])
@login_required
def votacao_page():
    if _is_admin():
        return redirect(url_for('jogador.votacao_admin_page'))

    if session.get('role') != 'usuario':
        return _resposta_voto_somente_usuario()

    partida = votacao_service.obter_ativa_para_usuario(session.get('user_id'))
    if not partida:
        return render_template('votacao_usuario.html', partida=None, voto=None, participante=None)

    participante = next(
        (p for p in partida.get('participantes', []) if p.get('user_id') == session.get('user_id')),
        None
    )
    voto = votacao_service.obter_voto_usuario(partida.get('id'), session.get('user_id'))
    return render_template('votacao_usuario.html', partida=partida, participante=participante, voto=voto)


@jogador_bp.route('/votacao/salvar', methods=['POST'])
@login_required
def votacao_salvar():
    if _is_admin() or session.get('role') != 'usuario':
        return _resposta_voto_somente_usuario()

    partida_id = request.form.get('partida_id', type=int)
    try:
        votacao_service.salvar_voto(
            partida_id=partida_id,
            user_id=session.get('user_id'),
            gols=request.form.get('gols', 0, type=int),
            assistencias=request.form.get('assistencias', 0, type=int),
            venceu=(request.form.get('venceu') == '1'),
            destaque=(request.form.get('destaque') == '1'),
            nota=request.form.get('nota', 0, type=int)
        )
        return redirect(url_for('jogador.votacao_page'))
    except ValueError as e:
        partida = votacao_service.obter_ativa_para_usuario(session.get('user_id'))
        participante = None
        voto = None
        if partida:
            participante = next(
                (p for p in partida.get('participantes', []) if p.get('user_id') == session.get('user_id')),
                None
            )
            voto = votacao_service.obter_voto_usuario(partida.get('id'), session.get('user_id'))
        return render_template(
            'votacao_usuario.html',
            partida=partida,
            participante=participante,
            voto=voto,
            erro=str(e)
        ), 400


@jogador_bp.route('/admin/votacao', methods=['GET'])
@admin_required
def votacao_admin_page():
    ativa = votacao_service.obter_ativa()
    historico = votacao_service.listar()
    return render_template('votacao_admin.html', ativa=ativa, historico=historico)


@jogador_bp.route('/admin/votacao/criar', methods=['POST'])
@admin_required
def votacao_admin_criar():
    try:
        times = _obter_times_do_ultimo_sorteio_global()
        if not times:
            return render_template(
                'votacao_admin.html',
                ativa=votacao_service.obter_ativa(),
                historico=votacao_service.listar(),
                erro='Nao ha sorteio no historico para iniciar votacao'
            ), 400

        usuarios = auth_service.listar_usuarios()
        partida = votacao_service.criar_partida(
            times_json=times,
            usuarios=usuarios,
            criado_por=session.get('user_id'),
            titulo=request.form.get('titulo', '').strip()
        )
        return redirect(url_for('jogador.votacao_admin_page', partida_id=partida.get('id')))
    except ValueError as e:
        return render_template(
            'votacao_admin.html',
            ativa=votacao_service.obter_ativa(),
            historico=votacao_service.listar(),
            erro=str(e)
        ), 400


@jogador_bp.route('/admin/votacao/<int:partida_id>/encerrar', methods=['POST'])
@admin_required
def votacao_admin_encerrar(partida_id):
    try:
        votacao_service.encerrar_e_apurar(partida_id, session.get('user_id'))
        return redirect(url_for('jogador.votacao_admin_page', partida_id=partida_id))
    except ValueError as e:
        return render_template(
            'votacao_admin.html',
            ativa=votacao_service.obter_ativa(),
            historico=votacao_service.listar(),
            erro=str(e)
        ), 400

    try:
        auth_service.alterar_senha(
            user_id=session.get('user_id'),
            senha_atual=senha_atual,
            nova_senha=nova_senha
        )
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=(jogador_service.listar_por_usuario(session.get('user_id')) or [None])[0],
            sucesso_senha='Senha alterada com sucesso!'
        )
    except ValueError as e:
        return render_template(
            'perfil.html',
            usuario=_usuario_logado(),
            jogador_proprio=(jogador_service.listar_por_usuario(session.get('user_id')) or [None])[0],
            erro_senha=str(e)
        ), 400


@jogador_bp.route('/admin', methods=['GET'])
@admin_required
def admin_page():
    usuarios = auth_service.listar_usuarios()
    return render_template(
        'admin.html',
        usuarios=usuarios,
        sucesso=request.args.get('sucesso', ''),
        erro=request.args.get('erro', '')
    )


@jogador_bp.route('/admin/usuarios', methods=['POST'])
@admin_required
def admin_criar_usuario():
    try:
        username = request.form.get('username', '')
        nome = request.form.get('nome', '')
        password = request.form.get('password', '')
        role = request.form.get('role', 'usuario')
        auth_service.criar_usuario(username=username, nome=nome, password=password, role=role)
        return redirect(url_for('jogador.admin_page', sucesso='Usuario criado com sucesso'))
    except ValueError as e:
        usuarios = auth_service.listar_usuarios()
        return render_template('admin.html', usuarios=usuarios, erro=str(e)), 400


@jogador_bp.route('/admin/usuarios/<user_id>/ativo', methods=['POST'])
@admin_required
def admin_alterar_ativo_usuario(user_id):
    acao = request.form.get('acao', '').strip().lower()
    ativo = acao == 'ativar'

    try:
        auth_service.definir_ativo(
            user_id=user_id,
            ativo=ativo,
            executor_id=session.get('user_id')
        )
        mensagem = 'Usuario ativado com sucesso' if ativo else 'Usuario desativado com sucesso'
        return redirect(url_for('jogador.admin_page', sucesso=mensagem))
    except ValueError as e:
        return redirect(url_for('jogador.admin_page', erro=str(e)))


@jogador_bp.route('/')
def index():
    """Página inicial com lista de jogadores"""
    jogadores = _jogadores_visiveis()
    return render_template(
        'index.html',
        jogadores=jogadores,
        total_jogadores=len(jogadores)
    )


@jogador_bp.route('/api/jogadores', methods=['GET'])
def listar_jogadores_api():
    """API: Lista todos os jogadores"""
    jogadores = _jogadores_visiveis()
    return jsonify([j.para_dict() for j in jogadores])


@jogador_bp.route('/api/jogadores', methods=['POST'])
@admin_required
def criar_jogador_api():
    """API: Cria novo jogador"""
    try:
        dados = request.get_json(silent=True) or {}
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
@admin_required
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
    jogador = jogador_service.obter_por_id(jogador_id, None if _is_admin() else session.get('user_id'))
    if not jogador:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    return jsonify(jogador.para_dict())


@jogador_bp.route('/api/jogadores/<jogador_id>', methods=['PUT'])
@admin_required
def atualizar_jogador(jogador_id):
    """API: Atualiza jogador"""
    try:
        dados = request.get_json(silent=True) or {}
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
@admin_required
def deletar_jogador(jogador_id):
    """API: Deleta jogador"""
    sucesso = jogador_service.deletar(jogador_id)
    if not sucesso:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    return jsonify({'sucesso': True, 'mensagem': 'Jogador deletado com sucesso'})


@jogador_bp.route('/delete/<jogador_id>')
@admin_required
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
        dados = request.get_json(silent=True) or {}
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
        times, somas, tem_aviso, aviso_msg = _sortear_diferente_do_anterior(presentes)
        num_times = len(times)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico
        sorteio = historico_service.adicionar_sorteio(times, somas, num_times, diferenca)
        sorteio_id = sorteio.get('id')

        # Salvar para download/exportação
        sorteio_data = _montar_sorteio_exportacao(
            sorteio_id,
            times,
            somas,
            diferenca,
            melhor_time,
            tem_aviso,
            aviso_msg
        )

        _salvar_ultimo_sorteio_sessao(sorteio_data)

        # Adicionar à pilha de undo/redo também no fluxo de página
        undoredo_service.adicionar_sorteio(sorteio_data)
        
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
        times, somas, tem_aviso, aviso_msg = _sortear_diferente_do_anterior(presentes)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico
        sorteio = historico_service.adicionar_sorteio(times, somas, len(times), diferenca)

        sorteio_data = _montar_sorteio_exportacao(
            sorteio.get('id'),
            times,
            somas,
            diferenca,
            melhor_time,
            tem_aviso,
            aviso_msg
        )

        # Salvar para download/exportação
        _salvar_ultimo_sorteio_sessao(sorteio_data)

        # Adicionar à pilha de undo/redo
        undoredo_service.adicionar_sorteio(sorteio_data)
        
        return jsonify({
            'sucesso': True,
            'sorteio_id': sorteio.get('id'),
            'times': sorteio_data['times'],
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
@jogador_bp.route('/stats')
def estatisticas():
    return redirect(url_for('jogador.index'))


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
    return redirect(url_for('jogador.index'))


@jogador_bp.route('/stats/times', methods=['GET'])
def stats_times_page():
    return redirect(url_for('jogador.index'))


@jogador_bp.route('/stats/combos', methods=['GET'])
def stats_combos_page():
    return redirect(url_for('jogador.index'))


@jogador_bp.route('/charts', methods=['GET'])
def charts():
    return redirect(url_for('jogador.index'))


# ============================================================
# EXPORTAÇÃO DE DADOS
# ============================================================

@jogador_bp.route('/export/sorteio/csv', methods=['GET'])
def export_sorteio_csv():
    """Exporta o último sorteio realizado em CSV"""
    if 'ultimo_sorteio' not in session:
        return jsonify({'erro': 'Nenhum sorteio realizado'}), 400
    
    sorteio_data = session['ultimo_sorteio']
    
    times_json = sorteio_data.get('times', [])
    times = [time.get('jogadores', []) for time in times_json]
    somas = sorteio_data.get('somas', [])
    diferenca = sorteio_data.get('diferenca', 0)
    
    csv_content = export_service.exportar_sorteio_csv(
        times, somas, diferenca
    )
    
    return send_file(
        io.BytesIO(csv_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'sorteio_{sorteio_data.get("sorteio_id", sorteio_data.get("id", "resultado"))}.csv'
    )


@jogador_bp.route('/export/sorteio/txt', methods=['GET'])
def export_sorteio_txt():
    """Retorna o último sorteio em texto simples (sem download forçado)"""
    if 'ultimo_sorteio' not in session:
        return jsonify({'erro': 'Nenhum sorteio realizado'}), 400
    
    sorteio_data = session['ultimo_sorteio']
    
    times_json = sorteio_data.get('times', [])
    times = [time.get('jogadores', []) for time in times_json]
    somas = sorteio_data.get('somas', [])
    diferenca = sorteio_data.get('diferenca', 0)
    
    txt_content = export_service.exportar_sorteio_texto(
        times, somas, diferenca
    )

    return Response(txt_content, mimetype='text/plain; charset=utf-8')


@jogador_bp.route('/api/export/sorteio/txt', methods=['GET'])
def api_export_sorteio_txt():
    """API para copiar o texto do último sorteio"""
    if 'ultimo_sorteio' not in session:
        return jsonify({'sucesso': False, 'erro': 'Nenhum sorteio realizado'}), 400

    sorteio_data = session['ultimo_sorteio']
    times_json = sorteio_data.get('times', [])
    times = [time.get('jogadores', []) for time in times_json]
    somas = sorteio_data.get('somas', [])
    diferenca = sorteio_data.get('diferenca', 0)

    txt_content = export_service.exportar_sorteio_texto(
        times, somas, diferenca
    )

    return jsonify({'sucesso': True, 'conteudo': txt_content})


@jogador_bp.route('/export/sorteio/pdf', methods=['GET'])
def export_sorteio_pdf():
    """Exporta o último sorteio em PDF"""
    if 'ultimo_sorteio' not in session:
        return jsonify({'erro': 'Nenhum sorteio realizado'}), 400

    sorteio_data = session['ultimo_sorteio']
    times_json = sorteio_data.get('times', [])
    times = [time.get('jogadores', []) for time in times_json]
    somas = sorteio_data.get('somas', [])
    diferenca = sorteio_data.get('diferenca', 0)

    pdf_bytes = export_service.exportar_sorteio_pdf(
        times,
        somas,
        diferenca,
        sorteio_id=sorteio_data.get('sorteio_id', sorteio_data.get('id'))
    )

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'sorteio_{sorteio_data.get("sorteio_id", sorteio_data.get("id", "resultado"))}.pdf'
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
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'sucesso': False, 'erro': 'Corpo JSON invalido'}), 400
    session['ultimo_sorteio'] = data
    session.modified = True
    return jsonify({'sucesso': True, 'mensagem': 'Sorteio armazenado para exportação'})


# ============================================================
# MODO COMPETITIVO - PARTIDAS E CAMPEONATO
# ============================================================

@jogador_bp.route('/resultado_partida/<int:sorteio_id>')
@admin_required
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
@admin_required
def registrar_resultado_partida():
    """API: Registra resultado de uma partida"""
    try:
        dados = request.get_json(silent=True) or {}
        
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
    return redirect(url_for('jogador.index'))


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
        dados = request.get_json(silent=True) or {}
        
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
    return redirect(url_for('jogador.index'))


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
        dados = request.get_json(silent=True) or {}
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
        sorteio_data = request.get_json(silent=True) or {}
        if not sorteio_data:
            return jsonify({'sucesso': False, 'erro': 'Corpo JSON invalido'}), 400
        
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


# ===== SUGESTÕES INTELIGENTES =====
@jogador_bp.route('/api/sugestoes/nivel', methods=['POST'])
def api_sugestoes_nivel():
    """API: Sugestões por nível"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_nivel(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Sugestões por Nível'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/sugestoes/diversidade', methods=['POST'])
def api_sugestoes_diversidade():
    """API: Sugestões por diversidade"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_diversidade(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Menos Utilizados'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/sugestoes/vencedores', methods=['POST'])
def api_sugestoes_vencedores():
    """API: Sugestões por jogadores vencedores"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_vencedoras(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Jogadores Vencedores'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/sugestoes/duplas', methods=['POST'])
def api_sugestoes_duplas():
    """API: Sugestões por duplas vencedoras"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_melhores_duplas(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Duplas Vencedoras'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/sugestoes/combinadas', methods=['POST'])
def api_sugestoes_combinadas():
    """API: Sugestões combinadas (todas as estratégias)"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_combinadas(selecionados, todos, 3)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ===== RANKING DE JOGADORES =====
@jogador_bp.route('/ranking')
def pagina_ranking():
    dados = votacao_service.ranking_jogadores_geral(50)
    return render_template('ranking.html', dados=dados)


@jogador_bp.route('/api/ranking/geral')
def api_ranking_geral():
    """API: Ranking geral de jogadores"""
    try:
        limite = request.args.get('limite', 50, type=int)
        dados = votacao_service.ranking_jogadores_geral(limite)
        
        return jsonify({
            'sucesso': True,
            'dados': dados
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@jogador_bp.route('/api/ranking/periodo/<int:dias>')
def api_ranking_periodo(dias):
    return jsonify({'sucesso': False, 'erro': 'Endpoint desativado'}), 410


@jogador_bp.route('/api/ranking/stats')
def api_ranking_stats():
    return jsonify({'sucesso': False, 'erro': 'Endpoint desativado'}), 410
