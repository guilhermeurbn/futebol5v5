import sys
from app import criar_app

app = criar_app('testing')
app.config['WTF_CSRF_ENABLED'] = False

import pytest
from unittest.mock import MagicMock

with app.test_request_context():
    with app.test_client() as client:
        # Mock session to simulate an admin
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin-id-123'
            sess['role'] = 'admin'
            sess['username'] = 'admin_user'

        # Patch admin route dependencies
        import routes.admin_routes as ar
        ar.auth_service.listar_usuarios = MagicMock(return_value=[])
        ar.notificacao_service.listar_notificacoes = MagicMock(return_value=[])
        ar.notificacao_service.contar_nao_lidas = MagicMock(return_value=0)

        response = client.get('/admin')
        print("STATUS:", response.status_code)
        body = response.get_data(as_text=True)
        
        # Locate the footer
        footer_start = body.find('<footer class="site-footer')
        if footer_start != -1:
            footer_end = body.find('</footer>', footer_start) + len('</footer>')
            print("FOOTER NAV RENDERED:")
            print(body[footer_start:footer_end])
        else:
            print("NO FOOTER RENDERED!")
