"""
Rotas dedicadas para integração segura com o Cloudinary (Upload Direto Assinado & Registro de Asset Metadados).
"""
import logging
import uuid
from flask import Blueprint, request, jsonify, session
from services.upload_service import UploadService, UploadError
from services.db import salvar_image_asset, clear_db_cache
from services.auth_service import AuthService
from services.jogador_service import JogadorService
from services.partida_service import PartidaService

logger = logging.getLogger(__name__)

cloudinary_bp = Blueprint('cloudinary', __name__)
upload_service = UploadService()
auth_service = AuthService()
jogador_service = JogadorService()
partida_service = PartidaService()


@cloudinary_bp.route('/api/cloudinary/sign-upload', methods=['POST'])
def sign_upload():
    """
    Gera a assinatura HMAC-SHA1 para upload direto do frontend ao Cloudinary.
    Segurança: O API Secret NUNCA sai do servidor.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401

    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    tipo = (payload.get('tipo') or 'avatar').strip().lower()
    entity_id = str(payload.get('entity_id') or user_id).strip()

    if tipo == 'avatar':
        folder = "futebol5v5/avatars"
        public_id = f"avatar_{entity_id}_{uuid.uuid4().hex[:6]}"
    elif tipo == 'card':
        folder = "futebol5v5/cards"
        public_id = f"campeao_{entity_id}_{uuid.uuid4().hex[:6]}"
    else:
        folder = f"futebol5v5/{tipo}"
        public_id = f"{tipo}_{entity_id}_{uuid.uuid4().hex[:6]}"

    try:
        sign_data = upload_service.gerar_assinatura_upload(folder=folder, public_id=public_id)
        return jsonify({'sucesso': True, 'data': sign_data})
    except UploadError as exc:
        logger.info("Cloudinary não configurado localmente (modo dev local): %s", exc)
        return jsonify({'sucesso': False, 'erro': str(exc)}), 400
    except Exception as exc:
        logger.error("Erro inesperado ao assinar upload Cloudinary: %s", exc)
        return jsonify({'sucesso': False, 'erro': 'Erro ao preparar upload seguro'}), 500


@cloudinary_bp.route('/api/cloudinary/register-asset', methods=['POST'])
def register_asset():
    """
    Registra os metadados da imagem enviados pelo frontend apos o upload direto no Cloudinary.
    Atualiza PostgreSQL (app_json_store) e os vinculos do usuario/jogador/partida.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401

    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({'sucesso': False, 'erro': 'Payload inválido'}), 400

    public_id = payload.get('public_id')
    secure_url = payload.get('secure_url') or payload.get('url')

    if not public_id or not secure_url:
        return jsonify({'sucesso': False, 'erro': 'Metadados de imagem incompletos'}), 400

    entity_type = payload.get('entity_type', 'avatar')
    entity_id = str(payload.get('entity_id') or user_id)

    # 1. Salvar no namespace image_assets no PostgreSQL
    asset_record = salvar_image_asset({
        "asset_id": payload.get('asset_id') or f"asset_{uuid.uuid4().hex[:8]}",
        "public_id": public_id,
        "resource_type": payload.get('resource_type', 'image'),
        "format": payload.get('format', 'jpg'),
        "width": payload.get('width', 0),
        "height": payload.get('height', 0),
        "bytes": payload.get('bytes', 0),
        "secure_url": secure_url,
        "url": secure_url,
        "entity_type": entity_type,
        "entity_id": entity_id,
    })

    # 2. Vincular a entidade correspondente (Perfil do Usuario / Jogador / Partida)
    if entity_type == 'avatar':
        # Atualizar no Auth (usuario)
        try:
            auth_service.atualizar_perfil_usuario(user_id=user_id, foto_url=secure_url)
        except Exception as e:
            logger.warning("Não foi possível atualizar avatar no auth_service: %s", e)

        # Atualizar no Jogador associado
        try:
            jog_list = jogador_service.listar_todos()
            for jog in jog_list:
                if str(jog.get('user_id')) == str(user_id) or str(jog.get('id')) == str(entity_id):
                    jogador_service.atualizar(jog.get('id'), foto_url=secure_url)
        except Exception as e:
            logger.warning("Não foi possível atualizar avatar no jogador_service: %s", e)

    elif entity_type == 'card':
        sorteio_id = int(entity_id) if entity_id.isdigit() else entity_id
        try:
            partidas = partida_service.obter_partidas_sorteio(sorteio_id)
            if partidas:
                partida_obj = partidas[0]
                partida_service.registrar_resultado(
                    sorteio_id=sorteio_id,
                    time_vencedor=partida_obj.get('time_vencedor'),
                    gols_times=partida_obj.get('gols_times', []),
                    notas=partida_obj.get('notas', ''),
                    times_desempenho=partida_obj.get('times_desempenho', []),
                    card_campeao_url=secure_url
                )
        except Exception as e:
            logger.warning("Não foi possível salvar card_campeao_url na partida: %s", e)

    clear_db_cache()
    return jsonify({
        'sucesso': True,
        'mensagem': 'Imagem registrada com sucesso',
        'url': secure_url,
        'asset': asset_record
    })


