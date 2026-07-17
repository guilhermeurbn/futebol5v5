(function () {
  if (!document.body || document.body.dataset.appShell === '0') {
    return;
  }

  const CONTENT_SELECTOR = '[data-app-content]';
  const LOADER_ID = 'app-shell-loader';
  const prefetched = new Set();
  let navigationToken = 0;
  const CACHE_PREFIX = 'natrave:app-shell:';

  function getContent(root) {
    return (root || document).querySelector(CONTENT_SELECTOR);
  }

  function normalizeUrl(value) {
    const url = new URL(value, window.location.href);
    url.hash = '';
    return url;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function readCachedJSON(key) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      return null;
    }
  }

  function writeCachedJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      // ignore storage quota or privacy mode issues
    }
  }

  function isExternalLink(link, url) {
    return link.hasAttribute('download') || (link.target && link.target !== '_self') || url.origin !== window.location.origin;
  }

  function shouldHandleLink(link, event) {
    if (!link || link.tagName !== 'A') return false;
    if (link.closest('[data-no-soft-nav]')) return false;
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;

    const href = link.getAttribute('href') || '';
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) {
      return false;
    }

    const url = normalizeUrl(href);
    if (isExternalLink(link, url)) return false;
    if (url.pathname === window.location.pathname && url.search === window.location.search) return false;

    return true;
  }

  function ensureLoader() {
    let loader = document.getElementById(LOADER_ID);
    if (loader) return loader;

    loader = document.createElement('div');
    loader.id = LOADER_ID;
    loader.className = 'app-shell-loader';
    loader.hidden = true;
    loader.setAttribute('aria-hidden', 'true');
    loader.innerHTML = `
      <div class="app-shell-loader__panel" role="status" aria-label="Carregando tela">
        <div class="app-shell-loader__title"></div>
        <div class="app-shell-loader__line app-shell-loader__line--wide"></div>
        <div class="app-shell-loader__line app-shell-loader__line--medium"></div>
        <div class="app-shell-loader__line app-shell-loader__line--short"></div>
        <div class="app-shell-loader__cards">
          <div class="app-shell-loader__chip"></div>
          <div class="app-shell-loader__chip"></div>
          <div class="app-shell-loader__chip"></div>
        </div>
      </div>
    `;
    document.body.appendChild(loader);
    return loader;
  }

  function setLoading(isLoading) {
    const loader = ensureLoader();
    loader.hidden = !isLoading;
    document.body.classList.toggle('app-shell-loading', isLoading);
  }

  function rehydrateScripts(container) {
    container.querySelectorAll('script').forEach(script => {
      const replacement = document.createElement('script');

      for (const attribute of script.attributes) {
        replacement.setAttribute(attribute.name, attribute.value);
      }

      if (script.src) {
        replacement.src = script.src;
        replacement.async = false;
      } else {
        replacement.textContent = script.textContent;
      }

      script.replaceWith(replacement);
    });
  }

  function matchesPath(linkPath, currentPath) {
    if (linkPath === '/') return currentPath === '/';
    if (linkPath === '/admin') return currentPath.startsWith('/admin');
    if (linkPath === '/perfil') return currentPath.startsWith('/perfil');
    if (linkPath === '/historico') return currentPath.startsWith('/historico') || currentPath.startsWith('/sorteio');
    if (linkPath === '/votacao') return currentPath.startsWith('/votacao');
    if (linkPath === '/jogar') return currentPath.startsWith('/jogar');
    return currentPath === linkPath || currentPath.startsWith(linkPath + '/');
  }

  function refreshFooterState(url) {
    const currentPath = url.pathname;
    const links = Array.from(document.querySelectorAll('.site-footer__link'));

    // Keep only one active footer item: pick the most specific route match.
    let bestMatch = null;
    let bestScore = -1;

    links.forEach(link => {
      const target = new URL(link.href, window.location.origin);
      const active = matchesPath(target.pathname, currentPath);

      if (active) {
        const score = target.pathname.length;
        if (score > bestScore) {
          bestScore = score;
          bestMatch = link;
        }
      }
    });

    links.forEach(link => {
      const active = link === bestMatch;
      link.classList.toggle('is-active', active);

      if (active) {
        link.setAttribute('aria-current', 'page');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }

  function runPageHooks() {
    if (window.NaTraveCSRF && typeof window.NaTraveCSRF.ensureFormTokens === 'function') {
      window.NaTraveCSRF.ensureFormTokens(document);
    }

    if (window.NaTraveMobileNav && typeof window.NaTraveMobileNav.refresh === 'function') {
      window.NaTraveMobileNav.refresh();
    }

    hydrateRankingPage();
    hydratePlayersPage();
    hydrateJudgePage();
    hydrateAdminPage();
  }

  function formatRankingValue(value) {
    if (value === null || value === undefined || value === '') {
      return '-';
    }
    return String(value);
  }

  function rankingPositionLabel(index) {
    if (index === 0) return '🥇';
    if (index === 1) return '🥈';
    if (index === 2) return '🥉';
    return String(index + 1);
  }

  function renderRankingSkeleton() {
    return `
      <div class="ranking-shell__skeleton" aria-busy="true" aria-live="polite">
        <section class="section ranking-hero">
          <div class="ranking-shell__skeleton-hero">
            <div class="ranking-shell__skeleton-title"></div>
            <div class="ranking-shell__skeleton-subtitle"></div>
          </div>
          <div class="ranking-shell__skeleton-facts">
            <div class="ranking-shell__skeleton-stat"></div>
            <div class="ranking-shell__skeleton-stat"></div>
            <div class="ranking-shell__skeleton-stat"></div>
          </div>
        </section>
        <section class="section">
          <div class="ranking-shell__skeleton-heading"></div>
          <div class="ranking-shell__skeleton-card"></div>
          <div class="ranking-shell__skeleton-card"></div>
          <div class="ranking-shell__skeleton-card"></div>
          <div class="ranking-shell__skeleton-table" style="margin-top: 1rem;"></div>
        </section>
      </div>
    `;
  }

  function renderPlayersSkeleton() {
    return `
      <div class="players-shell__overlay" aria-busy="true" aria-live="polite">
        <div class="players-shell__overlay-hero"></div>
        <div class="players-shell__overlay-panel"></div>
        <div class="players-shell__overlay-grid">
          <div class="players-shell__overlay-card"></div>
          <div class="players-shell__overlay-card"></div>
          <div class="players-shell__overlay-card"></div>
        </div>
      </div>
    `;
  }

  function renderSimpleOverlay(label, detailsCount = 2) {
    const cards = Array.from({ length: detailsCount }, () => '<div class="admin-shell__overlay-card"></div>').join('');
    return `
      <div class="${label}-shell__overlay" aria-busy="true" aria-live="polite">
        <div class="${label}-shell__overlay-strip"></div>
        ${cards}
      </div>
    `;
  }

  function normalizePlayerName(value) {
    return String(value || '').trim().toLowerCase();
  }

  function playerStatsValue(stats, keys, fallback) {
    if (!stats) return fallback;
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(stats, key) && stats[key] !== null && stats[key] !== undefined) {
        return stats[key];
      }
    }
    return fallback;
  }

  function buildPlayerStatsMap(statsPayload) {
    const map = new Map();
    if (!statsPayload || typeof statsPayload !== 'object') {
      return map;
    }

    Object.entries(statsPayload).forEach(([name, stats]) => {
      map.set(normalizePlayerName(name), stats || {});
    });

    return map;
  }

  function updatePlayersDom(jogadores, statsMap) {
    const countEl = document.querySelector('.players-showcase-count');
    if (countEl) {
      countEl.textContent = String(jogadores.length);
      countEl.setAttribute('aria-label', `${jogadores.length} jogadores cadastrados`);
    }

    const cards = Array.from(document.querySelectorAll('.player-card[data-player-id]'));
    cards.forEach(card => {
      const nameEl = card.querySelector('.player-card__name, .player-list-row__name');
      const name = normalizePlayerName(nameEl ? nameEl.textContent : card.dataset.name);
      const stats = statsMap.get(name);
      if (!stats) return;

      const wins = playerStatsValue(stats, ['vitórias', 'vitorias', 'wins'], 0);
      const matches = playerStatsValue(stats, ['total_partidas', 'matches', 'partidas'], 0);

      const statValues = card.querySelectorAll('.premium-player-stat-val, .player-card__stat-value');
      if (statValues[0]) statValues[0].textContent = String(wins);
      if (statValues[1]) statValues[1].textContent = String(matches);

      const mobileMeta = card.querySelector('.player-list-row__meta-item:last-child');
      if (mobileMeta) {
        mobileMeta.childNodes.forEach(node => {
          if (node.nodeType === Node.TEXT_NODE) {
            node.textContent = `${matches} partidas`;
          }
        });
      }
    });
  }

  async function hydratePlayersPage() {
    const shell = document.querySelector('[data-player-shell]');
    if (!shell) {
      return;
    }

    const apiUrl = shell.dataset.playerApi;
    const statsApiUrl = shell.dataset.playerStatsApi;
    const cacheKey = shell.dataset.playerCacheKey || `${CACHE_PREFIX}players`;
    if (!apiUrl) {
      return;
    }

    const cached = readCachedJSON(cacheKey);
    const overlay = document.createElement('div');
    overlay.innerHTML = renderPlayersSkeleton();
    const skeleton = overlay.firstElementChild;
    if (skeleton) {
      shell.classList.add('players-shell--loading');
      shell.style.position = 'relative';
      shell.prepend(skeleton);
    }

    const playersRequest = fetch(apiUrl, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'fetch'
      }
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    });

    const statsRequest = statsApiUrl ? fetch(statsApiUrl, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'fetch'
      }
    }).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    }) : Promise.resolve({});

    if (cached && Array.isArray(cached.players)) {
      updatePlayersDom(cached.players, buildPlayerStatsMap(cached.stats || {}));
      if (skeleton && skeleton.parentNode) {
        skeleton.remove();
      }
      shell.classList.remove('players-shell--loading');
    }

    try {
      const [players, statsPayload] = await Promise.all([playersRequest, statsRequest]);
      const statsMap = buildPlayerStatsMap(statsPayload);
      updatePlayersDom(players, statsMap);

      writeCachedJSON(cacheKey, {
        saved_at: new Date().toISOString(),
        players,
        stats: statsPayload
      });
    } catch (error) {
      // keep server-rendered content intact on failure
    } finally {
      if (skeleton && skeleton.parentNode) {
        skeleton.remove();
      }
      shell.classList.remove('players-shell--loading');
    }
  }

  function updateJudgeDom(data) {
    const totalEl = document.querySelector('[data-judge-total-jogadores]');
    if (totalEl && data && data.total_jogadores !== undefined) {
      totalEl.textContent = `${data.total_jogadores} jogadores disponíveis`;
    }

    const lastMatch = document.querySelector('[data-judge-last-match] .section-subtitle');
    if (lastMatch && data && data.ultima_partida) {
      lastMatch.textContent = data.ultima_partida.titulo || 'Partida encerrada recentemente';
    }
  }

  async function hydrateJudgePage() {
    const shell = document.querySelector('[data-judge-shell]');
    if (!shell) {
      return;
    }

    const apiUrl = shell.dataset.judgeApi;
    const cacheKey = shell.dataset.judgeCacheKey || `${CACHE_PREFIX}judge`;
    if (!apiUrl) {
      return;
    }

    const cached = readCachedJSON(cacheKey);
    if (cached && cached.data) {
      updateJudgeDom(cached.data);
    } else {
      const overlay = document.createElement('div');
      overlay.innerHTML = `
        <div class="judge-shell__overlay" aria-busy="true" aria-live="polite">
          <div class="judge-shell__overlay-strip"></div>
          <div class="judge-shell__overlay-card"></div>
        </div>
      `;
      const node = overlay.firstElementChild;
      if (node) {
        shell.classList.add('judge-shell--loading');
        shell.style.position = 'relative';
        shell.prepend(node);
      }
    }

    try {
      const response = await fetch(apiUrl, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'fetch' }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const payload = await response.json();
      if (!payload || payload.sucesso === false) throw new Error('Falha ao carregar resumo do juiz');

      writeCachedJSON(cacheKey, {
        saved_at: new Date().toISOString(),
        data: payload.dados
      });
      updateJudgeDom(payload.dados);
    } catch (error) {
      // keep SSR content intact
    } finally {
      shell.classList.remove('judge-shell--loading');
      shell.querySelector('.judge-shell__overlay')?.remove();
    }
  }

  function updateAdminDom(data) {
    const totalUsers = document.querySelector('[data-admin-total-usuarios]');
    const totalNotifs = document.querySelector('[data-admin-total-notificacoes]');
    const hint = document.querySelector('[data-admin-notification-hint]');

    if (totalUsers && data && data.total_usuarios !== undefined) {
      totalUsers.textContent = String(data.total_usuarios);
    }
    if (totalNotifs && data && data.total_notificacoes !== undefined) {
      totalNotifs.textContent = String(data.total_notificacoes);
    }
    if (hint && data && data.total_notificacoes !== undefined) {
      hint.textContent = data.total_notificacoes > 0
        ? `Você tem ${data.total_notificacoes} aviso(s) pendente(s).`
        : 'Nenhum aviso pendente no momento.';
    }
  }

  async function hydrateAdminPage() {
    const shell = document.querySelector('[data-admin-shell]');
    if (!shell) {
      return;
    }

    const apiUrl = shell.dataset.adminApi;
    const cacheKey = shell.dataset.adminCacheKey || `${CACHE_PREFIX}admin`;
    if (!apiUrl) {
      return;
    }

    const cached = readCachedJSON(cacheKey);
    if (cached && cached.data) {
      updateAdminDom(cached.data);
    } else {
      const overlay = document.createElement('div');
      overlay.innerHTML = `
        <div class="admin-shell__overlay" aria-busy="true" aria-live="polite">
          <div class="admin-shell__overlay-strip"></div>
          <div class="admin-shell__overlay-card"></div>
          <div class="admin-shell__overlay-card"></div>
        </div>
      `;
      const node = overlay.firstElementChild;
      if (node) {
        shell.classList.add('admin-shell--loading');
        shell.style.position = 'relative';
        shell.prepend(node);
      }
    }

    try {
      const response = await fetch(apiUrl, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'fetch' }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const payload = await response.json();
      if (!payload || payload.sucesso === false) throw new Error('Falha ao carregar painel admin');

      writeCachedJSON(cacheKey, {
        saved_at: new Date().toISOString(),
        data: payload.dados
      });
      updateAdminDom(payload.dados);
    } catch (error) {
      // keep SSR content intact
    } finally {
      shell.classList.remove('admin-shell--loading');
      shell.querySelector('.admin-shell__overlay')?.remove();
    }
  }

  function renderRankingMarkup(dados) {
    const ranking = Array.isArray(dados && dados.ranking) ? dados.ranking : [];
    const rankingTop3 = ranking.slice(0, 3);
    const rankingRest = ranking.slice(3);

    const facts = [
      { value: formatRankingValue(dados && dados.total_partidas), label: 'Partidas' },
      { value: formatRankingValue(dados && dados.total_votos), label: 'Votos' },
      { value: formatRankingValue(dados && dados.total_jogadores), label: 'Jogadores' }
    ].map(item => `
      <div class="ranking-hero__fact">
        <span>${escapeHtml(item.value)}</span>
        <small>${escapeHtml(item.label)}</small>
      </div>
    `).join('');

    const mobileTop3 = rankingTop3.map((item, index) => {
      const progressScore = Math.max(0, Math.min(100, Number(item.pontos) || 0));
      const rankClass = index === 0 ? 'ranking-1' : index === 1 ? 'ranking-2' : 'ranking-3';
      return `
        <article class="ranking-spotlight ranking-spotlight--${index + 1}">
          <div class="ranking-spotlight__rank ${rankClass}">${rankingPositionLabel(index)}</div>
          <div class="ranking-spotlight__content">
            <div class="ranking-spotlight__name">${escapeHtml(item.jogador_nome)}</div>
            <div class="ranking-spotlight__meta">${escapeHtml(item.jogos)} jogos • ${escapeHtml(item.vitorias)} vitórias • ${escapeHtml(item.derrotas)} derrotas</div>
            <div class="ranking-spotlight__stats">
              <span>${escapeHtml(item.destaques)} destaques</span>
              <span>${escapeHtml(item.nota_media)} média</span>
              <span>${escapeHtml(item.gols)} gols</span>
            </div>
            <div class="ranking-spotlight__bar" aria-hidden="true"><span style="width: ${progressScore}%;"></span></div>
          </div>
          <div class="ranking-spotlight__score">${escapeHtml(item.pontos)}</div>
        </article>
      `;
    }).join('');

    const mobileRest = rankingRest.map((item, index) => `
      <article class="ranking-row-card">
        <div class="ranking-row-card__rank ranking-other">${index + 4}</div>
        <div class="ranking-row-card__content">
          <div class="ranking-row-card__name">${escapeHtml(item.jogador_nome)}</div>
          <div class="ranking-row-card__meta">${escapeHtml(item.jogos)} jogos • ${escapeHtml(item.vitorias)} vitórias • ${escapeHtml(item.gols)} gols</div>
        </div>
        <div class="ranking-row-card__score">
          <strong>${escapeHtml(item.pontos)}</strong>
          <span>${escapeHtml(item.nota_media)} média</span>
        </div>
      </article>
    `).join('');

    const tableRows = ranking.map((item, index) => `
      <tr${index < 3 ? ' style="background: rgba(102, 126, 234, 0.05);"' : ''}>
        <td>${rankingPositionLabel(index)}</td>
        <td style="font-weight: 600;">${escapeHtml(item.jogador_nome)}</td>
        <td class="text-center" style="font-weight: 700;">${escapeHtml(item.pontos)}</td>
        <td class="text-center">${escapeHtml(item.jogos)}</td>
        <td class="text-center">${escapeHtml(item.gols)}</td>
        <td class="text-center">${escapeHtml(item.vitorias)}</td>
        <td class="text-center">${escapeHtml(item.derrotas)}</td>
        <td class="text-center">${escapeHtml(item.destaques)}</td>
        <td class="text-center">${escapeHtml(item.nota_media)}</td>
      </tr>
    `).join('');

    if (!ranking.length) {
      return `
        <section class="section ranking-hero">
          <div class="ranking-hero__heading">
            <div>
              <span class="section-label">Classificação geral</span>
              <h1 class="ranking-hero__title">Ranking de Jogadores</h1>
              <p class="section-subtitle ranking-hero__subtitle">Visão consolidada de desempenho, participação e evolução da temporada.</p>
            </div>
          </div>
          <div class="alert alert-warning">Sem dados ainda. Abra votação no painel admin, colete votos e encerre a rodada.</div>
        </section>
      `;
    }

    return `
      <section class="section ranking-hero">
        <div class="ranking-hero__heading">
          <div>
            <span class="section-label">Classificação geral</span>
            <h1 class="ranking-hero__title">Ranking de Jogadores</h1>
            <p class="section-subtitle ranking-hero__subtitle">Visão consolidada de desempenho, participação e evolução da temporada.</p>
          </div>
        </div>

        <div class="ranking-hero__facts" aria-label="Resumo do ranking">
          ${facts}
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">🏆 Classificação</h2>
        <div class="ranking-mobile-list" aria-label="Ranking completo em cards para mobile">
          <div class="ranking-mobile-list__section">
            ${mobileTop3}
          </div>
          ${rankingRest.length ? `<div class="ranking-mobile-list__rest">${mobileRest}</div>` : ''}
        </div>

        <div class="table-shell ranking-desktop-table">
          <table class="uniform-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Jogador</th>
                <th class="text-center">Nota</th>
                <th class="text-center">Jogos</th>
                <th class="text-center">Gols</th>
                <th class="text-center">Vitórias</th>
                <th class="text-center">Derrotas</th>
                <th class="text-center">Destaques</th>
                <th class="text-center">Nota média</th>
              </tr>
            </thead>
            <tbody>
              ${tableRows}
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  async function hydrateRankingPage() {
    const shell = document.querySelector('[data-ranking-shell]');
    if (!shell) {
      return;
    }

    const apiUrl = shell.dataset.rankingApi;
    const cacheKey = shell.dataset.rankingCacheKey || `${CACHE_PREFIX}ranking`;
    if (!apiUrl) {
      return;
    }

    const cached = readCachedJSON(cacheKey);
    if (cached && cached.data) {
      shell.innerHTML = renderRankingMarkup(cached.data);
    } else {
      shell.classList.add('ranking-shell--loading');
      shell.innerHTML = renderRankingSkeleton();
    }

    try {
      const response = await fetch(apiUrl, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'fetch'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = await response.json();
      if (!payload || payload.sucesso === false) {
        throw new Error(payload && payload.erro ? payload.erro : 'Falha ao carregar ranking');
      }

      writeCachedJSON(cacheKey, {
        saved_at: new Date().toISOString(),
        data: payload.dados
      });

      shell.classList.remove('ranking-shell--loading');
      shell.innerHTML = renderRankingMarkup(payload.dados);
    } catch (error) {
      if (!cached || !cached.data) {
        shell.classList.remove('ranking-shell--loading');
      }
    }
  }

  function updateShell(nextDocument, nextUrl) {
    const nextContent = getContent(nextDocument);
    const currentContent = getContent(document);

    if (!nextContent || !currentContent) {
      return false;
    }

    document.body.className = nextDocument.body.className;
    currentContent.innerHTML = nextContent.innerHTML;
    rehydrateScripts(currentContent);

    if (nextDocument.title) {
      document.title = nextDocument.title;
    }

    refreshFooterState(nextUrl);
    runPageHooks();
    window.scrollTo(0, 0);

    return true;
  }

  function shouldUseViewTransition() {
    return typeof document.startViewTransition === 'function' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  async function loadPage(url, options) {
    const targetUrl = normalizeUrl(url);
    const token = ++navigationToken;
    const replace = Boolean(options && options.replace);

    setLoading(true);

    try {
      const response = await fetch(targetUrl.href, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'fetch'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const html = await response.text();
      if (token !== navigationToken) {
        return;
      }

      const nextDocument = new DOMParser().parseFromString(html, 'text/html');
      const rendered = () => {
        if (!updateShell(nextDocument, targetUrl)) {
          window.location.assign(targetUrl.href);
          return;
        }

        const state = { path: targetUrl.pathname + targetUrl.search };
        if (replace) {
          history.replaceState(state, '', targetUrl.href);
        } else {
          history.pushState(state, '', targetUrl.href);
        }
      };

      if (shouldUseViewTransition()) {
        const transition = document.startViewTransition(rendered);
        await transition.finished.catch(() => {});
      } else {
        rendered();
      }
    } catch (error) {
      window.location.assign(targetUrl.href);
    } finally {
      if (token === navigationToken) {
        setLoading(false);
      }
    }
  }

  function collectPrefetchTargets() {
    const urls = new Set();

    document.querySelectorAll('.site-footer__link[href], .judge-nav__tab[href]').forEach(link => {
      urls.add(normalizeUrl(link.href).href);
    });

    const commonTargets = ['/', '/ranking', '/historico', '/perfil', '/admin', '/jogar'];
    commonTargets.forEach(path => urls.add(normalizeUrl(path).href));

    return Array.from(urls);
  }

  function prefetchUrl(href) {
    if (prefetched.has(href)) return;
    prefetched.add(href);
    fetch(href, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'prefetch'
      }
    }).catch(() => {});
  }

  function schedulePrefetch() {
    const run = () => {
      collectPrefetchTargets().slice(0, 6).forEach(prefetchUrl);
    };

    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(run, { timeout: 1500 });
      return;
    }

    window.setTimeout(run, 600);
  }

  function boot() {
    refreshFooterState(new URL(window.location.href));
    runPageHooks();
    schedulePrefetch();
  }

  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!shouldHandleLink(link, event)) {
      return;
    }

    event.preventDefault();
    loadPage(link.href, { replace: false });
  }, true);

  // Delegação de clique para cartões de jogadores (.player-card) integrada com o PWA
  document.addEventListener('click', event => {
    const card = event.target.closest('.player-card');
    if (!card) return;

    if (event.target.closest('a') || event.target.closest('button')) {
      return;
    }

    const btn = card.querySelector('.premium-player-card-btn');
    if (btn) {
      event.preventDefault();
      btn.click();
    }
  });

  // Delegação de clique para abas de filtros de categoria (.premium-filter-tab)
  document.addEventListener('click', event => {
    const tab = event.target.closest('.premium-filter-tab');
    if (!tab) return;

    event.preventDefault();
    const filterValue = tab.getAttribute('data-filter');

    // 1. Atualizar classe ativa das abas de filtro
    document.querySelectorAll('.premium-filter-tab').forEach(t => {
      t.classList.toggle('is-active', t === tab);
    });

    // 2. Filtrar os cards de jogadores baseando-se em tipo/posição
    document.querySelectorAll('.player-card').forEach(card => {
      const tipo = String(card.getAttribute('data-tipo') || '').trim().toLowerCase();
      const posicao = String(card.getAttribute('data-posicao') || '').trim().toLowerCase();

      let matches = false;
      if (filterValue === 'all') {
        matches = true;
      } else if (filterValue === 'fixo' && tipo === 'fixo') {
        matches = true;
      } else if (filterValue === 'avulso' && tipo === 'avulso') {
        matches = true;
      } else if (filterValue === 'goleiro' && posicao === 'goleiro') {
        matches = true;
      } else if (filterValue === 'linha' && posicao === 'linha') {
        matches = true;
      }

      if (matches) {
        card.style.removeProperty('display');
      } else {
        card.style.setProperty('display', 'none', 'important');
      }
    });
  });

  window.addEventListener('popstate', () => {
    loadPage(window.location.href, { replace: true });
  });

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
