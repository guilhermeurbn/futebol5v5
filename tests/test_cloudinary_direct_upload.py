"""
Testes unitários e de integração para o novo sistema de upload direto assinado ao Cloudinary,
armazenamento de metadados em PostgreSQL e transformações de URL CDN.
"""
import os
import pytest
from services.upload_service import UploadService, UploadError
from services.db import salvar_image_asset, obter_image_asset
from app import criar_app


@pytest.fixture
def app():
    os.environ['CLOUDINARY_CLOUD_NAME'] = 'test_cloud'
    os.environ['CLOUDINARY_API_KEY'] = '123456789'
    os.environ['CLOUDINARY_API_SECRET'] = 'secret_test_key'
    app_inst = criar_app('testing')
    app_inst.config['WTF_CSRF_ENABLED'] = False
    return app_inst


@pytest.fixture
def client(app):
    return app.test_client()


def test_gerar_assinatura_upload(app):
    service = UploadService()
    res = service.gerar_assinatura_upload(folder="futebol5v5/avatars", public_id="avatar_user123", timestamp=1700000000)
    assert res is not None
    assert res['cloud_name'] == 'test_cloud'
    assert res['api_key'] == '123456789'
    assert res['folder'] == "futebol5v5/avatars"
    assert res['public_id'] == "avatar_user123"
    assert res['signature'] is not None
    assert len(res['signature']) == 40  # HMAC-SHA1 hex length


def test_salvar_e_obter_image_asset():
    asset_data = {
        "asset_id": "asset_test_999",
        "public_id": "futebol5v5/cards/campeao_99",
        "resource_type": "image",
        "format": "jpg",
        "width": 1080,
        "height": 1620,
        "bytes": 250000,
        "secure_url": "https://res.cloudinary.com/test_cloud/image/upload/futebol5v5/cards/campeao_99.jpg",
        "entity_type": "card",
        "entity_id": "99"
    }

    record = salvar_image_asset(asset_data)
    assert record['asset_id'] == "asset_test_999"
    assert record['public_id'] == "futebol5v5/cards/campeao_99"

    fetched = obter_image_asset("futebol5v5/cards/campeao_99")
    assert fetched['asset_id'] == "asset_test_999"
    assert fetched['width'] == 1080


def test_gerar_url_otimizada():
    # 1. URL Cloudinary completa
    cloud_url = "https://res.cloudinary.com/test_cloud/image/upload/v1/futebol5v5/avatars/user1.jpg"
    opt = UploadService.gerar_url_otimizada(cloud_url, width=200, height=200, crop="fill")
    assert "f_auto,q_auto" in opt
    assert "w_200" in opt
    assert "h_200" in opt

    # 2. Caminho local estático (compatibilidade legada)
    local_url = "/static/uploads/avatars/avatar_old.webp"
    opt_local = UploadService.gerar_url_otimizada(local_url, width=200)
    assert opt_local == local_url


def test_rota_sign_upload_requer_auth(client):
    res = client.post('/api/cloudinary/sign-upload', json={'tipo': 'avatar', 'entity_id': '123'})
    assert res.status_code == 401


def test_rota_sign_upload_com_sucesso(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'user_test_456'
        sess['role'] = 'usuario'

    res = client.post('/api/cloudinary/sign-upload', json={'tipo': 'avatar', 'entity_id': 'user_test_456'})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['sucesso'] is True
    assert json_data['data']['cloud_name'] == 'test_cloud'
    assert json_data['data']['signature'] is not None


def test_rota_register_asset_com_sucesso(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'user_test_789'
        sess['role'] = 'usuario'

    payload = {
        "asset_id": "asset_reg_123",
        "public_id": "futebol5v5/avatars/avatar_user789",
        "secure_url": "https://res.cloudinary.com/test_cloud/image/upload/futebol5v5/avatars/avatar_user789.jpg",
        "format": "jpg",
        "width": 300,
        "height": 300,
        "entity_type": "avatar",
        "entity_id": "user_test_789"
    }

    res = client.post('/api/cloudinary/register-asset', json=payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['sucesso'] is True
    assert json_data['url'] == payload['secure_url']


def test_rota_upload_local_fallback(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'user_test_local'
        sess['role'] = 'usuario'

    base64_pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    res = client.post('/api/cloudinary/upload-local', json={
        'tipo': 'avatar',
        'entity_id': 'user_test_local',
        'base64': base64_pixel
    })
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['sucesso'] is True
    assert '/static/uploads/' in json_data['url']
