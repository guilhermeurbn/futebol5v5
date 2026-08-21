"""
Teste para validação do parse de CLOUDINARY_URL e inicialização do Cloudinary.
"""
import os
import io
import pytest
from unittest.mock import patch, MagicMock
from services.upload_service import UploadService
from werkzeug.datastructures import FileStorage
from PIL import Image


def test_cloudinary_url_parsing():
    dummy_img = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    dummy_img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    file_storage = FileStorage(stream=img_byte_arr, filename="avatar_test.png", content_type="image/png")

    env = {
        "CLOUDINARY_URL": "cloudinary://123456789012345:dummy_api_secret_key@dummy_cloud_name"
    }

    with patch.dict(os.environ, env, clear=True):
        with patch("cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/dummy_cloud_name/image/upload/v123/avatar.webp"}
            
            us = UploadService()
            url_resultado = us.processar_foto_perfil(file_storage, user_id="user_test_123")

            assert url_resultado == "https://res.cloudinary.com/dummy_cloud_name/image/upload/v123/avatar.webp"
            assert mock_upload.called
