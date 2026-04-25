(function () {
  const QUEUE_KEY = 'natrave_offline_queue_v1';
  const SELECTION_DRAFT_KEY = 'natrave_offline_selection_v1';

  function readJSON(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (error) {
      return fallback;
    }
  }

  function writeJSON(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function isOffline() {
    return typeof navigator !== 'undefined' && navigator.onLine === false;
  }

  function getQueue() {
    return readJSON(QUEUE_KEY, []);
  }

  function saveQueue(queue) {
    writeJSON(QUEUE_KEY, queue);
  }

  function enqueueRequest(entry) {
    const queue = getQueue();
    queue.push({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      created_at: new Date().toISOString(),
      ...entry
    });
    saveQueue(queue);
    return queue[queue.length - 1];
  }

  async function syncQueue() {
    if (isOffline()) {
      return { synced: 0, pending: getQueue().length };
    }

    const queue = getQueue();
    if (!queue.length) {
      return { synced: 0, pending: 0 };
    }

    const restante = [];
    let synced = 0;

    for (const item of queue) {
      try {
        const response = await fetch(item.url, {
          method: item.method || 'POST',
          headers: item.headers || {},
          body: item.body
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        synced += 1;
      } catch (error) {
        restante.push(item);
      }
    }

    saveQueue(restante);
    return { synced, pending: restante.length };
  }

  function salvarSelecaoOffline(payload) {
    writeJSON(SELECTION_DRAFT_KEY, {
      ...payload,
      saved_at: new Date().toISOString()
    });
  }

  function obterSelecaoOffline() {
    return readJSON(SELECTION_DRAFT_KEY, null);
  }

  function limparSelecaoOffline() {
    localStorage.removeItem(SELECTION_DRAFT_KEY);
  }

  function gerarTimesLocalmente(jogadores, numeroTimes) {
    const times = Array.from({ length: Math.max(1, numeroTimes) }, (_, index) => ({
      numero: index + 1,
      jogadores: [],
      soma: 0
    }));

    const goleiros = [...jogadores].filter(jogador => (jogador.posicao || '').toLowerCase() === 'goleiro');
    const outros = [...jogadores].filter(jogador => (jogador.posicao || '').toLowerCase() !== 'goleiro');

    goleiros.forEach((jogador, index) => {
      const alvo = times[index % times.length];
      const nivel = Number(jogador.nivel) || 0;
      alvo.jogadores.push(jogador);
      alvo.soma += nivel;
    });

    const ordenados = outros.sort((a, b) => (Number(b.nivel) || 0) - (Number(a.nivel) || 0));

    ordenados.forEach(jogador => {
      times.sort((a, b) => a.soma - b.soma);
      const alvo = times[0];
      const nivel = Number(jogador.nivel) || 0;
      alvo.jogadores.push(jogador);
      alvo.soma += nivel;
    });

    const somas = times.map(time => time.soma);
    const maior = somas.length ? Math.max(...somas) : 0;
    const menor = somas.length ? Math.min(...somas) : 0;

    return {
      times,
      somas,
      diferenca: maior - menor
    };
  }

  function montarHtmlPreview(preview) {
    if (!preview || !preview.times || !preview.times.length) {
      return '<div class="alert alert-warning">Nenhum sorteio local disponível.</div>';
    }

    let html = '<div class="stats-grid" style="margin-bottom: 1rem;">';
    html += `<div class="stat-card"><div class="stat-label">Times</div><div class="stat-value">${preview.times.length}</div></div>`;
    html += `<div class="stat-card"><div class="stat-label">Diferença</div><div class="stat-value">${preview.diferenca}</div></div>`;
    html += '</div>';
    html += '<div class="times-container" style="display:grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));">';

    preview.times.forEach(time => {
      html += `<div class="team"><div class="team-header"><h3 class="team-title">Time ${time.numero}</h3><span class="team-score">${time.soma}</span></div><div class="players-list">`;
      time.jogadores.forEach(jogador => {
        html += `<div class="player-item"><span class="player-name">${jogador.nome}</span><span class="player-level">N${jogador.nivel || 0}</span></div>`;
      });
      html += '</div></div>';
    });

    html += '</div>';
    return html;
  }

  function renderizarPreview(containerId, preview, mensagem) {
    const container = document.getElementById(containerId);
    if (!container) {
      return;
    }

    container.style.display = 'block';
    container.innerHTML = `
      <section class="section" style="margin-top: 1rem;">
        <h2 class="section-title">📴 Modo Offline</h2>
        <p style="margin-bottom: 1rem; opacity: 0.9;">${mensagem || 'O sorteio foi montado localmente. Ele será sincronizado quando a conexão voltar.'}</p>
        ${montarHtmlPreview(preview)}
      </section>
    `;
  }

  function estadoFila() {
    const queue = getQueue();
    return {
      total: queue.length,
      pendentes: queue.length
    };
  }

  async function queueFormSubmission(config) {
    if (!config || !config.url) {
      throw new Error('Configuração inválida para fila offline');
    }

    enqueueRequest({
      label: config.label || 'Requisição offline',
      url: config.url,
      method: config.method || 'POST',
      headers: config.headers || {},
      body: config.body || null,
      kind: config.kind || 'generic'
    });

    return estadoFila();
  }

  function initAutoSync() {
    if (typeof window === 'undefined') {
      return;
    }

    window.addEventListener('online', () => {
      syncQueue().then(result => {
        console.log('[NaTrave Offline] Sincronização concluída:', result);
      }).catch(error => {
        console.warn('[NaTrave Offline] Falha na sincronização:', error);
      });
    });

    if (!isOffline()) {
      syncQueue().catch(() => {});
    }
  }

  initAutoSync();

  window.NaTraveOffline = {
    isOffline,
    enqueueRequest,
    syncQueue,
    queueFormSubmission,
    salvarSelecaoOffline,
    obterSelecaoOffline,
    limparSelecaoOffline,
    gerarTimesLocalmente,
    renderizarPreview,
    estadoFila
  };
})();