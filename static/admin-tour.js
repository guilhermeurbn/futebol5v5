/**
 * Admin Onboarding Tour - NaTrave 5v5
 * Apresentação guiada, centralizada e com ícones vetoriais SVG (sem emojis).
 */

(function () {
  'use strict';

  const SVG_ICONS = {
    jogadores: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    historico: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>`,
    ranking: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v6a5 5 0 0 1-10 0V4Z"/><path d="M18 5h3v2a3 3 0 0 1-3 3"/><path d="M6 5H3v2a3 3 0 0 0 3 3"/></svg>`,
    perfil: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M6 21v-2a6 6 0 0 1 12 0v2"/></svg>`,
    ajustes: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
    lampada: `<svg viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-7 7c0 2.5 1.5 4.7 3.5 6h7c2-1.3 3.5-3.5 3.5-6a7 7 0 0 0-7-7z"/></svg>`,
    check: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`
  };

  const TOUR_STEPS = [
    {
      tabId: 'tourTabJogadores',
      svgIcon: SVG_ICONS.jogadores,
      title: 'Jogadores do Clube',
      description: 'Gestão completa do elenco. Adicione atletas, defina notas iniciais e posições para partidas equilibradas.',
      example: '<strong>Como funciona:</strong> O algoritmo utiliza a nota dos atletas para sortear times nivelados e competitivos em segundos.'
    },
    {
      tabId: 'tourTabHistorico',
      svgIcon: SVG_ICONS.historico,
      title: 'Histórico de Partidas',
      description: 'Arquivo oficial dos confrontos realizados. Registra placares, duelos e a escalação de cada equipe.',
      example: '<strong>Como funciona:</strong> Cada jogo encerrado pelo juiz gera uma súmula detalhada com gols, artilharia e pontuação.'
    },
    {
      tabId: 'tourTabRanking',
      svgIcon: SVG_ICONS.ranking,
      title: 'Ranking da Temporada',
      description: 'Tabela de classificação calculada automaticamente a partir das vitórias, gols e aproveitamento dos atletas.',
      example: '<strong>Como funciona:</strong> Acompanhe quem lidera a temporada, os artilheiros da rodada e a taxa de vitórias (%) de cada um.'
    },
    {
      tabId: 'tourTabPerfil',
      svgIcon: SVG_ICONS.perfil,
      title: 'Perfil do Administrador',
      description: 'Área da sua conta de Admin. Gerencie suas credenciais de acesso, segurança e preferências no NaTrave.',
      example: '<strong>Como funciona:</strong> Altere sua senha com facilidade e configure sua identificação única no clube.'
    },
    {
      tabId: 'tourTabAjustes',
      svgIcon: SVG_ICONS.ajustes,
      title: 'Ajustes do Administrador',
      description: 'Painel de controle exclusivo do clube para gerenciar acessos, regras, juízes e identidade visual.',
      example: '<strong>Como funciona:</strong> Altere o código/PIN de convite, consulte a senha do juiz ou personalize o escudo e cores do clube.'
    }
  ];

  let currentStep = 0;
  let overlayEl = null;
  let originalActiveTab = null;

  function obterChaveStorage() {
    const cod = window.CLUBE_CODIGO || (document.body ? document.body.getAttribute('data-clube-codigo') : '') || '001';
    return `natrave_admin_tour_completed_${cod}`;
  }

  function criarEstruturaTour() {
    if (document.getElementById('adminTourOverlay')) {
      return document.getElementById('adminTourOverlay');
    }

    const overlay = document.createElement('div');
    overlay.id = 'adminTourOverlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Tour de Apresentação das Abas do Clube');

    overlay.innerHTML = `
      <div id="adminTourCard">
        <div class="tour-card-header">
          <div class="tour-step-pill" id="tourStepIndicator">PASSO 1 DE 5</div>
          <button type="button" class="tour-btn-skip" id="btnSkipTour" aria-label="Pular Tour">
            <span>Pular</span>
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="tour-title-wrap">
          <div class="tour-icon-box" id="tourIconBox"></div>
          <h3 class="tour-title" id="tourTitle">Jogadores</h3>
        </div>

        <p class="tour-desc" id="tourDesc"></p>

        <div class="tour-example-box">
          <div class="tour-example-icon">${SVG_ICONS.lampada}</div>
          <p class="tour-example-text" id="tourExample"></p>
        </div>

        <div class="tour-card-footer">
          <div class="tour-dots-wrap" id="tourDotsWrap">
            ${TOUR_STEPS.map((_, i) => `<div class="tour-dot ${i === 0 ? 'is-active' : ''}" data-step="${i}"></div>`).join('')}
          </div>
          <div class="tour-actions-wrap">
            <button type="button" class="tour-btn-prev" id="btnPrevTour" aria-label="Voltar etapa" title="Voltar" style="display: none;">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </button>
            <button type="button" class="tour-btn-next" id="btnNextTour">
              <span id="btnNextTourText">Próximo</span>
              <span id="btnNextTourIcon" style="display: inline-flex; align-items: center;">
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </span>
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('btnSkipTour').addEventListener('click', encerrarAdminTour);
    document.getElementById('btnPrevTour').addEventListener('click', passoAnterior);
    document.getElementById('btnNextTour').addEventListener('click', proximoPasso);

    // Permite clicar nos dots para navegar diretamente ao tópico
    document.querySelectorAll('#tourDotsWrap .tour-dot').forEach((dot) => {
      dot.addEventListener('click', function () {
        const stepIdx = parseInt(this.getAttribute('data-step'), 10);
        if (!isNaN(stepIdx)) {
          renderizarPasso(stepIdx);
        }
      });
    });

    return overlay;
  }

  function renderizarPasso(index) {
    if (index < 0 || index >= TOUR_STEPS.length) return;
    currentStep = index;
    const step = TOUR_STEPS[index];

    // Atualiza indicadores do card
    document.getElementById('tourStepIndicator').textContent = `PASSO ${index + 1} DE ${TOUR_STEPS.length}`;
    document.getElementById('tourIconBox').innerHTML = step.svgIcon;
    document.getElementById('tourTitle').textContent = step.title;
    document.getElementById('tourDesc').textContent = step.description;
    document.getElementById('tourExample').innerHTML = step.example;

    // Atualiza dots
    const dots = document.querySelectorAll('#tourDotsWrap .tour-dot');
    dots.forEach((dot, i) => {
      dot.classList.toggle('is-active', i === index);
    });

    // Botão Voltar (Seta esquerda)
    const btnPrev = document.getElementById('btnPrevTour');
    btnPrev.style.display = index > 0 ? 'inline-flex' : 'none';

    // Botão Próximo / Concluir
    const btnNextText = document.getElementById('btnNextTourText');
    const btnNextIcon = document.getElementById('btnNextTourIcon');
    if (index === TOUR_STEPS.length - 1) {
      btnNextText.textContent = 'Concluir';
      btnNextIcon.innerHTML = SVG_ICONS.check;
    } else {
      btnNextText.textContent = 'Próximo';
      btnNextIcon.innerHTML = `
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      `;
    }

    // Gerencia o destaque iluminado na aba ativa: remove de todas
    document.querySelectorAll('.tour-highlight-tab').forEach(el => el.classList.remove('tour-highlight-tab'));
    
    // Garante que NENHUMA aba fique com classe is-active enquanto o tour estiver em execução
    document.querySelectorAll('.site-footer__link').forEach(el => el.classList.remove('is-active'));

    const targetTab = document.getElementById(step.tabId);
    if (targetTab) {
      targetTab.classList.add('tour-highlight-tab');
      try {
        targetTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      } catch (e) {}
    }
  }

  function proximoPasso() {
    if (currentStep < TOUR_STEPS.length - 1) {
      renderizarPasso(currentStep + 1);
    } else {
      encerrarAdminTour();
    }
  }

  function passoAnterior() {
    if (currentStep > 0) {
      renderizarPasso(currentStep - 1);
    }
  }

  function ligarEventosAbas() {
    TOUR_STEPS.forEach((step, idx) => {
      const el = document.getElementById(step.tabId);
      if (el) {
        el._tourHandler = function (e) {
          if (!document.body.classList.contains('admin-tour-active')) return;
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          renderizarPasso(idx);
        };
        el.addEventListener('click', el._tourHandler, true);
        el.addEventListener('touchend', el._tourHandler, { capture: true, passive: false });
      }
    });
  }

  function desligarEventosAbas() {
    TOUR_STEPS.forEach((step) => {
      const el = document.getElementById(step.tabId);
      if (el && el._tourHandler) {
        el.removeEventListener('click', el._tourHandler, true);
        el.removeEventListener('touchend', el._tourHandler, true);
        delete el._tourHandler;
      }
    });
  }

  function interceptarCliqueAbas(e) {
    if (!document.body.classList.contains('admin-tour-active')) return;

    // Cliques dentro do card (Próximo, Voltar, Pular, Dots) funcionam normalmente
    if (e.target.closest('#adminTourCard')) return;

    // Se clicou em uma aba do rodapé, muda a explicação diretamente para ela (não navega como link)
    const tabLink = e.target.closest('.site-footer__link');
    if (tabLink) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();

      const stepIndex = TOUR_STEPS.findIndex(s => s.tabId === tabLink.id);
      if (stepIndex !== -1) {
        renderizarPasso(stepIndex);
      }
      return;
    }

    // Se clicou fora do card ou no backdrop, impede fechar o tour e bloqueia ações externas
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
  }

  function encerrarAdminTour() {
    try {
      localStorage.setItem(obterChaveStorage(), '1');
    } catch (e) {}

    // Remove destaque do tour
    document.querySelectorAll('.tour-highlight-tab').forEach(el => el.classList.remove('tour-highlight-tab'));
    document.body.classList.remove('admin-tour-active');

    // Restaura a aba ativa original (ex: Jogadores na home)
    if (originalActiveTab && document.getElementById(originalActiveTab.id)) {
      document.getElementById(originalActiveTab.id).classList.add('is-active');
    } else {
      const tabJog = document.getElementById('tourTabJogadores');
      if (tabJog) tabJog.classList.add('is-active');
    }

    if (overlayEl) {
      overlayEl.classList.remove('is-active');
      setTimeout(() => {
        if (overlayEl && overlayEl.parentNode) {
          overlayEl.parentNode.removeChild(overlayEl);
          overlayEl = null;
        }
      }, 300);
    }

    window.removeEventListener('click', interceptarCliqueAbas, true);
    document.removeEventListener('click', interceptarCliqueAbas, true);
    desligarEventosAbas();
    document.removeEventListener('keydown', lidarTeclado);
  }

  function lidarTeclado(e) {
    if (e.key === 'Escape') {
      encerrarAdminTour();
    } else if (e.key === 'ArrowRight') {
      proximoPasso();
    } else if (e.key === 'ArrowLeft') {
      passoAnterior();
    }
  }

  window.iniciarAdminTour = function (force = false) {
    if (!force) {
      try {
        const jaVisto = localStorage.getItem(obterChaveStorage());
        if (jaVisto) return;
      } catch (e) {}
    }

    // Salva qual aba estava originalmente ativa para restaurar ao fechar
    const currentlyActive = document.querySelector('.site-footer__link.is-active');
    if (currentlyActive) {
      originalActiveTab = { id: currentlyActive.id };
    }

    overlayEl = criarEstruturaTour();
    document.body.classList.add('admin-tour-active');

    requestAnimationFrame(() => {
      overlayEl.classList.add('is-active');
      renderizarPasso(0);
    });

    ligarEventosAbas();
    window.addEventListener('click', interceptarCliqueAbas, true);
    document.addEventListener('click', interceptarCliqueAbas, true);
    document.addEventListener('keydown', lidarTeclado);
  };

  // Inicialização automática para administradores no modo boas-vindas
  document.addEventListener('DOMContentLoaded', function () {
    const urlParams = new URLSearchParams(window.location.search);
    const temParamBoasVindas = urlParams.get('boas_vindas') === '1';
    const hasAdminWelcomeCard = !!document.getElementById('adminWelcomeHub');

    if (temParamBoasVindas || hasAdminWelcomeCard) {
      setTimeout(() => {
        window.iniciarAdminTour(temParamBoasVindas);
      }, 450);
    }
  });

})();
