from datetime import datetime, timedelta

import app as app_module
from app import criar_app
from routes import juiz_routes, partida_routes, votacao_routes
from services.votacao_service import VotacaoService


def _times():
    return [{
        'numero': 1,
        'jogadores': [
            {'nome': f'Jogador {idx}', 'owner_user_id': f'u{idx}'}
            for idx in range(1, 6)
        ],
    }]


def _usuarios():
    return [
        {'id': f'u{idx}', 'username': f'user{idx}', 'nome': f'Usuario {idx}'}
        for idx in range(1, 6)
    ]


def _votos():
    return [
        {'jogador_nome': f'Jogador {idx}', 'time_numero': 1, 'nota': 8}
        for idx in range(1, 6)
    ]


def test_voting_window_is_twelve_hours(tmp_path):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    partida = service.criar_partida(
        _times(),
        _usuarios(),
        'juiz',
        sorteio_id=1,
        duracao_horas=12,
    )

    aberta = datetime.fromisoformat(partida['aberta_em'])
    fecha = datetime.fromisoformat(partida['fecha_em'])
    assert fecha - aberta == timedelta(hours=12)


def test_voting_closes_when_every_eligible_player_votes(tmp_path):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    partida = service.criar_partida(
        _times(),
        _usuarios(),
        'juiz',
        sorteio_id=1,
        duracao_horas=12,
    )

    for idx in range(1, 6):
        service.salvar_voto(partida['id'], f'u{idx}', _votos())

    encerrada = service.obter_partida(partida['id'])
    assert encerrada['status'] == 'encerrada'
    assert encerrada['encerramento_motivo'] == 'todos_votaram'
    assert encerrada['ranking']['total_votos'] == 5
    assert encerrada['ranking']['melhor_jogador']


def test_judge_rating_is_not_part_of_voting(tmp_path):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    partida = service.criar_partida(
        _times(),
        _usuarios(),
        'juiz',
        sorteio_id=1,
        duracao_horas=12,
    )

    assert 'avaliacao_juiz' not in partida


def test_orphan_user_links_do_not_block_automatic_close(tmp_path):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    times = _times()
    times[0]['jogadores'].append({'nome': 'Externo', 'owner_user_id': 'usuario-inexistente'})
    partida = service.criar_partida(
        times,
        _usuarios(),
        'juiz',
        sorteio_id=1,
        duracao_horas=12,
    )

    for idx in range(1, 6):
        service.salvar_voto(partida['id'], f'u{idx}', _votos())

    encerrada = service.obter_partida(partida['id'])
    externo = next(p for p in encerrada['participantes'] if p['jogador_nome'] == 'Externo')
    assert externo['user_id'] is None
    assert externo['externo'] is True
    assert encerrada['encerramento_motivo'] == 'todos_votaram'


def test_legacy_player_is_linked_by_unique_normalized_name(tmp_path):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    times = [{
        'numero': 1,
        'jogadores': [{'nome': 'André Balada', 'owner_user_id': None}],
    }]
    usuarios = [{
        'id': 'andre-id',
        'username': 'andre_balada',
        'nome': 'Andre Balada',
        'role': 'usuario',
        'ativo': True,
    }]

    partida = service.criar_partida(
        times,
        usuarios,
        'juiz',
        sorteio_id=1,
    )

    assert partida['participantes'][0]['user_id'] == 'andre-id'
    assert partida['participantes'][0]['externo'] is False


def test_ambiguous_legacy_name_is_not_linked(tmp_path):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    times = [{
        'numero': 1,
        'jogadores': [{'nome': 'Guilherme', 'owner_user_id': None}],
    }]
    usuarios = [
        {'id': 'u1', 'username': 'gui1', 'nome': 'Guilherme', 'role': 'usuario', 'ativo': True},
        {'id': 'u2', 'username': 'gui2', 'nome': 'Guilherme', 'role': 'usuario', 'ativo': True},
    ]

    partida = service.criar_partida(
        times,
        usuarios,
        'juiz',
        sorteio_id=1,
    )

    assert partida['participantes'][0]['user_id'] is None


