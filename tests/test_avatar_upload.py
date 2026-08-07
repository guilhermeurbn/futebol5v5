"""
Testes automatizados para validação de segurança e upload de foto de perfil.
"""
import io
import pytest
from PIL import Image
from services.upload_service import UploadService, UploadError


def _criar_imagem_dummy_bytes(formato="PNG", largura=100, altura=100) -> io.BytesIO:
    """Cria um buffer binário de imagem válida para simular upload."""
    buffer = io.BytesIO()
    img = Image.new("RGB", (largura, altura), color=(34, 197, 94))
    img.save(buffer, format=formato)
    buffer.seek(0)
    return buffer


def test_upload_foto_valida(tmp_path):
    """Testa o processamento e salvamento de uma imagem válida."""
    pasta_teste = tmp_path / "avatars"
    service = UploadService(pasta_destino=str(pasta_teste))

    img_buffer = _criar_imagem_dummy_bytes("PNG")
    
    class DummyFileStorage:
        def __init__(self, buffer, filename):
            self.stream = buffer
            self.filename = filename
            self.tell = buffer.tell
            self.seek = buffer.seek

    dummy = DummyFileStorage(img_buffer, "minha_foto.png")
    url = service.processar_foto_perfil(dummy, user_id="user_123")

    assert url.startswith("/static/uploads/avatars/avatar_user_123_")
    assert url.endswith(".webp")
    assert (pasta_teste / url.split("/")[-1]).exists()


def test_upload_rejeita_extensao_invalida(tmp_path):
    """Garante que extensões perigosas ou inválidas sejam rejeitadas."""
    service = UploadService(pasta_destino=str(tmp_path))
    img_buffer = io.BytesIO(b"conteudo malicioso script")

    class DummyFileStorage:
        def __init__(self, buffer, filename):
            self.stream = buffer
            self.filename = filename
            self.tell = buffer.tell
            self.seek = buffer.seek

    dummy = DummyFileStorage(img_buffer, "script.exe")

    with pytest.raises(UploadError) as exc_info:
        service.processar_foto_perfil(dummy, user_id="user_123")

    assert "Formato de imagem inválido" in str(exc_info.value)


def test_upload_rejeita_arquivo_falso_com_extensao_png(tmp_path):
    """Garante que um arquivo de texto com extensão .png seja rejeitado na inspeção do Pillow."""
    service = UploadService(pasta_destino=str(tmp_path))
    falso_buffer = io.BytesIO(b"print('hack')")

    class DummyFileStorage:
        def __init__(self, buffer, filename):
            self.stream = buffer
            self.filename = filename
            self.tell = buffer.tell
            self.seek = buffer.seek

    dummy = DummyFileStorage(falso_buffer, "fake_image.png")

    with pytest.raises(UploadError) as exc_info:
        service.processar_foto_perfil(dummy, user_id="user_123")

    assert "não é uma imagem válida" in str(exc_info.value)


def test_remover_foto(tmp_path):
    """Testa a remoção de foto de perfil do disco."""
    pasta_teste = tmp_path / "avatars"
    service = UploadService(pasta_destino=str(pasta_teste))

    img_buffer = _criar_imagem_dummy_bytes("JPEG")

    class DummyFileStorage:
        def __init__(self, buffer, filename):
            self.stream = buffer
            self.filename = filename
            self.tell = buffer.tell
            self.seek = buffer.seek

    dummy = DummyFileStorage(img_buffer, "foto.jpg")
    url = service.processar_foto_perfil(dummy, user_id="user_test")

    filename = url.split("/")[-1]
    assert (pasta_teste / filename).exists()

    removido = service.remover_foto(url)
    assert removido is True
    assert not (pasta_teste / filename).exists()
