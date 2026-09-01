import os
import io
import base64
import pytest
from PIL import Image
from services.upload_service import UploadService
from services.partida_service import PartidaService

def test_processar_foto_campeao_base64(tmp_path):
    # Criar uma imagem simples 100x100 para o teste em base64
    img = Image.new('RGB', (100, 100), color='green')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    b64_str = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')

    upload_svc = UploadService()
    url = upload_svc.processar_foto_campeao(base64_data=b64_str, sorteio_id=99)
    assert url is not None
    assert "campeao_99_" in url

def test_registrar_resultado_com_card_campeao():
    partida_svc = PartidaService()
    card_url = "/static/uploads/cards/campeao_test_123.webp"
    partida = partida_svc.registrar_resultado(
        sorteio_id=9999,
        time_vencedor=1,
        gols_times=[3, 1],
        notas="Teste campeao",
        times_desempenho=[{"time_numero": 1, "vitorias": 1, "empates": 0, "derrotas": 0, "gols": 3}],
        card_campeao_url=card_url
    )
    assert partida.get("card_campeao_url") == card_url