def test_pending_vote_notification_is_shown_only_until_user_votes(tmp_path, monkeypatch):
    service = VotacaoService(str(tmp_path / 'votacoes.json'))
    partida = service.criar_partida(
        _times(),
        _usuarios(),
        'juiz',
        titulo='Rodada decisiva',
        sorteio_id=1,
    )
    monkeypatch.setattr(app_module, 'votacao_service', service)

    app = criar_app('testing')
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'u1'
            sess['username'] = 'user1'
            sess['nome'] = 'Usuario 1'
            sess['role'] = 'usuario'
            sess['senha_temporaria_ativa'] = False

        response = client.get('/')
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'player-vote-notification' in body
        assert 'Votação aberta' in body
        assert 'Rodada decisiva' in body
        assert 'Minha votação' in body

        service.salvar_voto(partida['id'], 'u1', _votos())
        response = client.get('/')

        assert response.status_code == 200
        assert 'player-vote-notification' not in response.get_data(as_text=True)


def _login_juiz(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'juiz-id'
        sess['username'] = 'juiz'
        sess['nome'] = 'Juiz'
        sess['role'] = 'juiz'
        sess['senha_temporaria_ativa'] = False


def _login_usuario(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'user-id'
        sess['username'] = 'usuario'
        sess['nome'] = 'Usuario'
        sess['role'] = 'usuario'
        sess['senha_temporaria_ativa'] = False


def test_share_page_renders_selected_draw(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteio = {
        'id': 7,
        'total_jogadores': 5,
        'num_times': 1,
        'pontuacoes': [25],
        'diferenca': 0,
        'times': [{
            'numero': 1,
            'jogadores': [{'nome': 'Jogador 1'}],
        }],
    }
    monkeypatch.setattr(
        partida_routes.historico_service,
        'obter_sorteio',
        lambda sorteio_id: sorteio if sorteio_id == 7 else None,
    )

    with app.test_client() as client:
        _login_juiz(client)
        response = client.get('/sorteio/7/compartilhar')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Times do sorteio #7' in body
    assert '>Copiar<' in body
    assert 'Baixar PDF' in body


def test_judge_draw_page_uses_dedicated_times_workspace(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteio = {
        'id': 7,
        'total_jogadores': 5,
        'num_times': 1,
        'pontuacoes': [25],
        'diferenca': 0,
        'times': [{
            'numero': 1,
            'jogadores': [{
                'nome': 'Jogador 1',
                'nivel': 5,
                'posicao': 'linha',
            }],
        }],
    }
    monkeypatch.setattr(
        partida_routes.historico_service,
        'obter_sorteio',
        lambda sorteio_id: sorteio if sorteio_id == 7 else None,
    )
    monkeypatch.setattr(
        partida_routes.votacao_service,
        'obter_por_sorteio',
        lambda sorteio_id: None,
    )
    monkeypatch.setattr(
        partida_routes.partida_service,
        'obter_partidas_sorteio',
        lambda sorteio_id: [],
    )

    with app.test_client() as client:
        _login_juiz(client)
        response = client.get('/sorteio/7')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'judge-teams-page' in body
    assert 'Times' in body
    assert 'Ir para votações' in body
    assert 'Histórico de sorteios' not in body


def test_judge_history_has_its_own_page(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteios = [
        {
            'id': 6,
            'data': '2026-06-12T20:00:00',
            'total_jogadores': 10,
            'num_times': 2,
            'diferenca': 1,
            'times': _times(),
        },
        {
            'id': 7,
            'data': '2026-06-13T20:00:00',
            'total_jogadores': 10,
            'num_times': 2,
            'diferenca': 0,
            'times': _times(),
        },
    ]
    monkeypatch.setattr(juiz_routes.historico_service, 'listar_sorteios', lambda: sorteios)
    monkeypatch.setattr(
        juiz_routes.juiz_partida_service,
        'obter_estado',
        lambda: {'status': 'sorteada', 'partida_atual': {'sorteio_id': 7}},
    )

    with app.test_client() as client:
        _login_juiz(client)
        response = client.get('/jogar/historico')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'judge-history-page' in body
    assert 'Histórico de sorteios' in body
    assert body.index('Sorteio #7') < body.index('Sorteio #6')


def test_judge_create_redirects_to_open_draw(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    monkeypatch.setattr(
        juiz_routes,
        '_sincronizar_fluxo_juiz',
        lambda: {'status': 'sorteada', 'partida_atual': {'sorteio_id': 23}},
    )

    def fail_if_started(*_args, **_kwargs):
        raise AssertionError('nao deve iniciar nova partida com sorteio aberto')

    monkeypatch.setattr(juiz_routes.juiz_partida_service, 'iniciar_partida', fail_if_started)
    monkeypatch.setattr(juiz_routes.jogador_service, 'limpar_presenca', fail_if_started)

    with app.test_client() as client:
        _login_juiz(client)
        response = client.post('/jogar/criar-partida')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/jogar/times?sorteio_id=23')


def test_judge_create_allows_selection_without_draw(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    monkeypatch.setattr(
        juiz_routes,
        '_sincronizar_fluxo_juiz',
        lambda: {'status': 'selecionando', 'partida_atual': {'sorteio_id': None}},
    )
    monkeypatch.setattr(juiz_routes.jogador_service, 'limpar_presenca', lambda: None)
    monkeypatch.setattr(juiz_routes.juiz_partida_service, 'iniciar_partida', lambda *_args: None)
    monkeypatch.setattr(juiz_routes.jogador_service, 'listar', lambda: [])

    with app.test_client() as client:
        _login_juiz(client)
        response = client.post('/jogar/criar-partida')

    assert response.status_code == 200
    assert 'Quem vai jogar?' in response.get_data(as_text=True)


def test_public_history_renders_inline_round_summary(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    sorteios = [{
        'id': 11,
        'data': '2026-06-15T20:00:00',
        'total_jogadores': 10,
        'num_times': 2,
        'diferenca': 1,
        'times': [
            {
                'numero': 1,
                'jogadores': [
                    {'nome': 'Jogador 1'},
                    {'nome': 'Jogador 2'},
                ],
            },
            {
                'numero': 2,
                'jogadores': [
                    {'nome': 'Jogador 3'},
                    {'nome': 'Jogador 4'},
                ],
            },
        ],
    }]
    resultado = {
        'id': 77,
        'data': '2026-06-15T21:00:00',
        'gols_times': [3, 2],
        'times_desempenho': [
            {'time_numero': 1, 'vitorias': 1, 'empates': 0, 'derrotas': 0},
            {'time_numero': 2, 'vitorias': 0, 'empates': 0, 'derrotas': 1},
        ],
    }
    votacao = {
        'id': 88,
        'status': 'encerrada',
        'ranking': {
            'ranking_jogadores': [
                {'jogador_nome': 'Jogador 1', 'time_numero': 1, 'votos': 4, 'nota_media': 8.5},
            ],
            'melhor_jogador': {'jogador_nome': 'Jogador 1', 'votos': 4, 'nota_media': 8.5},
            'media_geral': 8.5,
            'total_jogadores': 1,
        },
    }

    monkeypatch.setattr(partida_routes.historico_service, 'listar_sorteios', lambda: sorteios)
    monkeypatch.setattr(partida_routes.partida_service, 'obter_partidas_sorteio', lambda sorteio_id: [resultado] if sorteio_id == 11 else [])
    monkeypatch.setattr(partida_routes.votacao_service, 'obter_por_sorteio', lambda sorteio_id: votacao if sorteio_id == 11 else None)

    with app.test_client() as client:
        _login_usuario(client)
        response = client.get('/historico')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Sorteio #11' in body
    assert 'Resultado lançado' in body
    assert 'Status da votação: encerrada' in body
    assert 'Ver ranking' in body
    assert 'Ver resultado' not in body


def test_judge_voting_context_cannot_mix_draws(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteios = [
        {'id': 8, 'times': _times()},
        {'id': 9, 'times': _times()},
    ]
    ativa_outro_sorteio = {
        'id': 99,
        'sorteio_id': 9,
        'status': 'aberta',
        'votos': [{'user_id': 'u1'}],
    }
    monkeypatch.setattr(votacao_routes.historico_service, 'listar_sorteios', lambda: sorteios)
    monkeypatch.setattr(votacao_routes.votacao_service, 'obter_ativa', lambda: ativa_outro_sorteio)
    monkeypatch.setattr(votacao_routes.votacao_service, 'listar', lambda: [ativa_outro_sorteio])
    monkeypatch.setattr(
        votacao_routes.votacao_service,
        'obter_por_sorteio',
        lambda sorteio_id: ativa_outro_sorteio if sorteio_id == 9 else None,
    )
    monkeypatch.setattr(
        votacao_routes.partida_service,
        'obter_partidas_sorteio',
        lambda sorteio_id: [],
    )
    monkeypatch.setattr(
        votacao_routes.juiz_partida_service,
        'obter_estado',
        lambda: {
            'status': 'sorteada',
            'partida_atual': {
                'sorteio_id': 8,
                'avaliacao_juiz': None,
                'votacao_partida_id': None,
            },
        },
    )

    with app.test_request_context('/admin/votacao?sorteio_id=9'):
        from flask import session

        session['user_id'] = 'juiz-id'
        session['role'] = 'juiz'
        contexto = votacao_routes._resolver_contexto_admin(sorteio_id_hint=9)

    assert contexto['selected_sorteio_id'] == 8
    assert contexto['ativa'] is None
    assert contexto['voted_user_ids'] == set()


def test_judge_cannot_open_vote_for_another_draw(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteio = {
        'id': 9,
        'times': _times(),
    }
    monkeypatch.setattr(
        votacao_routes.historico_service,
        'obter_sorteio',
        lambda sorteio_id: sorteio if sorteio_id == 9 else None,
    )
    monkeypatch.setattr(
        votacao_routes.juiz_partida_service,
        'obter_estado',
        lambda: {
            'partida_atual': {
                'sorteio_id': 8,
            },
        },
    )
    monkeypatch.setattr(
        votacao_routes.historico_service,
        'listar_sorteios',
        lambda: [sorteio],
    )
    monkeypatch.setattr(
        votacao_routes.votacao_service,
        'obter_ativa',
        lambda: None,
    )
    monkeypatch.setattr(
        votacao_routes.votacao_service,
        'listar',
        lambda: [],
    )
    monkeypatch.setattr(
        votacao_routes.votacao_service,
        'obter_por_sorteio',
        lambda sorteio_id: None,
    )

    with app.test_client() as client:
        _login_juiz(client)
        response = client.post('/admin/votacao/criar', data={'sorteio_id': '9'})

    assert response.status_code == 400
    assert 'nao pertence a partida atual' in response.get_data(as_text=True)


def test_judge_registers_team_result_before_voting(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteio = {
        'id': 8,
        'times': [
            {'numero': 1, 'jogadores': [{'nome': 'A'}]},
            {'numero': 2, 'jogadores': [{'nome': 'B'}]},
        ],
    }
    salvo = {}

    monkeypatch.setattr(votacao_routes.historico_service, 'listar_sorteios', lambda: [sorteio])
    monkeypatch.setattr(votacao_routes.votacao_service, 'obter_ativa', lambda: None)
    monkeypatch.setattr(votacao_routes.votacao_service, 'obter_por_sorteio', lambda sorteio_id: None)
    monkeypatch.setattr(votacao_routes.partida_service, 'obter_partidas_sorteio', lambda sorteio_id: [])
    monkeypatch.setattr(
        votacao_routes.juiz_partida_service,
        'obter_estado',
        lambda: {'partida_atual': {'sorteio_id': 8}},
    )

    def registrar_resultado(**dados):
        salvo.update(dados)
        return {'id': 31, **dados}

    monkeypatch.setattr(votacao_routes.partida_service, 'registrar_resultado', registrar_resultado)
    monkeypatch.setattr(
        votacao_routes.juiz_partida_service,
        'marcar_resultado_registrado',
        lambda sorteio_id, resultado_id: salvo.update(
            {'estado_sorteio_id': sorteio_id, 'resultado_id': resultado_id}
        ),
    )

    with app.test_client() as client:
        _login_juiz(client)
        response = client.post('/admin/votacao/resultado', data={
            'sorteio_id': '8',
            'vitorias_1': '2',
            'empates_1': '1',
            'derrotas_1': '1',
            'gols_1': '9',
            'vitorias_2': '1',
            'empates_2': '1',
            'derrotas_2': '2',
            'gols_2': '7',
        })

    assert response.status_code == 302
    assert salvo['gols_times'] == [9, 7]
    assert salvo['times_desempenho'][0]['vitorias'] == 2
    assert salvo['resultado_id'] == 31


def test_judge_result_accepts_unbalanced_wins_and_losses(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    sorteio = {
        'id': 8,
        'times': [
            {'numero': 1, 'jogadores': [{'nome': 'A'}]},
            {'numero': 2, 'jogadores': [{'nome': 'B'}]},
        ],
    }

    monkeypatch.setattr(votacao_routes.historico_service, 'listar_sorteios', lambda: [sorteio])
    monkeypatch.setattr(votacao_routes.votacao_service, 'obter_ativa', lambda: None)
    monkeypatch.setattr(votacao_routes.votacao_service, 'obter_por_sorteio', lambda sorteio_id: None)
    monkeypatch.setattr(votacao_routes.partida_service, 'obter_partidas_sorteio', lambda sorteio_id: [])
    monkeypatch.setattr(
        votacao_routes.juiz_partida_service,
        'obter_estado',
        lambda: {'partida_atual': {'sorteio_id': 8}},
    )
    monkeypatch.setattr(
        votacao_routes.partida_service,
        'registrar_resultado',
        lambda **dados: {'id': 31, **dados}
    )
    monkeypatch.setattr(
        votacao_routes.juiz_partida_service,
        'marcar_resultado_registrado',
        lambda sorteio_id, resultado_id: None
    )

    with app.test_client() as client:
        _login_juiz(client)
        response = client.post('/admin/votacao/resultado', data={
            'sorteio_id': '8',
            'vitorias_1': '2',
            'empates_1': '0',
            'derrotas_1': '0',
            'gols_1': '5',
            'vitorias_2': '0',
            'empates_2': '0',
            'derrotas_2': '1',
            'gols_2': '2',
        })

    assert response.status_code == 302


def test_judge_last_match_clickable_navigation(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    ultima_partida = {
        'titulo': 'Votação do sorteio #37',
        'sorteio_id': 37,
        'partida_id': 36,
        'encerrado_em': '2026-07-15T12:31:06.667581',
        'resultado_resumido': [
            {'time_numero': 1, 'gols': 3, 'vitorias': 2, 'empates': 0, 'derrotas': 1, 'resultado': 'vitoria'},
            {'time_numero': 2, 'gols': 1, 'vitorias': 1, 'empates': 0, 'derrotas': 2, 'resultado': 'derrota'},
        ]
    }

    # Mock the judge state to have an ultima_partida_encerrada
    monkeypatch.setattr(
        juiz_routes.juiz_partida_service,
        'obter_estado',
        lambda: {
            'status': 'idle',
            'partida_atual': None,
            'ultima_partida_encerrada': ultima_partida
        }
    )

    # Mock list_sorteios to return the matching sorteio so it gets rendered in history
    sorteios = [
        {
            'id': 37,
            'data': '2026-07-15T12:30:00',
            'total_jogadores': 10,
            'num_times': 2,
            'diferenca': 0,
            'times': [
                {'numero': 1, 'jogadores': []},
                {'numero': 2, 'jogadores': []}
            ]
        }
    ]
    monkeypatch.setattr(juiz_routes.historico_service, 'listar_sorteios', lambda: sorteios)

    with app.test_client() as client:
        _login_juiz(client)
        # Check that the home page displays the card and link correctly
        response = client.get('/jogar')
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert 'judge-last-match-card' in body
        assert 'href="/jogar/historico?sorteio_id=37#sorteio-37"' in body
        assert 'Time 1' in body
        assert '2V' in body
        assert '3 gol' in body

        # Check that going to the history page with a sorteio_id opens it
        response_hist = client.get('/jogar/historico?sorteio_id=37')
        assert response_hist.status_code == 200
        body_hist = response_hist.get_data(as_text=True)
        # The history template opens the details item matching the ID and sets correct id attribute
        assert 'id="sorteio-37"' in body_hist
        assert 'open' in body_hist
