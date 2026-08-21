"""
Serviço seguro de processamento, validação e otimização de uploads de fotos de perfil.
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Configurações de segurança para upload
EXTENSOES_PERMITIDAS = {'.png', '.jpg', '.jpeg', '.webp'}
TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB
LARGURA_AVATAR_PX = 300
ALTURA_AVATAR_PX = 300
DIRETORIO_UPLOADS = os.path.join("static", "uploads", "avatars")


class UploadError(Exception):
    """Exceção customizada para erros de upload e validação de imagem."""
    pass


class UploadService:
    """Gerencia o recebimento, validação e otimização de fotos de perfil."""

    def __init__(self, pasta_destino: str = DIRETORIO_UPLOADS):
        self.pasta_destino = os.path.abspath(pasta_destino)
        os.makedirs(self.pasta_destino, exist_ok=True)

    def processar_foto_perfil(self, file_storage, user_id: str, foto_antiga_url: Optional[str] = None) -> str:
        """Recebe o FileStorage do Flask, valida a segurança e salva a imagem otimizada.

        Retorna a URL relativa estática para salvamento no banco de dados (ex: '/static/uploads/avatars/avatar_123.webp').
        """
        if not file_storage or not file_storage.filename:
            raise UploadError("Nenhum arquivo de imagem foi enviado")

        filename = secure_filename(file_storage.filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in EXTENSOES_PERMITIDAS:
            raise UploadError("Formato de imagem inválido. Use apenas PNG, JPG ou WEBP.")

        # 1. Validação do tamanho do arquivo em memória/disco
        file_storage.seek(0, os.SEEK_END)
        tamanho = file_storage.tell()
        file_storage.seek(0)

        if tamanho == 0:
            raise UploadError("O arquivo enviado está vazio")

        if tamanho > TAMANHO_MAXIMO_BYTES:
            raise UploadError("A imagem excede o tamanho máximo de 5MB")

        # 2. Validação profunda de segurança com Pillow (inspeção do cabeçalho binário)
        try:
            img = Image.open(file_storage.stream)
            img.verify()
        except Exception as e:
            logger.warning("Falha de segurança ao verificar cabeçalho da imagem para user %s: %s", user_id, e)
            raise UploadError("O arquivo enviado não é uma imagem válida ou está corrompido")

        # Re-abrir a imagem para manipulação após o .verify()
        file_storage.seek(0)
        img = Image.open(file_storage.stream)

        # 3. Correção de orientação EXIF (para fotos tiradas em celulares)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # 4. Redimensionamento e corte quadrado centralizado (Center Crop 300x300)
        img_quadrada = ImageOps.fit(
            img,
            (LARGURA_AVATAR_PX, ALTURA_AVATAR_PX),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        # 5. Se o Cloudinary estiver configurado nas variáveis de ambiente, enviar para a nuvem
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        cloudinary_url = os.getenv("CLOUDINARY_URL")

        if cloudinary_url or (cloud_name and api_key and api_secret):
            try:
                import io
                import cloudinary
                import cloudinary.uploader
                from urllib.parse import urlparse

                c_cloud = cloud_name
                c_key = api_key
                c_secret = api_secret

                if cloudinary_url:
                    parsed = urlparse(cloudinary_url)
                    if parsed.hostname and parsed.username and parsed.password:
                        c_cloud = parsed.hostname
                        c_key = parsed.username
                        c_secret = parsed.password

                if c_cloud and c_key and c_secret:
                    cloudinary.config(
                        cloud_name=c_cloud,
                        api_key=c_key,
                        api_secret=c_secret,
                        secure=True
                    )

                    if img_quadrada.mode != "RGB":
                        img_quadrada = img_quadrada.convert("RGB")

                    buffer = io.BytesIO()
                    img_quadrada.save(buffer, format="WEBP", quality=85, optimize=True)
                    buffer.seek(0)

                    nome_publico = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}"
                    res = cloudinary.uploader.upload(
                        buffer,
                        folder="futebol5v5/avatars",
                        public_id=nome_publico,
                        overwrite=True,
                        resource_type="image"
                    )
                    url_nuvem = res.get("secure_url") or res.get("url")
                    if url_nuvem:
                        logger.info("Foto enviada com sucesso ao Cloudinary para user %s: %s", user_id, url_nuvem)
                        return url_nuvem
            except Exception as exc:
                logger.error("Erro ao enviar imagem ao Cloudinary para user %s: %s. Usando fallback local.", user_id, exc)

        # 6. Fallback Local: Gerar nome de arquivo seguro e salvar no disco local
        nome_unico = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.webp"
        caminho_final = os.path.join(self.pasta_destino, nome_unico)

        try:
            if img_quadrada.mode != "RGB":
                img_quadrada = img_quadrada.convert("RGB")
            
            img_quadrada.save(caminho_final, format="WEBP", quality=85, optimize=True)
        except Exception as exc:
            logger.error("Erro ao converter/salvar imagem localmente para user %s: %s", user_id, exc)
            raise UploadError("Erro ao processar imagem no servidor")

        # 7. Apagar a foto antiga do disco se existir
        if foto_antiga_url:
            self.remover_foto(foto_antiga_url)

        url_relativa = f"/static/uploads/avatars/{nome_unico}"
        return url_relativa

    def remover_foto(self, foto_url: str) -> bool:
        """Apaga o arquivo físico da foto de perfil do disco."""
        if not foto_url or not foto_url.startswith("/static/uploads/avatars/"):
            return False

        nome_arquivo = os.path.basename(foto_url)
        caminho_arquivo = os.path.join(self.pasta_destino, nome_arquivo)

        if os.path.exists(caminho_arquivo):
            try:
                os.remove(caminho_arquivo)
                return True
            except Exception as e:
                logger.warning("Não foi possível apagar foto antiga %s: %s", caminho_arquivo, e)
                return False
        return False
