/**
 * Juiz Onboarding Tour - Simulador Interativo Passo a Passo
 * Permite ao usuário executar o fluxo real de sorteio de forma guiada:
 * 1. Clicar em "Selecionar jogadores"
 * 2. Escolher quantidade (10 / 15 / 20)
 * 3. Selecionar atletas da lista de 20 jogadores fictícios com notas aleatórias e aviso de demonstração
 * 4. Clicar em "Sortear Times"
 * 5. Visualizar times, testar troca/edição, copiar WhatsApp e clicar em "Iniciar Rodada"
 * 6. Visualizar onde lançar resultados, clicar em "Abrir Votação" e "Encerrar Partida"
 * 7. Apresentação das abas "Histórico" e "Cronômetro" na barra inferior
 */

(function () {
  'use strict';

  const SVG_ICONS = {
    criar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m14.5 4.5 5 5"/><path d="M4 20l4.5-1 10-10a2.12 2.12 0 0 0-3-3l-10 10z"/></svg>`,
    jogadores: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    sorteio: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 7h.01"/><path d="M17 7h.01"/><path d="M7 17h.01"/><path d="M17 17h.01"/><path d="M12 12h.01"/></svg>`,
    swap: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/></svg>`,
    whatsapp: `<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M20.52 3.48A11.9 11.9 0 0 0 12.06 0C5.46 0 .09 5.37.09 11.97c0 2.11.55 4.17 1.6 5.98L0 24l6.23-1.63a11.93 11.93 0 0 0 5.83 1.51h.01c6.6 0 11.97-5.37 11.97-11.97 0-3.2-.12-6.21-3.52-8.43z"/></svg>`,
    play: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`,
    historico: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>`,
    cronometro: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2"/><path d="M9 2h6"/></svg>`,
    votacao: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 12 11 14 15 10"/><path d="M5 3h14"/><path d="M5 7h14"/><path d="M7 21h10a2 2 0 0 0 2-2V9H5v10a2 2 0 0 0 2 2Z"/></svg>`,
    check: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
    arrowRight: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`,
    copy: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`
  };

  // 20 Jogadores Fictícios com posições e notas realistas de demonstração
  const JOGADORES_FICTICIOS = [
    { id: 'f1', nome: 'Gabriel Costa', posicao: 'goleiro', nivel: 9.0 },
    { id: 'f2', nome: 'Bruno Rocha', posicao: 'goleiro', nivel: 8.5 },
    { id: 'f3', nome: 'Thiago Neves', posicao: 'goleiro', nivel: 8.0 },
    { id: 'f4', nome: 'Danilo Alcantara', posicao: 'goleiro', nivel: 7.5 },
    { id: 'f5', nome: 'Lucas Silva', posicao: 'linha', nivel: 8.5 },
    { id: 'f6', nome: 'Igor Martins', posicao: 'linha', nivel: 9.0 },
    { id: 'f7', nome: 'Matheus Lima', posicao: 'linha', nivel: 8.0 },
    { id: 'f8', nome: 'Rafael Souza', posicao: 'linha', nivel: 8.0 },
    { id: 'f9', nome: 'André Santos', posicao: 'linha', nivel: 7.5 },
    { id: 'f10', nome: 'Felipe Ramos', posicao: 'linha', nivel: 7.5 },
    { id: 'f11', nome: 'Pedro Alves', posicao: 'linha', nivel: 7.0 },
    { id: 'f12', nome: 'Caio Ribeiro', posicao: 'linha', nivel: 6.5 },
    { id: 'f13', nome: 'Rodrigo Mendes', posicao: 'linha', nivel: 8.5 },
    { id: 'f14', nome: 'Gustavo Henrique', posicao: 'linha', nivel: 8.0 },
    { id: 'f15', nome: 'Vinicius Prado', posicao: 'linha', nivel: 7.5 },
    { id: 'f16', nome: 'Leandro Barbosa', posicao: 'linha', nivel: 7.0 },
    { id: 'f17', nome: 'Bernardo Castro', posicao: 'linha', nivel: 7.0 },
    { id: 'f18', nome: 'Eduardo Farias', posicao: 'linha', nivel: 6.5 },
    { id: 'f19', nome: 'Murilo Silveira', posicao: 'linha', nivel: 6.5 },
    { id: 'f20', nome: 'Renan Pires', posicao: 'linha', nivel: 6.0 }
  ];

  // Estado da simulação interativa
  let simState = {
    step: 0,
    targetQty: null,
    selectedPlayerIds: new Set(),
    teams: [],
    swappingPlayer: null,
    isEditingTeams: false,
    golsTime1: 3,
    golsTime2: 2,
    votacaoAberta: false,
    votacaoEncerrada: false,
    partidaEncerrada: false,
    timerSeconds: 600,
    timerRunning: false,
    timerInterval: null
  };

  const TOTAL_STEPS = 8;
  let overlayEl = null;
  let originalActiveTab = null;

  function obterChaveStorage() {
    const cod = window.CLUBE_CODIGO || (document.body ? document.body.getAttribute('data-clube-codigo') : '') || '001';
    return `natrave_juiz_tour_completed_${cod}`;
  }

  function criarEstruturaTour() {
    if (document.getElementById('juizTourOverlay')) {
      return document.getElementById('juizTourOverlay');
    }

    const overlay = document.createElement('div');
    overlay.id = 'juizTourOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Tour Interativo do Modo Juiz');

    overlay.innerHTML = `
      <div id="juizTourCard">
        <div class="juiz-tour-header">
          <div class="juiz-tour-step-mini" id="simStepPill">Passo <strong>1</strong> de ${TOTAL_STEPS}</div>
          <button type="button" class="juiz-tour-btn-skip" id="btnSkipJuizTour" aria-label="Fechar">
            <span>Fechar</span> ✕
          </button>
        </div>

        <div id="simDynamicContainer" class="juiz-sim-stage"></div>

        <div class="juiz-tour-footer">
          <div class="juiz-tour-dots-wrap" id="simDotsWrap">
            ${Array.from({ length: TOTAL_STEPS }).map((_, i) => `<div class="juiz-tour-dot ${i === 0 ? 'is-active' : ''}" data-step="${i}" title="Passo ${i + 1}"></div>`).join('')}
          </div>
          <div class="juiz-tour-actions-wrap" id="simFooterActions"></div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    document.getElementById('btnSkipJuizTour').addEventListener('click', encerrarJuizTour);

    // Permite navegar clicando nos dots
    overlay.querySelectorAll('#simDotsWrap .juiz-tour-dot').forEach((dot) => {
      dot.addEventListener('click', function () {
        const s = parseInt(this.getAttribute('data-step'), 10);
        irParaEtapaPorIndice(s);
      });
    });

    return overlay;
  }

  function atualizarIndicador(passoIdx, footerTabId = null) {
    simState.step = passoIdx;

    const pill = document.getElementById('simStepPill');
    if (pill) {
      pill.innerHTML = `Passo <strong>${passoIdx + 1}</strong> de ${TOTAL_STEPS}`;
    }

    // Atualiza dots
    document.querySelectorAll('#simDotsWrap .juiz-tour-dot').forEach((dot, i) => {
      dot.classList.toggle('is-active', i === passoIdx);
    });

    // Remove classe is-active de todas as abas durante o tour para não haver confusão visual
    document.querySelectorAll('.site-footer__link').forEach(el => el.classList.remove('is-active'));

    // Destaque limpo e nítido na aba inferior correspondente
    document.querySelectorAll('.tour-highlight-tab').forEach(el => el.classList.remove('tour-highlight-tab'));
    if (footerTabId) {
      const tab = document.getElementById(footerTabId);
      if (tab) {
        tab.classList.add('tour-highlight-tab');
        try { tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' }); } catch (e) {}
      }
    }
  }

  function irParaEtapaPorIndice(idx) {
    if (idx === 0) renderEtapa1_Inicio();
    else if (idx === 1) renderEtapa2_Formato();
    else if (idx === 2) {
      if (!simState.targetQty) simState.targetQty = 10;
      renderEtapa3_SelecaoJogadores();
    }
    else if (idx === 3) {
      if (!simState.targetQty) simState.targetQty = 10;
      if (!simState.teams || simState.teams.length === 0) {
        preencherJogadoresFicticiosPadrao();
        gerarTimesSimulados();
      }
      renderEtapa4_Times();
    }
    else if (idx === 4) renderEtapa5_Resultados();
    else if (idx === 5) renderEtapa6_Votacao();
    else if (idx === 6) renderEtapa7_Historico();
    else if (idx === 7) renderEtapa8_Cronometro();
  }

  function preencherJogadoresFicticiosPadrao() {
    if (!simState.targetQty) simState.targetQty = 10;
    simState.selectedPlayerIds.clear();
    const numGoleiros = simState.targetQty === 20 ? 4 : (simState.targetQty === 15 ? 3 : 2);
    const numLinha = simState.targetQty - numGoleiros;
    const goleiros = JOGADORES_FICTICIOS.filter(j => j.posicao === 'goleiro').slice(0, numGoleiros);
    const linha = JOGADORES_FICTICIOS.filter(j => j.posicao !== 'goleiro').slice(0, numLinha);
    [...goleiros, ...linha].forEach(j => simState.selectedPlayerIds.add(j.id));
  }

  function renderEtapaSair() {
    atualizarIndicador(
      simState.step,
      'INFORMAÇÃO: SAIR DO MODO JUIZ',
      'tourJuizTabSair'
    );

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div class="sim-tab-feature-card">
        <div class="sim-tab-feature-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </div>
        <h4>Aba Sair (Logout Seguro)</h4>
        <p>Ao término de todos os jogos da rodada, você clica nesta aba para encerrar a sessão do juiz no dispositivo do clube com total segurança.</p>
        <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 8px; padding: 0.45rem 0.8rem; font-size: 0.78rem; color: #4ade80; font-weight: 750;">
          Você está no modo Tour. Os botões abaixo funcionam exclusivamente para demonstração.
        </div>
      </div>
    `;

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarDoSair">
        ← Voltar ao Tour
      </button>
    `;

    document.getElementById('btnVoltarDoSair').addEventListener('click', () => {
      irParaEtapaPorIndice(simState.step || 0);
    });
  }

  // ==========================================
  // ETAPA 1: Início - Clicar em "Selecionar jogadores"
  // ==========================================
  function renderEtapa1_Inicio() {
    atualizarIndicador(0, 'tourJuizTabCriar');

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div class="sim-start-card">
        <h3 style="margin: 0; font-size: 1.3rem; font-weight: 850; color: #ffffff;">Criar Partida</h3>
        <button type="button" class="sim-btn-action-primary" id="btnSimSelecionarJogadores">
          <span>Selecionar jogadores</span>
          ${SVG_ICONS.arrowRight}
        </button>
      </div>
    `;

    document.getElementById('btnSimSelecionarJogadores').addEventListener('click', () => {
      renderEtapa2_Formato();
    });

    document.getElementById('simFooterActions').innerHTML = ``;
  }

  // ==========================================
  // ETAPA 2: Escolha de Formato (10, 15, 20)
  // ==========================================
  function renderEtapa2_Formato() {
    atualizarIndicador(1, 'tourJuizTabCriar');

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div style="margin-bottom: 0.5rem;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 850; color: #ffffff;">Quantos jogadores vão jogar?</h3>
      </div>

      <div class="sim-qty-picker" style="margin-top: 0.25rem;">
        <button type="button" class="sim-qty-btn ${simState.targetQty === 10 ? 'is-selected' : ''}" data-qty="10">
          <span class="sim-qty-number">10</span>
          <span class="sim-qty-label">2 times</span>
        </button>
        <button type="button" class="sim-qty-btn ${simState.targetQty === 15 ? 'is-selected' : ''}" data-qty="15">
          <span class="sim-qty-number">15</span>
          <span class="sim-qty-label">3 times</span>
        </button>
        <button type="button" class="sim-qty-btn ${simState.targetQty === 20 ? 'is-selected' : ''}" data-qty="20">
          <span class="sim-qty-number">20</span>
          <span class="sim-qty-label">4 times</span>
        </button>
      </div>
    `;

    container.querySelectorAll('.sim-qty-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const qty = parseInt(this.getAttribute('data-qty'), 10);
        simState.targetQty = qty;
        // Limpa seleções anteriores para não herdar jogadores de outros formatos
        simState.selectedPlayerIds.clear();
        simState.teams = [];
        renderEtapa3_SelecaoJogadores();
      });
    });

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa1">
        ← Voltar
      </button>
    `;
    document.getElementById('btnVoltarEtapa1').addEventListener('click', () => {
      renderEtapa1_Inicio();
    });
  }

  // ==========================================
  // ETAPA 3: Convocação dos Atletas Presentes
  // ==========================================
  function renderEtapa3_SelecaoJogadores() {
    // Garante que a seleção nunca ultrapasse a quantidade escolhida
    if (simState.selectedPlayerIds.size > simState.targetQty) {
      const ids = Array.from(simState.selectedPlayerIds).slice(0, simState.targetQty);
      simState.selectedPlayerIds = new Set(ids);
    }

    const isPronto = simState.selectedPlayerIds.size === simState.targetQty;
    atualizarIndicador(2, 'tourJuizTabCriar');

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div class="sim-players-header">
        <div class="sim-selection-counter">
          Selecionados: <strong id="simCounterText">${simState.selectedPlayerIds.size}</strong> / ${simState.targetQty}
        </div>
        <button type="button" class="sim-quick-select-btn" id="btnAutoPreencher">
          Auto-preencher ${simState.targetQty}
        </button>
      </div>

      <div class="sim-players-scroll" id="simPlayersList">
        ${JOGADORES_FICTICIOS.map(j => {
          const isSelected = simState.selectedPlayerIds.has(j.id);
          const iconPos = j.posicao === 'goleiro' ? '🧤' : '⚽';
          const labelPos = j.posicao === 'goleiro' ? 'Goleiro' : 'Linha';
          return `
            <div class="sim-player-card ${isSelected ? 'is-selected' : ''}" data-player-id="${j.id}">
              <div class="sim-player-meta">
                <span class="sim-player-name">${j.nome}</span>
                <span class="sim-player-role">${iconPos} ${labelPos}</span>
              </div>
              <span class="sim-player-badge">${j.nivel.toFixed(1)}</span>
            </div>
          `;
        }).join('')}
      </div>

      <div id="simSortearArea" class="sim-sort-action-container" style="${isPronto ? '' : 'display: none;'}">
        <button type="button" class="sim-btn-sortear" id="btnSimSortear">
          ${SVG_ICONS.sorteio}
          <span>Sortear Times</span>
        </button>
      </div>
    `;

    // Handler de clique em cada jogador
    container.querySelectorAll('.sim-player-card').forEach(card => {
      card.addEventListener('click', function () {
        const id = this.getAttribute('data-player-id');
        if (simState.selectedPlayerIds.has(id)) {
          simState.selectedPlayerIds.delete(id);
        } else {
          if (simState.selectedPlayerIds.size < simState.targetQty) {
            simState.selectedPlayerIds.add(id);
          }
        }
        atualizarGridJogadores();
      });
    });

    // Auto-preencher inteligente respeitando exatamente targetQty e equilíbrio de posições
    document.getElementById('btnAutoPreencher').addEventListener('click', () => {
      preencherJogadoresFicticiosPadrao();
      atualizarGridJogadores();
    });

    // Botão Sortear
    const btnSort = document.getElementById('btnSimSortear');
    if (btnSort) {
      btnSort.addEventListener('click', () => {
        if (simState.selectedPlayerIds.size === simState.targetQty) {
          gerarTimesSimulados();
          renderEtapa4_Times();
        }
      });
    }

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa2">
        ← Voltar
      </button>
    `;
    document.getElementById('btnVoltarEtapa2').addEventListener('click', () => {
      renderEtapa2_Formato();
    });
  }

  function atualizarGridJogadores() {
    const list = document.getElementById('simPlayersList');
    if (!list) return;

    list.querySelectorAll('.sim-player-card').forEach(card => {
      const id = card.getAttribute('data-player-id');
      card.classList.toggle('is-selected', simState.selectedPlayerIds.has(id));
    });

    const isPronto = simState.selectedPlayerIds.size === simState.targetQty;
    const counter = document.getElementById('simCounterText');
    if (counter) counter.textContent = simState.selectedPlayerIds.size;

    const sortArea = document.getElementById('simSortearArea');
    if (sortArea) {
      sortArea.style.display = isPronto ? 'flex' : 'none';
      const btnSortear = document.getElementById('btnSimSortear');
      if (btnSortear && !btnSortear._hasAttached) {
        btnSortear._hasAttached = true;
        btnSortear.addEventListener('click', () => {
          if (simState.selectedPlayerIds.size === simState.targetQty) {
            gerarTimesSimulados();
            renderEtapa4_Times();
          }
        });
      }
    }
  }

  function gerarTimesSimulados() {
    const selecionados = JOGADORES_FICTICIOS.filter(j => simState.selectedPlayerIds.has(j.id));
    const goleiros = selecionados.filter(j => j.posicao === 'goleiro');
    const linha = selecionados.filter(j => j.posicao !== 'goleiro');

    const numTimes = simState.targetQty === 20 ? 4 : (simState.targetQty === 15 ? 3 : 2);
    const times = Array.from({ length: numTimes }, (_, i) => ({
      numero: i + 1,
      nome: i === 0 ? 'Time 1 (Verde)' : (i === 1 ? 'Time 2 (Azul)' : (i === 2 ? 'Time 3 (Laranja)' : 'Time 4 (Branco)')),
      corClass: i === 0 ? 'team-verde' : (i === 1 ? 'team-azul' : ''),
      jogadores: []
    }));

    // Distribui goleiros
    goleiros.forEach((g, idx) => {
      times[idx % numTimes].jogadores.push(g);
    });

    // Distribui linha balanceando
    linha.forEach((l, idx) => {
      times[idx % numTimes].jogadores.push(l);
    });

    simState.teams = times;
  }

  // ==========================================
  // ETAPA 4: Tela de Times Sorteados, Edição & Ações Compactas (Imagem 3 e 4)
  // ==========================================
  function renderEtapa4_Times() {
    atualizarIndicador(3, 'tourJuizTabTimes');

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.45rem;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 850; color: #ffffff;">Times Sorteados</h3>
        <button type="button" class="sim-btn-edit-teams ${simState.isEditingTeams ? 'is-active' : ''}" id="btnSimEditarTimes">
          ${SVG_ICONS.swap}
          <span>${simState.isEditingTeams ? 'Concluir' : 'Editar'}</span>
        </button>
      </div>

      ${simState.isEditingTeams ? `
        <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 8px; padding: 0.35rem 0.65rem; font-size: 0.76rem; color: #4ade80; font-weight: 700; margin-bottom: 0.45rem;">
          Toque em 2 atletas para trocar suas posições entre os times.
        </div>
      ` : ''}

      <div class="sim-teams-grid" id="simTeamsGrid">
        ${simState.teams.slice(0, 2).map(t => {
          const somaNivel = t.jogadores.reduce((acc, curr) => acc + curr.nivel, 0);
          return `
            <div class="sim-team-box ${t.corClass}" data-team-num="${t.numero}">
              <div class="sim-team-header">
                <strong style="color: ${t.numero === 1 ? '#22c55e' : '#38bdf8'};">${t.nome}</strong>
                <span style="color: #94a3b8;">${somaNivel.toFixed(1)} pts</span>
              </div>
              <div class="sim-team-players">
                ${t.jogadores.map(j => `
                  <div class="sim-team-player-row ${simState.swappingPlayer && simState.swappingPlayer.id === j.id ? 'is-swapping' : ''}" data-player-id="${j.id}" data-team-num="${t.numero}">
                    <span>${j.posicao === 'goleiro' ? '🧤' : '⚽'} ${j.nome.split(' ')[0]}</span>
                    <strong>${j.nivel.toFixed(1)}</strong>
                  </div>
                `).join('')}
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <div class="sim-team-actions-compact-row">
        <button type="button" class="sim-btn-compact-secondary" id="btnSimCopiar">
          ${SVG_ICONS.copy}
          <span id="txtCopiarLabel">Copiar</span>
        </button>

        <button type="button" class="sim-btn-action-primary" id="btnSimIniciarRodada" style="flex: 1; justify-content: center; padding: 0.55rem 1rem;">
          ${SVG_ICONS.play}
          <span>Iniciar Rodada</span>
        </button>
      </div>
    `;

    // Botão Editar / Concluir Edição
    document.getElementById('btnSimEditarTimes').addEventListener('click', () => {
      simState.isEditingTeams = !simState.isEditingTeams;
      simState.swappingPlayer = null;
      renderEtapa4_Times();
    });

    // Simulação de troca interativa entre jogadores ao clicar em dois atletas
    container.querySelectorAll('.sim-team-player-row').forEach(row => {
      row.addEventListener('click', function () {
        const playerId = this.getAttribute('data-player-id');
        const teamNum = parseInt(this.getAttribute('data-team-num'), 10);
        const playerObj = JOGADORES_FICTICIOS.find(j => j.id === playerId);

        if (!simState.swappingPlayer) {
          simState.swappingPlayer = { id: playerId, teamNum: teamNum, obj: playerObj };
          simState.isEditingTeams = true;
          renderEtapa4_Times();
        } else {
          if (simState.swappingPlayer.id !== playerId) {
            // Executa a troca entre os times
            const tOrigem = simState.teams.find(t => t.numero === simState.swappingPlayer.teamNum);
            const tDestino = simState.teams.find(t => t.numero === teamNum);

            if (tOrigem && tDestino) {
              const idx1 = tOrigem.jogadores.findIndex(j => j.id === simState.swappingPlayer.id);
              const idx2 = tDestino.jogadores.findIndex(j => j.id === playerId);
              if (idx1 !== -1 && idx2 !== -1) {
                const temp = tOrigem.jogadores[idx1];
                tOrigem.jogadores[idx1] = tDestino.jogadores[idx2];
                tDestino.jogadores[idx2] = temp;
              }
            }
          }
          simState.swappingPlayer = null;
          renderEtapa4_Times();
        }
      });
    });

    // Copiar simples e direto (sem referência ao WhatsApp)
    document.getElementById('btnSimCopiar').addEventListener('click', function () {
      const lbl = document.getElementById('txtCopiarLabel');
      if (lbl) {
        lbl.textContent = 'Copiado!';
        setTimeout(() => { if (lbl) lbl.textContent = 'Copiar'; }, 2000);
      }
    });

    // Iniciar Rodada
    document.getElementById('btnSimIniciarRodada').addEventListener('click', () => {
      renderEtapa5_Resultados();
    });

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa3">
        ← Voltar
      </button>
    `;
    document.getElementById('btnVoltarEtapa3').addEventListener('click', () => {
      renderEtapa3_SelecaoJogadores();
    });
  }

  // ==========================================
  // ETAPA 5: Registro de Resultados & Encerrar Partida
  // ==========================================
  function renderEtapa5_Resultados() {
    atualizarIndicador(4, 'tourJuizTabTimes');

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div style="margin-bottom: 0.5rem;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 850; color: #ffffff;">Registro de Resultados</h3>
      </div>

      <div class="sim-score-panel">
        <div class="sim-score-row">
          <span style="font-size: 0.85rem; font-weight: 800; color: #22c55e;">Time 1 (Verde)</span>
          <div class="sim-score-controls">
            <button type="button" class="sim-quick-select-btn" id="btnGolsMenos1">-</button>
            <span class="sim-score-value" id="valGols1">${simState.golsTime1} gols</span>
            <button type="button" class="sim-quick-select-btn" id="btnGolsMais1">+</button>
          </div>
        </div>

        <div class="sim-score-row">
          <span style="font-size: 0.85rem; font-weight: 800; color: #38bdf8;">Time 2 (Azul)</span>
          <div class="sim-score-controls">
            <button type="button" class="sim-quick-select-btn" id="btnGolsMenos2">-</button>
            <span class="sim-score-value" id="valGols2">${simState.golsTime2} gols</span>
            <button type="button" class="sim-quick-select-btn" id="btnGolsMais2">+</button>
          </div>
        </div>
      </div>

      <div style="margin-top: 0.5rem;">
        <button type="button" class="sim-btn-action-primary" id="btnSimEncerrarResultados" style="width: 100%; justify-content: center; background: #22c55e; color: #000000;">
          ${SVG_ICONS.check}
          <span>Encerrar Partida & Salvar Resultados</span>
        </button>
      </div>
    `;

    // Controles de placar
    document.getElementById('btnGolsMenos1').addEventListener('click', () => {
      if (simState.golsTime1 > 0) simState.golsTime1--;
      document.getElementById('valGols1').textContent = `${simState.golsTime1} gols`;
    });
    document.getElementById('btnGolsMais1').addEventListener('click', () => {
      simState.golsTime1++;
      document.getElementById('valGols1').textContent = `${simState.golsTime1} gols`;
    });
    document.getElementById('btnGolsMenos2').addEventListener('click', () => {
      if (simState.golsTime2 > 0) simState.golsTime2--;
      document.getElementById('valGols2').textContent = `${simState.golsTime2} gols`;
    });
    document.getElementById('btnGolsMais2').addEventListener('click', () => {
      simState.golsTime2++;
      document.getElementById('valGols2').textContent = `${simState.golsTime2} gols`;
    });

    // Encerrar resultados e ir para o card de votação
    document.getElementById('btnSimEncerrarResultados').addEventListener('click', () => {
      simState.partidaEncerrada = true;
      renderEtapa6_Votacao();
    });

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa4">
        ← Voltar
      </button>
    `;
    document.getElementById('btnVoltarEtapa4').addEventListener('click', () => {
      renderEtapa4_Times();
    });
  }

  // ==========================================
  // ETAPA 6: Votação no App (Novo Card Dedicado)
  // ==========================================
  function renderEtapa6_Votacao() {
    atualizarIndicador(5, 'tourJuizTabVotacoes');

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div style="margin-bottom: 0.5rem;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 850; color: #ffffff;">Craque & Bagre da Partida</h3>
      </div>

      <div class="sim-voting-preview-box">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
          <div style="display: flex; align-items: center; gap: 0.45rem; color: #22c55e;">
            ${SVG_ICONS.votacao}
            <strong style="font-size: 0.88rem; color: #ffffff;">Votação Oficial</strong>
          </div>
          <span id="txtVotacaoBadge" style="font-size: 0.74rem; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 999px; ${simState.votacaoEncerrada ? 'background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3);' : (simState.votacaoAberta ? 'background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid #22c55e;' : 'background: rgba(255, 255, 255, 0.08); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.15);')}">
            ${simState.votacaoEncerrada ? '✓ Encerrada' : (simState.votacaoAberta ? '● Aberta no App' : 'Fechada')}
          </span>
        </div>

        <div id="simAreaBotoesVotacao" style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.25rem;">
          ${!simState.votacaoAberta ? `
            <button type="button" class="sim-btn-action-primary" id="btnSimAbrirVotacao" style="justify-content: center;">
              ${SVG_ICONS.votacao}
              <span>Abrir Votação no App</span>
            </button>
          ` : (!simState.votacaoEncerrada ? `
            <button type="button" class="sim-team-btn" id="btnSimEncerrarVotacao" style="background: rgba(234, 179, 8, 0.12); border-color: rgba(234, 179, 8, 0.35); color: #fde047; justify-content: center; gap: 0.4rem;">
              <span>Encerrar Votação e Salvar Pontos</span>
            </button>
          ` : `
            <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 8px; padding: 0.45rem 0.8rem; font-size: 0.78rem; color: #4ade80; font-weight: 750; text-align: center;">
              ✓ Votos computados no Ranking!
            </div>
          `)}
        </div>
      </div>
    `;

    // Interações de abrir / encerrar votação
    const btnAbrir = document.getElementById('btnSimAbrirVotacao');
    if (btnAbrir) {
      btnAbrir.addEventListener('click', () => {
        simState.votacaoAberta = true;
        renderEtapa6_Votacao();
      });
    }

    const btnEncerrar = document.getElementById('btnSimEncerrarVotacao');
    if (btnEncerrar) {
      btnEncerrar.addEventListener('click', () => {
        simState.votacaoEncerrada = true;
        renderEtapa6_Votacao();
      });
    }

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa5">
        ← Voltar
      </button>
      <button type="button" class="sim-btn-action-primary ${simState.votacaoEncerrada ? 'is-lit' : 'is-dimmed'}" id="btnAvancarParaHistorico" style="padding: 0.45rem 1rem; font-size: 0.84rem;">
        <span>Avançar para o Histórico</span>
        ${SVG_ICONS.arrowRight}
      </button>
    `;

    document.getElementById('btnVoltarEtapa5').addEventListener('click', () => {
      renderEtapa5_Resultados();
    });

    document.getElementById('btnAvancarParaHistorico').addEventListener('click', () => {
      renderEtapa7_Historico();
    });
  }

  // ==========================================
  // ETAPA 7: Exemplo Prático do Histórico de Partidas
  // ==========================================
  function renderEtapa7_Historico() {
    atualizarIndicador(6, 'tourJuizTabHistorico');

    const time1Venceu = simState.golsTime1 >= simState.golsTime2;
    const timeCampeao = (simState.teams && simState.teams.length >= 2)
      ? (time1Venceu ? simState.teams[0] : simState.teams[1])
      : {
          nome: 'Time 1 (Verde)',
          corClass: 'team-verde',
          jogadores: [
            { nome: 'Gabriel Costa', posicao: 'goleiro' },
            { nome: 'Lucas Silva', posicao: 'linha' },
            { nome: 'Rafael Souza', posicao: 'linha' },
            { nome: 'Pedro Alves', posicao: 'linha' },
            { nome: 'Gustavo Henrique', posicao: 'linha' }
          ]
        };

    const jogadoresCampeoes = (timeCampeao.jogadores && timeCampeao.jogadores.length > 0)
      ? timeCampeao.jogadores
      : [
          { nome: 'Gabriel Costa', posicao: 'goleiro' },
          { nome: 'Lucas Silva', posicao: 'linha' },
          { nome: 'Rafael Souza', posicao: 'linha' },
          { nome: 'Pedro Alves', posicao: 'linha' },
          { nome: 'Gustavo Henrique', posicao: 'linha' }
        ];

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div style="margin-bottom: 0.5rem;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 850; color: #ffffff;">Exemplo no Histórico</h3>
      </div>

      <div class="sim-history-demo-card">
        <div class="sim-history-demo-header">
          <div>
            <span class="sim-history-demo-kicker">Partida #14 • Terça-feira, 20:30</span>
            <div style="display: flex; gap: 0.35rem; margin-top: 0.2rem;">
              <span style="font-size: 0.72rem; color: #cbd5e1; background: rgba(255, 255, 255, 0.06); padding: 0.15rem 0.45rem; border-radius: 999px;">10 jogadores</span>
              <span style="font-size: 0.72rem; color: #cbd5e1; background: rgba(255, 255, 255, 0.06); padding: 0.15rem 0.45rem; border-radius: 999px;">2 times</span>
            </div>
          </div>
          <span class="sim-history-status-badge">🏆 Encerrada</span>
        </div>

        <div class="sim-history-scoreboard">
          <div class="sim-history-team">
            <span style="font-size: 0.82rem; font-weight: 800; color: #22c55e;">Time 1 (Verde)</span>
            <span class="sim-history-score">${simState.golsTime1}</span>
          </div>
          <span class="sim-history-divider">×</span>
          <div class="sim-history-team text-right">
            <span class="sim-history-score">${simState.golsTime2}</span>
            <span style="font-size: 0.82rem; font-weight: 800; color: #38bdf8;">Time 2 (Azul)</span>
          </div>
        </div>

        <div class="sim-history-champion-box">
          <div class="sim-history-pill" style="border-left: 3px solid #eab308; background: rgba(234, 179, 8, 0.08); padding: 0.45rem 0.65rem;">
            <span style="color: #fde047; font-weight: 850; display: flex; align-items: center; gap: 0.35rem;">
              🏆 Time Campeão:
            </span>
            <strong style="color: ${time1Venceu ? '#22c55e' : '#38bdf8'}; font-weight: 850; font-size: 0.88rem;">
              ${timeCampeao.nome}
            </strong>
          </div>

          <div class="sim-history-champion-players">
            ${jogadoresCampeoes.map(j => `
              <span class="sim-champion-player-tag">
                ${j.posicao === 'goleiro' ? '🧤' : '⚽'} ${j.nome}
              </span>
            `).join('')}
          </div>
        </div>

        <div style="font-size: 0.76rem; color: #4ade80; background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 8px; padding: 0.35rem 0.65rem; text-align: center; font-weight: 600;">
          Alimenta automaticamente o Ranking Oficial da Temporada!
        </div>
      </div>
    `;

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa6">
        ← Voltar
      </button>
      <button type="button" class="sim-btn-action-primary" id="btnAvancarCronometro" style="padding: 0.45rem 1rem; font-size: 0.84rem;">
        <span>Avançar para Cronômetro</span>
        ${SVG_ICONS.arrowRight}
      </button>
    `;

    document.getElementById('btnVoltarEtapa6').addEventListener('click', () => {
      renderEtapa6_Votacao();
    });

    document.getElementById('btnAvancarCronometro').addEventListener('click', () => {
      renderEtapa8_Cronometro();
    });
  }

  // ==========================================
  // ETAPA 8: Cronômetro Oficial da Partida (Testável)
  // ==========================================
  function renderEtapa8_Cronometro() {
    atualizarIndicador(7, 'tourJuizTabCronometro');

    const formatTimer = (totalSec) => {
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    };

    const container = document.getElementById('simDynamicContainer');
    container.innerHTML = `
      <div style="margin-bottom: 0.5rem;">
        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 850; color: #ffffff;">Cronômetro da Partida</h3>
      </div>

      <div class="sim-timer-box">
        <div class="sim-timer-display ${simState.timerSeconds === 0 ? 'is-finished' : ''}" id="simTimerDisplay">
          ${formatTimer(simState.timerSeconds)}
        </div>

        <div class="sim-timer-presets">
          <button type="button" class="sim-timer-preset-btn ${simState.timerSeconds === 300 ? 'is-active' : ''}" data-sec="300">5 min</button>
          <button type="button" class="sim-timer-preset-btn ${simState.timerSeconds === 480 ? 'is-active' : ''}" data-sec="480">8 min</button>
          <button type="button" class="sim-timer-preset-btn ${simState.timerSeconds === 600 ? 'is-active' : ''}" data-sec="600">10 min</button>
        </div>

        <div class="sim-timer-controls">
          <button type="button" class="sim-btn-compact-secondary" id="btnTimerMinus" style="padding: 0.4rem 0.75rem;">-1 min</button>
          <button type="button" class="sim-btn-action-primary" id="btnTimerToggle" style="padding: 0.45rem 1.25rem;">
            ${simState.timerRunning ? 'Pausar' : 'Iniciar'}
          </button>
          <button type="button" class="sim-btn-compact-secondary" id="btnTimerPlus" style="padding: 0.4rem 0.75rem;">+1 min</button>
          <button type="button" class="sim-btn-compact-secondary" id="btnTimerReset" style="padding: 0.4rem 0.75rem; color: #ef4444; border-color: rgba(239, 68, 68, 0.3);">Resetar</button>
        </div>
      </div>
    `;

    const displayEl = document.getElementById('simTimerDisplay');
    const toggleBtn = document.getElementById('btnTimerToggle');

    const updateDisplay = () => {
      if (displayEl) {
        displayEl.textContent = formatTimer(simState.timerSeconds);
        displayEl.classList.toggle('is-finished', simState.timerSeconds === 0);
      }
      if (toggleBtn) {
        toggleBtn.textContent = simState.timerRunning ? 'Pausar' : 'Iniciar';
      }
    };

    // Presets
    container.querySelectorAll('.sim-timer-preset-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const sec = parseInt(this.getAttribute('data-sec'), 10);
        simState.timerSeconds = sec;
        if (simState.timerRunning) {
          clearInterval(simState.timerInterval);
          simState.timerRunning = false;
        }
        renderEtapa8_Cronometro();
      });
    });

    // Iniciar / Pausar
    toggleBtn.addEventListener('click', () => {
      if (simState.timerRunning) {
        clearInterval(simState.timerInterval);
        simState.timerInterval = null;
        simState.timerRunning = false;
        updateDisplay();
      } else {
        if (simState.timerSeconds <= 0) simState.timerSeconds = 600;
        simState.timerRunning = true;
        updateDisplay();
        simState.timerInterval = setInterval(() => {
          if (simState.timerSeconds > 0) {
            simState.timerSeconds--;
            updateDisplay();
          } else {
            clearInterval(simState.timerInterval);
            simState.timerInterval = null;
            simState.timerRunning = false;
            updateDisplay();
          }
        }, 1000);
      }
    });

    // -1 min
    document.getElementById('btnTimerMinus').addEventListener('click', () => {
      simState.timerSeconds = Math.max(0, simState.timerSeconds - 60);
      updateDisplay();
    });

    // +1 min
    document.getElementById('btnTimerPlus').addEventListener('click', () => {
      simState.timerSeconds += 60;
      updateDisplay();
    });

    // Resetar
    document.getElementById('btnTimerReset').addEventListener('click', () => {
      if (simState.timerInterval) {
        clearInterval(simState.timerInterval);
        simState.timerInterval = null;
      }
      simState.timerRunning = false;
      simState.timerSeconds = 600;
      renderEtapa8_Cronometro();
    });

    document.getElementById('simFooterActions').innerHTML = `
      <button type="button" class="sim-btn-action-secondary" id="btnVoltarEtapa7">
        ← Voltar
      </button>
      <button type="button" class="sim-btn-action-primary" id="btnConcluirTour" style="padding: 0.5rem 1.2rem; font-size: 0.88rem;">
        <span>Concluir Tour</span>
        ${SVG_ICONS.check}
      </button>
    `;

    document.getElementById('btnVoltarEtapa7').addEventListener('click', () => {
      if (simState.timerInterval) { clearInterval(simState.timerInterval); simState.timerInterval = null; simState.timerRunning = false; }
      renderEtapa7_Historico();
    });

    document.getElementById('btnConcluirTour').addEventListener('click', () => {
      if (simState.timerInterval) { clearInterval(simState.timerInterval); simState.timerInterval = null; simState.timerRunning = false; }
      encerrarJuizTour();
    });
  }

  function ligarEventosAbas() {
    const mapaAbas = [
      { id: 'tourJuizTabCriar', fn: () => renderEtapa1_Inicio() },
      { id: 'tourJuizTabTimes', fn: () => {
        if (!simState.teams || simState.teams.length === 0) {
          preencherJogadoresFicticiosPadrao();
          gerarTimesSimulados();
        }
        renderEtapa4_Times();
      }},
      { id: 'tourJuizTabVotacoes', fn: () => renderEtapa6_Votacao() },
      { id: 'tourJuizTabHistorico', fn: () => renderEtapa7_Historico() },
      { id: 'tourJuizTabCronometro', fn: () => renderEtapa8_Cronometro() },
      { id: 'tourJuizTabSair', fn: () => renderEtapaSair() }
    ];

    mapaAbas.forEach(aba => {
      const el = document.getElementById(aba.id);
      if (el) {
        el._juizTourHandler = function (e) {
          if (!document.body.classList.contains('juiz-tour-active')) return;
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          aba.fn();
        };
        el.addEventListener('click', el._juizTourHandler, true);
        el.addEventListener('touchend', el._juizTourHandler, { capture: true, passive: false });
      }
    });
  }

  function desligarEventosAbas() {
    ['tourJuizTabCriar', 'tourJuizTabTimes', 'tourJuizTabVotacoes', 'tourJuizTabHistorico', 'tourJuizTabCronometro', 'tourJuizTabSair'].forEach(id => {
      const el = document.getElementById(id);
      if (el && el._juizTourHandler) {
        el.removeEventListener('click', el._juizTourHandler, true);
        el.removeEventListener('touchend', el._juizTourHandler, true);
        delete el._juizTourHandler;
      }
    });
  }

  function interceptarCliqueAbas(e) {
    if (!document.body.classList.contains('juiz-tour-active')) return;

    // Permite interações normais dentro do card do tour
    if (e.target.closest('#juizTourCard')) return;

    // Se clicou em uma aba do rodapé do juiz (ou botão de sair)
    const tabLink = e.target.closest('.site-footer__link');
    if (tabLink) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();

      const id = tabLink.id;
      if (id === 'tourJuizTabCriar') {
        renderEtapa1_Inicio();
      } else if (id === 'tourJuizTabTimes') {
        if (!simState.teams || simState.teams.length === 0) {
          preencherJogadoresFicticiosPadrao();
          gerarTimesSimulados();
        }
        renderEtapa4_Times();
      } else if (id === 'tourJuizTabVotacoes') {
        renderEtapa6_Votacao();
      } else if (id === 'tourJuizTabHistorico') {
        renderEtapa7_Historico();
      } else if (id === 'tourJuizTabCronometro') {
        renderEtapa8_Cronometro();
      } else if (id === 'tourJuizTabSair') {
        renderEtapaSair();
      }
      return;
    }

    // Impede fechar ao clicar no backdrop ou em outros links externos
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
  }

  function encerrarJuizTour() {
    if (simState.timerInterval) {
      clearInterval(simState.timerInterval);
      simState.timerInterval = null;
    }
    simState.timerRunning = false;

    try {
      localStorage.setItem(obterChaveStorage(), 'true');
    } catch (e) {}

    window.removeEventListener('click', interceptarCliqueAbas, true);
    document.removeEventListener('click', interceptarCliqueAbas, true);
    window.removeEventListener('touchend', interceptarCliqueAbas, true);
    desligarEventosAbas();

    document.body.classList.remove('juiz-tour-active');
    document.querySelectorAll('.tour-highlight-tab').forEach(el => el.classList.remove('tour-highlight-tab'));

    // Restaura a aba ativa original
    if (originalActiveTab && document.getElementById(originalActiveTab.id)) {
      document.getElementById(originalActiveTab.id).classList.add('is-active');
    } else {
      const tabCriar = document.getElementById('tourJuizTabCriar');
      if (tabCriar) tabCriar.classList.add('is-active');
    }

    if (overlayEl) {
      overlayEl.classList.remove('is-active');
      setTimeout(() => {
        if (overlayEl && overlayEl.parentNode) {
          overlayEl.parentNode.removeChild(overlayEl);
        }
        overlayEl = null;
      }, 220);
    }
  }

  window.iniciarJuizTour = function (force = false) {
    if (!force) {
      try {
        if (localStorage.getItem(obterChaveStorage()) === 'true') {
          return;
        }
      } catch (e) {}
    }

    // Salva a aba ativa original e limpa estado is-active das abas
    originalActiveTab = document.querySelector('.site-footer__link.is-active');
    document.querySelectorAll('.site-footer__link').forEach(el => el.classList.remove('is-active'));

    // Reseta estado da simulação
    simState = {
      step: 0,
      targetQty: null,
      selectedPlayerIds: new Set(),
      teams: [],
      swappingPlayer: null,
      isEditingTeams: false,
      golsTime1: 3,
      golsTime2: 2,
      votacaoAberta: false,
      votacaoEncerrada: false,
      partidaEncerrada: false,
      timerSeconds: 600,
      timerRunning: false,
      timerInterval: null
    };

    overlayEl = criarEstruturaTour();
    document.body.classList.add('juiz-tour-active');

    window.addEventListener('click', interceptarCliqueAbas, true);
    document.addEventListener('click', interceptarCliqueAbas, true);
    window.addEventListener('touchend', interceptarCliqueAbas, { capture: true, passive: false });
    ligarEventosAbas();

    setTimeout(() => {
      overlayEl.classList.add('is-active');
      renderEtapa1_Inicio();
    }, 40);
  };

  function autoInit() {
    const isJuizHome = window.location.pathname.startsWith('/jogar') || 
                       document.querySelector('.judge-workspace-page') !== null ||
                       document.querySelector('.judge-site-footer') !== null;
    if (!isJuizHome) return;

    const urlParams = new URLSearchParams(window.location.search);
    const temParamTour = urlParams.get('tour') === '1' || urlParams.get('onboarding') === '1';

    try {
      const jaViu = localStorage.getItem(obterChaveStorage()) === 'true';
      if (!jaViu || temParamTour) {
        setTimeout(() => {
          window.iniciarJuizTour(temParamTour);
        }, 600);
      }
    } catch (e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }
})();
