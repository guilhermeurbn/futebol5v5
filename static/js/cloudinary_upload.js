/**
 * NaTrave — Módulo de Upload Direto Assinado para o Cloudinary com Fila de Retry Offline.
 */

(function(window) {
    'use strict';

    const QUEUE_STORAGE_KEY = 'natrave_pending_uploads_v1';
    const RETRY_DELAYS_MS = [2000, 5000, 15000, 30000];

    class NaTraveCloudinaryUploader {
        constructor() {
            this.isProcessingQueue = false;
            this.initListeners();
        }

        initListeners() {
            window.addEventListener('online', () => {
                console.log('[CloudinaryUpload] Conexão restabelecida. Processando fila pendente...');
                this.processPendingQueue();
            });
        }

        /**
         * Realiza o upload direto de um Blob/Canvas ao Cloudinary usando assinatura HMAC-SHA1 gerada pelo Flask.
         */
        async uploadBlobDirect(blob, options = {}) {
            const {
                tipo = 'avatar',
                entityId = '',
                onStatusChange = () => {},
                csrfToken = ''
            } = options;

            onStatusChange('SOLICITANDO_ASSINATURA', 'Gerando autorização segura...');

            // 1. Solicitar Assinatura Assinada ao Backend Flask
            let signData;
            try {
                const response = await fetch('/api/cloudinary/sign-upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ tipo, entity_id: entityId })
                });

                const resJson = await response.json();
                if (!response.ok || !resJson.sucesso) {
                    // Fallback para upload local se as credenciais do Cloudinary não estiverem no .env (Dev Localhost)
                    if (resJson.erro && resJson.erro.includes('não configuradas')) {
                        console.warn('[CloudinaryUpload] Credenciais não configuradas. Usando salvamento local fallback...');
                        onStatusChange('SALVANDO_LOCAL', 'Salvando imagem localmente (Modo Desenvolvimento)...');
                        const base64Str = await this.blobToBase64(blob);
                        const localRes = await fetch('/api/cloudinary/upload-local', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrfToken
                            },
                            body: JSON.stringify({
                                tipo,
                                entity_id: entityId,
                                base64: base64Str
                            })
                        });
                        const localJson = await localRes.json();
                        if (localRes.ok && localJson.sucesso) {
                            onStatusChange('SUCESSO', 'Salvo localmente!');
                            return localJson;
                        }
                        throw new Error(localJson.erro || 'Falha no salvamento local');
                    }
                    throw new Error(resJson.erro || 'Falha ao obter autorização de upload');
                }
                signData = resJson.data;
            } catch (err) {
                console.warn('[CloudinaryUpload] Falha ao obter assinatura:', err);
                onStatusChange('ERRO', err.message || 'Erro ao conectar ao servidor');
                throw err;
            }

            // 2. Upload Direto para a API do Cloudinary (POST Multipart Direct)
            onStatusChange('ENVIANDO_CLOUDINARY', 'Enviando imagem diretamente ao Cloudinary...');

            const formData = new FormData();
            formData.append('file', blob, `${tipo}_${entityId}.jpg`);
            formData.append('api_key', signData.api_key);
            formData.append('timestamp', signData.timestamp);
            formData.append('signature', signData.signature);
            formData.append('folder', signData.folder);
            formData.append('public_id', signData.public_id);

            let cloudinaryRes;
            try {
                const cResponse = await fetch(signData.upload_url, {
                    method: 'POST',
                    body: formData
                });

                cloudinaryRes = await cResponse.json();
                if (!cResponse.ok || cloudinaryRes.error) {
                    const cErrMsg = (cloudinaryRes.error && cloudinaryRes.error.message) || 'Erro no upload Cloudinary';
                    throw new Error(cErrMsg);
                }
            } catch (err) {
                console.warn('[CloudinaryUpload] Falha no upload direto ao Cloudinary:', err);
                
                // Salvar na fila de retentativa offline se for erro de rede
                if (!navigator.onLine || err.message.includes('fetch') || err.message.includes('network')) {
                    this.enqueuePendingUpload({
                        tipo,
                        entityId,
                        blobBase64: await this.blobToBase64(blob),
                        signData,
                        attemptCount: 0
                    });
                    onStatusChange('PENDENTE_RETRY', 'Conexão oscilou. Upload agendado para retentativa automática...');
                } else {
                    onStatusChange('ERRO', err.message);
                }
                throw err;
            }

            // 3. Registrar Metadados no PostgreSQL via Flask
            onStatusChange('REGISTRANDO_METADADOS', 'Registrando imagem no banco de dados...');
            let registerRes;
            try {
                const regResponse = await fetch('/api/cloudinary/register-asset', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        asset_id: cloudinaryRes.asset_id,
                        public_id: cloudinaryRes.public_id,
                        secure_url: cloudinaryRes.secure_url || cloudinaryRes.url,
                        resource_type: cloudinaryRes.resource_type || 'image',
                        format: cloudinaryRes.format || 'jpg',
                        width: cloudinaryRes.width || 0,
                        height: cloudinaryRes.height || 0,
                        bytes: cloudinaryRes.bytes || 0,
                        entity_type: tipo,
                        entity_id: entityId
                    })
                });

                registerRes = await regResponse.json();
                if (!regResponse.ok || !registerRes.sucesso) {
                    throw new Error(registerRes.erro || 'Erro ao registrar metadados');
                }
            } catch (err) {
                console.warn('[CloudinaryUpload] Falha ao registrar metadados:', err);
                onStatusChange('ERRO', err.message);
                throw err;
            }

            onStatusChange('SUCESSO', 'Upload e registro concluídos!');
            return registerRes;
        }

        /**
         * Converte Canvas HTML5 diretamente em Blob e realiza o upload assinado.
         */
        uploadCanvasDirect(canvas, options = {}) {
            const quality = options.quality || 0.82;
            return new Promise((resolve, reject) => {
                canvas.toBlob(async (blob) => {
                    if (!blob) {
                        return reject(new Error('Falha ao extrair imagem do Canvas'));
                    }
                    try {
                        const result = await this.uploadBlobDirect(blob, options);
                        resolve(result);
                    } catch (err) {
                        reject(err);
                    }
                }, 'image/jpeg', quality);
            });
        }

        blobToBase64(blob) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }

        getPendingQueue() {
            try {
                const raw = localStorage.getItem(QUEUE_STORAGE_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        }

        savePendingQueue(queue) {
            try {
                localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue));
            } catch (e) {
                console.warn('Erro ao salvar fila pendente:', e);
            }
        }

        enqueuePendingUpload(item) {
            const queue = this.getPendingQueue();
            item.id = item.id || `pending_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
            item.createdAt = item.createdAt || Date.now();
            queue.push(item);
            this.savePendingQueue(queue);
            this.scheduleRetry();
        }

        scheduleRetry() {
            if (this.isProcessingQueue) return;
            const queue = this.getPendingQueue();
            if (queue.length === 0) return;

            const nextItem = queue[0];
            const attempts = nextItem.attemptCount || 0;
            const delay = RETRY_DELAYS_MS[Math.min(attempts, RETRY_DELAYS_MS.length - 1)];

            console.log(`[CloudinaryUpload] Retentativa agendada para daqui a ${delay / 1000}s (Tentativa ${attempts + 1})...`);
            setTimeout(() => {
                this.processPendingQueue();
            }, delay);
        }

        async processPendingQueue() {
            if (this.isProcessingQueue || !navigator.onLine) return;
            this.isProcessingQueue = true;

            const queue = this.getPendingQueue();
            if (queue.length === 0) {
                this.isProcessingQueue = false;
                return;
            }

            const item = queue[0];
            item.attemptCount = (item.attemptCount || 0) + 1;

            try {
                console.log(`[CloudinaryUpload] Retentando upload pendente (${item.id})...`);
                const response = await fetch(item.signData.upload_url, {
                    method: 'POST',
                    body: item.formData
                });
                if (response.ok) {
                    queue.shift(); // Remove item processado
                    this.savePendingQueue(queue);
                    console.log(`[CloudinaryUpload] Upload pendente ${item.id} concluído com sucesso!`);
                } else if (item.attemptCount >= 5) {
                    queue.shift(); // Descartar apos 5 tentativas sem sucesso
                    this.savePendingQueue(queue);
                } else {
                    this.savePendingQueue(queue);
                }
            } catch (e) {
                console.warn('[CloudinaryUpload] Falha ao re-enviar item da fila:', e);
            } finally {
                this.isProcessingQueue = false;
                if (this.getPendingQueue().length > 0) {
                    this.scheduleRetry();
                }
            }
        }
    }

    window.NaTraveCloudinaryUploader = new NaTraveCloudinaryUploader();
})(window);
