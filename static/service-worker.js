// NaTrave Service Worker - Offline Support & Caching Strategy
const CACHE_NAME = 'natrave-v2';
const RUNTIME_CACHE = 'natrave-runtime-v2';
const IMAGE_CACHE = 'natrave-images-v2';

// URLs que devem estar sempre em cache
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/offline-judge.js',
  '/sortear',
  '/historico',
  '/favoritos',
  '/campeonato',
  '/charts'
];

// Instalação do Service Worker
self.addEventListener('install', event => {
  console.log('[Service Worker] Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[Service Worker] Caching URLs essenciais');
      return cache.addAll(urlsToCache).catch(err => {
        console.warn('[Service Worker] Alguns URLs falharam ao caching:', err);
        // Continuar mesmo se alguns falhem
      });
    })
  );
  self.skipWaiting();
});

// Ativação do Service Worker
self.addEventListener('activate', event => {
  console.log('[Service Worker] Ativando...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE && cacheName !== IMAGE_CACHE) {
            console.log('[Service Worker] Deletando cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Estratégia de fetch - Network First para APIs, Cache First para assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Ignorar requisições não-GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Estratégia para APIs (JSON responses)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache responses de sucesso
          if (response.status === 200) {
            const responseToCache = response.clone();
            caches.open(RUNTIME_CACHE).then(cache => {
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        })
        .catch(() => {
          // Retornar cached response se offline
          return caches.match(event.request).then(response => {
            if (response) {
              console.log('[Service Worker] Retornando cache para API:', url.pathname);
              return response;
            }
            // Retornar resposta vazia ou fallback
            return new Response(
              JSON.stringify({ erro: 'Offline - dados não disponíveis', offline: true }),
              { headers: { 'Content-Type': 'application/json' } }
            );
          });
        })
    );
    return;
  }

  // Estratégia para HTML pages
  if (url.pathname.endsWith('.html') || !url.pathname.includes('.')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then(response => {
            if (response) {
              return response;
            }
            // Página offline fallback
            return new Response(
              `<!DOCTYPE html>
              <html>
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>NaTrave - Offline</title>
                <style>
                  body { font-family: Arial; background: #0a0e27; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                  .container { text-align: center; }
                  h1 { color: #667eea; margin-bottom: 1rem; }
                  p { font-size: 18px; margin-bottom: 2rem; }
                  .emoji { font-size: 80px; margin-bottom: 1rem; }
                </style>
              </head>
              <body>
                <div class="container">
                  <div class="emoji">📡</div>
                  <h1>Sem Conexão</h1>
                  <p>Você está offline. Acesse uma página já carregada ou conecte à internet.</p>
                  <p><a href="/" style="color: #667eea; text-decoration: none;">← Voltar ao início</a></p>
                </div>
              </body>
              </html>`,
              { headers: { 'Content-Type': 'text/html' }, status: 503 }
            );
          });
        })
    );
    return;
  }

  // Estratégia para CSS e JavaScript
  if (url.pathname.endsWith('.css') || url.pathname.endsWith('.js')) {
    event.respondWith(
      caches.match(event.request).then(response => {
        if (response) {
          // Atualizar cache em background
          fetch(event.request).then(newResponse => {
            if (newResponse.status === 200) {
              caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, newResponse);
              });
            }
          }).catch(() => {});
          return response;
        }
        
        // Não está em cache, fazer requisição
        return fetch(event.request).then(response => {
          if (response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseToCache);
            });
          }
          return response;
        }).catch(() => {
          // Se falhar e não tiver cache, retornar placeholder
          if (url.pathname.endsWith('.css')) {
            return new Response('', { headers: { 'Content-Type': 'text/css' } });
          }
          return new Response('', { headers: { 'Content-Type': 'application/javascript' } });
        });
      })
    );
    return;
  }

  // Estratégia para imagens (Cache First, Stale While Revalidate)
  if (url.pathname.match(/\.(png|jpg|jpeg|svg|gif|webp)$/i)) {
    event.respondWith(
      caches.open(IMAGE_CACHE).then(cache => {
        return cache.match(event.request).then(response => {
          // Retornar cached image se disponível
          if (response) {
            // Atualizar cache em background
            fetch(event.request).then(newResponse => {
              if (newResponse.status === 200) {
                cache.put(event.request, newResponse);
              }
            }).catch(() => {});
            return response;
          }
          
          // Buscar da rede
          return fetch(event.request).then(response => {
            if (response.status === 200) {
              const responseToCache = response.clone();
              cache.put(event.request, responseToCache);
            }
            return response;
          }).catch(() => {
            // Retornar placeholder image
            return new Response(
              `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
              <rect fill="#667eea" width="100" height="100"/>
              <text x="50" y="50" text-anchor="middle" dy="0.3em" fill="white" font-size="20">⚽</text>
              </svg>`,
              { headers: { 'Content-Type': 'image/svg+xml' } }
            );
          });
        });
      })
    );
    return;
  }

  // Fallback - Network First
  event.respondWith(
    fetch(event.request)
      .then(response => {
        if (response.status === 200) {
          const responseToCache = response.clone();
          caches.open(RUNTIME_CACHE).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).catch(() => {
          return new Response('Recurso não disponível', { status: 503 });
        });
      })
  );
});

// Background Sync (experimental)
self.addEventListener('sync', event => {
  if (event.tag === 'sync-favoritos') {
    event.waitUntil(
      fetch('/api/favoritos', { method: 'GET' })
        .then(() => console.log('[Service Worker] Sync favoritos completo'))
        .catch(err => console.error('[Service Worker] Sync favoritos falhou:', err))
    );
  }
});

// Message Handler - Para comunicação com cliente
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.delete(RUNTIME_CACHE).then(() => {
      console.log('[Service Worker] Cache de runtime limpo');
    });
  }
});