@cloudinary_bp.route('/api/cloudinary/upload-local', methods=['POST'])
def upload_local():
    """
    Fallback local em dev (localhost): Salva imagem em static/uploads/ quando
    o Cloudinary não possui credenciais configuradas no ambiente local.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401

    payload = request.get_json(silent=True) or {}
    file_obj = request.files.get('file')
    tipo = (payload.get('tipo') or request.form.get('tipo') or 'avatar').strip().lower()
    entity_id = str(payload.get('entity_id') or request.form.get('entity_id') or user_id).strip()

    try:
        if tipo == 'card':
            url_local = upload_service.processar_foto_campeao(file_storage=file_obj, base64_data=payload.get('base64'), sorteio_id=entity_id)
        else:
            if file_obj:
                url_local = upload_service.processar_foto_perfil(file_obj, user_id=user_id)
            elif payload.get('base64'):
                url_local = upload_service.processar_foto_campeao(base64_data=payload.get('base64'), sorteio_id=entity_id)
            else:
                return jsonify({'sucesso': False, 'erro': 'Nenhuma imagem fornecida'}), 400

        # Registrar vinculação no banco
        salvar_image_asset({
            "asset_id": f"local_{uuid.uuid4().hex[:8]}",
            "public_id": f"local_{tipo}_{entity_id}",
            "secure_url": url_local,
            "entity_type": tipo,
            "entity_id": entity_id
        })

        # Executar logica de vinculo
        if tipo == 'avatar':
            try:
                auth_service.atualizar_perfil_usuario(user_id=user_id, foto_url=url_local)
            except Exception as e:
                logger.warning("Não foi possível atualizar avatar no auth_service: %s", e)
            try:
                jog_list = jogador_service.listar_todos()
                for jog in jog_list:
                    if str(jog.get('user_id')) == str(user_id) or str(jog.get('id')) == str(entity_id):
                        jogador_service.atualizar(jog.get('id'), foto_url=url_local)
            except Exception as e:
                logger.warning("Não foi possível atualizar avatar no jogador_service: %s", e)
        elif tipo == 'card':
            sorteio_id = int(entity_id) if entity_id.isdigit() else entity_id
            partidas = partida_service.obter_partidas_sorteio(sorteio_id)
            if partidas:
                partida_obj = partidas[0]
                partida_service.registrar_resultado(
                    sorteio_id=sorteio_id,
                    time_vencedor=partida_obj.get('time_vencedor'),
                    gols_times=partida_obj.get('gols_times', []),
                    notas=partida_obj.get('notas', ''),
                    times_desempenho=partida_obj.get('times_desempenho', []),
                    card_campeao_url=url_local
                )

        clear_db_cache()
        return jsonify({'sucesso': True, 'url': url_local, 'mensagem': 'Foto salva localmente em modo fallback'})
    except Exception as exc:
        logger.error("Erro no fallback local de upload: %s", exc)
        return jsonify({'sucesso': False, 'erro': str(exc)}), 500
