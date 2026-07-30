from pathlib import Path
import sys
from flask import session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import routes.auth_routes as auth_routes
from app import criar_app


def _fake_user():
    return {
        'id': 'user-delete-test',
        'username': 'deleteme',
        'nome': 'Delete Me',
        'role': 'usuario',
        'password_hash': 'scrypt:32768:8:1$dummy$dummyhash',
        'senha_temporaria_ativa': False,
    }


def test_delete_account_requires_login():
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        response = client.post('/perfil/apagar-conta', data={
            'confirmar_palavra': 'APAGAR',
            'senha': 'password123',
        })
        # Should redirect to login page
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')


def test_delete_account_invalid_word(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    
    monkeypatch.setattr(auth_routes.auth_service, 'obter_por_id', lambda uid: _fake_user())

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'user-delete-test'
            sess['username'] = 'deleteme'
            sess['nome'] = 'Delete Me'
            sess['role'] = 'usuario'

        response = client.post('/perfil/apagar-conta', data={
            'confirmar_palavra': 'WRONG_WORD',
            'senha': 'password123',
        })
        
        assert response.status_code == 400
        body = response.get_data(as_text=True)
        assert 'Você deve digitar a palavra APAGAR para confirmar.' in body


def test_delete_account_wrong_password(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    
    monkeypatch.setattr(auth_routes.auth_service, 'obter_por_id', lambda uid: _fake_user())
    monkeypatch.setattr('werkzeug.security.check_password_hash', lambda h, p: False)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'user-delete-test'
            sess['username'] = 'deleteme'
            sess['nome'] = 'Delete Me'
            sess['role'] = 'usuario'

        response = client.post('/perfil/apagar-conta', data={
            'confirmar_palavra': 'APAGAR',
            'senha': 'wrongpassword',
        })
        
        assert response.status_code == 400
        body = response.get_data(as_text=True)
        assert 'Senha atual incorreta. Confirmação falhou.' in body


def test_delete_account_success(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    
    deleted_called = []
    
    monkeypatch.setattr(auth_routes.auth_service, 'obter_por_id', lambda uid: _fake_user())
    monkeypatch.setattr('werkzeug.security.check_password_hash', lambda h, p: True)
    monkeypatch.setattr(auth_routes.auth_service, 'deletar_usuario', lambda uid, executor_id: deleted_called.append(uid))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'user-delete-test'
            sess['username'] = 'deleteme'
            sess['nome'] = 'Delete Me'
            sess['role'] = 'usuario'

        response = client.post('/perfil/apagar-conta', data={
            'confirmar_palavra': 'APAGAR',
            'senha': 'correctpassword',
        })
        
        # Should call deletion, clear session, and redirect to login
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')
        assert 'sucesso=' in response.headers.get('Location', '')
        assert 'user-delete-test' in deleted_called

        # Session should be empty
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


def test_delete_account_admin_fails(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    
    admin_user = _fake_user()
    admin_user['role'] = 'admin'
    
    monkeypatch.setattr(auth_routes.auth_service, 'obter_por_id', lambda uid: admin_user)
    monkeypatch.setattr('werkzeug.security.check_password_hash', lambda h, p: True)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'user-delete-test'
            sess['username'] = 'deleteme'
            sess['nome'] = 'Delete Me'
            sess['role'] = 'admin'

        response = client.post('/perfil/apagar-conta', data={
            'confirmar_palavra': 'APAGAR',
            'senha': 'correctpassword',
        })
        
        assert response.status_code == 400
        body = response.get_data(as_text=True)
        assert 'Administradores não podem excluir sua própria conta.' in body
