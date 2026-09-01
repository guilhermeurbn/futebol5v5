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

    def _enviar_para_cloudinary(self, img: Image.Image, folder: str, public_id: str, quality: int = 90) -> Optional[str]:
        """Envia uma imagem PIL para o Cloudinary se houver credenciais configuradas."""
        cloud_name = (os.getenv("CLOUDINARY_CLOUD_NAME") or "").strip("\"' ")
        api_key = (os.getenv("CLOUDINARY_API_KEY") or "").strip("\"' ")
        api_secret = (os.getenv("CLOUDINARY_API_SECRET") or "").strip("\"' ")
        cloudinary_url = (os.getenv("CLOUDINARY_URL") or "").strip()

        if "=" in cloudinary_url and "cloudinary://" in cloudinary_url:
            cloudinary_url = cloudinary_url.split("=", 1)[-1]
        cloudinary_url = cloudinary_url.strip("\"' ")

        if not (cloudinary_url or (cloud_name and api_key and api_secret)):
            return None

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

                if img.mode != "RGB":
                    img = img.convert("RGB")

                buffer = io.BytesIO()
                img.save(buffer, format="WEBP", quality=quality, optimize=True)
                buffer.seek(0)

                res = cloudinary.uploader.upload(
                    buffer,
                    folder=folder,
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image",
                    timeout=12
                )
                url_nuvem = res.get("secure_url") or res.get("url")
                if url_nuvem:
                    logger.info("Imagem enviada com sucesso ao Cloudinary (%s/%s): %s", folder, public_id, url_nuvem)
                    return url_nuvem
        except Exception as exc:
            logger.error("Erro ao enviar imagem ao Cloudinary (%s/%s): %s. Usando fallback local.", folder, public_id, exc)

        return None

    def processar_foto_perfil(self, file_storage, user_id: str, foto_antiga_url: Optional[str] = None) -> str:
        """Recebe o FileStorage do Flask, valida a segurança e salva a imagem otimizada no Cloudinary (ou local)."""
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

        # 2. Validação profunda de segurança com Pillow
        try:
            img = Image.open(file_storage.stream)
            img.verify()
        except Exception as e:
            logger.warning("Falha de segurança ao verificar cabeçalho da imagem para user %s: %s", user_id, e)
            raise UploadError("O arquivo enviado não é uma imagem válida ou está corrompido")

        file_storage.seek(0)
        img = Image.open(file_storage.stream)

        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        img_quadrada = ImageOps.fit(
            img,
            (LARGURA_AVATAR_PX, ALTURA_AVATAR_PX),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        # Tentar upload Cloudinary primeiro
        nome_publico = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}"
        url_nuvem = self._enviar_para_cloudinary(img_quadrada, "futebol5v5/avatars", nome_publico, quality=85)
        if url_nuvem:
            if foto_antiga_url:
                self.remover_foto(foto_antiga_url)
            return url_nuvem

        # Fallback Local
        nome_unico = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.webp"
        caminho_final = os.path.join(self.pasta_destino, nome_unico)

        try:
            if img_quadrada.mode != "RGB":
                img_quadrada = img_quadrada.convert("RGB")
            img_quadrada.save(caminho_final, format="WEBP", quality=85, optimize=True)
        except Exception as exc:
            logger.error("Erro ao converter/salvar imagem localmente para user %s: %s", user_id, exc)
            raise UploadError("Erro ao processar imagem no servidor")

        if foto_antiga_url:
            self.remover_foto(foto_antiga_url)

        return f"/static/uploads/avatars/{nome_unico}"

    def remover_foto(self, foto_url: str) -> bool:
        """Apaga o arquivo físico da foto de perfil do disco se for local."""
        if not foto_url or not isinstance(foto_url, str) or not foto_url.startswith("/static/uploads/avatars/"):
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

    def processar_foto_campeao(self, file_storage=None, base64_data: Optional[str] = None, sorteio_id: Optional[str] = None, foto_antiga_url: Optional[str] = None) -> str:
        """Processa e salva a foto/card do time campeão diretamente no Cloudinary (com fallback local)."""
        pasta_cards = os.path.abspath(os.path.join("static", "uploads", "cards"))
        os.makedirs(pasta_cards, exist_ok=True)

        import base64
        import io
        img = None

        if base64_data and isinstance(base64_data, str) and "data:image" in base64_data:
            try:
                header, encoded = base64_data.split(",", 1)
                data_bytes = base64.b64decode(encoded)
                img = Image.open(io.BytesIO(data_bytes))
            except Exception as exc:
                logger.error("Erro ao decodificar base64 do card campeão: %s", exc)
                raise UploadError("Formato de imagem do card enviado é inválido")
        elif file_storage and hasattr(file_storage, "filename") and file_storage.filename:
            try:
                file_storage.seek(0)
                img = Image.open(file_storage.stream)
            except Exception as exc:
                logger.error("Erro ao abrir arquivo enviado para foto campeão: %s", exc)
                raise UploadError("Arquivo de imagem enviado é inválido")
        else:
            raise UploadError("Nenhuma foto ou card do time campeão foi enviado")

        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.mode != "RGB":
            img = img.convert("RGB")

        # Redimensionar se for maior que 1200px de largura para otimizar velocidade de upload
        if img.width > 1200:
            ratio = 1200.0 / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((1200, new_height), Image.Resampling.LANCZOS)

        # Tentar upload Cloudinary primeiro
        s_tag = str(sorteio_id) if sorteio_id else uuid.uuid4().hex[:6]
        nome_publico = f"campeao_{s_tag}_{uuid.uuid4().hex[:6]}"
        url_nuvem = self._enviar_para_cloudinary(img, "futebol5v5/cards", nome_publico, quality=95)
        if url_nuvem:
            if foto_antiga_url:
                self.remover_card_campeao(foto_antiga_url)
            return url_nuvem

        # Fallback local
        nome_unico = f"campeao_{s_tag}_{uuid.uuid4().hex[:6]}.webp"
        caminho_final = os.path.join(pasta_cards, nome_unico)
        img.save(caminho_final, format="WEBP", quality=95, optimize=True)

        if foto_antiga_url:
            self.remover_card_campeao(foto_antiga_url)

        return f"/static/uploads/cards/{nome_unico}"

    def remover_card_campeao(self, card_url: Optional[str]) -> bool:
        """Apaga o arquivo físico do card do campeão do disco se for local."""
        if not card_url or not isinstance(card_url, str) or not card_url.startswith("/static/uploads/cards/"):
            return False

        pasta_cards = os.path.abspath(os.path.join("static", "uploads", "cards"))
        nome_arquivo = os.path.basename(card_url)
        caminho_arquivo = os.path.join(pasta_cards, nome_arquivo)

        if os.path.exists(caminho_arquivo):
            try:
                os.remove(caminho_arquivo)
                logger.info("Card campeão local antigo removido do disco: %s", caminho_arquivo)
                return True
            except Exception as e:
                logger.warning("Não foi possível apagar card campeão antigo %s: %s", caminho_arquivo, e)
                return False
        return False
