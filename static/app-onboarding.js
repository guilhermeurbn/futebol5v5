/**
 * NATRAVE 5v5 - CONTROLLER DE ONBOARDING & MODO APP
 * Gerencia o layout unificado do aplicativo e os controles de onboarding (Cards explicativos).
 */
document.addEventListener('DOMContentLoaded', () => {
  // Garantir que a página de login/auth permaneça sempre no Modo Aplicativo (Posição Única)
  document.body.classList.add('is-capacitor-app');

  const onboardingModal = document.getElementById('app-onboarding-modal');
  const loginFormContainer = document.getElementById('app-login-container');
  const onboardingKey = 'natrave_app_onboarding_completed_v1';

  // Sempre apresentar a introdução para quem chega deslogado à tela de login
  // Omitir apenas se houver mensagem recente de erro/sucesso (ex: senha incorreta) ou se explicitamente fechado
  const urlParams = new URLSearchParams(window.location.search);
  const forceShowOnboarding = urlParams.get('onboarding') === '1' || urlParams.get('show_onboarding') === '1';
  const hasAuthAlert = Boolean(document.querySelector('.auth-message--warning, .auth-message--success'));

  const loginFormPanel = document.getElementById('loginFormPanel') || document.querySelector('.auth-panel--form') || document.getElementById('authCardFlip');

  // Isolamento de Parte 1 (Apresentação) x Parte 2 (Login):
  // Desativa completamente campos de input enquanto o modal de apresentação estiver aberto.
  // Isso impede que o teclado ou sugestões nativas do Keychain/Celular surjam durante o onboarding.
  function disableLoginInputs() {
    if (loginFormPanel) {
      loginFormPanel.setAttribute('inert', '');
    }
    const elements = document.querySelectorAll('.auth-card-flip-container input, .auth-card-flip-container button, .auth-panel--form input, .auth-panel--form button');
    elements.forEach(el => {
      if (el.closest('#app-onboarding-modal')) return;
      el.setAttribute('disabled', 'disabled');
      el.setAttribute('tabindex', '-1');
      el.dataset.onboardingDisabled = 'true';
    });
  }

  function enableLoginInputs() {
    if (loginFormPanel) {
      loginFormPanel.removeAttribute('inert');
    }
    const elements = document.querySelectorAll('.auth-card-flip-container input, .auth-card-flip-container button, .auth-panel--form input, .auth-panel--form button');
    elements.forEach(el => {
      if (el.closest('#app-onboarding-modal')) return;
      if (el.dataset.onboardingDisabled === 'true') {
        el.removeAttribute('disabled');
        el.removeAttribute('tabindex');
        delete el.dataset.onboardingDisabled;
      }
    });
  }

  if (onboardingModal) {
    if (hasAuthAlert && !forceShowOnboarding) {
      onboardingModal.classList.add('is-hidden');
      onboardingModal.style.setProperty('display', 'none', 'important');
      if (loginFormContainer) {
        loginFormContainer.classList.add('onboarding-done');
      }
      enableLoginInputs();
    } else {
      onboardingModal.classList.remove('is-hidden', 'fade-out');
      onboardingModal.style.display = 'block';
      disableLoginInputs();
    }
  } else {
    enableLoginInputs();
  }

  // Reabertura manual do Onboarding
  document.querySelectorAll('.js-open-onboarding').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      if (onboardingModal) {
        disableLoginInputs();
        onboardingModal.classList.remove('is-hidden', 'fade-out');
        onboardingModal.style.display = 'block';
        updateCard(0);
      }
    });
  });

  if (!onboardingModal) return;

  let currentCard = 0;
  const cards = Array.from(onboardingModal.querySelectorAll('.onboarding-card'));
  const dots = Array.from(onboardingModal.querySelectorAll('.onboarding-dot'));
  const btnNext = document.getElementById('onboarding-btn-next');
  const btnPrev = document.getElementById('onboarding-btn-prev');
  const btnSkip = document.getElementById('onboarding-btn-skip');

  function triggerHaptic() {
    try {
      if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
        window.Capacitor.Plugins.Haptics.impact({ style: 'LIGHT' });
      }
    } catch (e) { }
  }

  function updateCard(index) {
    if (index < 0) index = 0;
    if (index >= cards.length) index = cards.length - 1;
    currentCard = index;

    cards.forEach((card, i) => {
      card.classList.toggle('active', i === index);
    });
    dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });

    // Controla visibilidade do botão Voltar (Invisível no Slide 0)
    if (btnPrev) {
      if (index > 0) {
        btnPrev.style.display = 'inline-flex';
        btnPrev.style.visibility = 'visible';
        btnPrev.style.pointerEvents = 'auto';
      } else {
        btnPrev.style.display = 'none';
        btnPrev.style.visibility = 'hidden';
        btnPrev.style.pointerEvents = 'none';
      }
    }

    // Botão Avançar / Começar
    if (btnNext) {
      const isLast = index === cards.length - 1;
      const btnSpan = btnNext.querySelector('span');
      if (btnSpan) {
        btnSpan.textContent = isLast ? 'Começar' : 'Avançar';
      } else {
        btnNext.textContent = isLast ? 'Começar' : 'Avançar';
      }
    }
  }

  function completeOnboarding() {
    triggerHaptic();
    try {
      localStorage.setItem(onboardingKey, 'true');
    } catch (e) { }

    // Grava o cookie persistente por 1 ano (365 dias)
    document.cookie = 'natrave_onboarding_seen=1; path=/; max-age=31536000; SameSite=Lax';

    // Habilita a área de login apenas após sair da apresentação
    enableLoginInputs();

    if (onboardingModal) {
      onboardingModal.classList.add('fade-out', 'is-hidden');
      onboardingModal.style.setProperty('display', 'none', 'important');
    }
    if (loginFormContainer) {
      loginFormContainer.classList.add('onboarding-done');
    }
  }

  // Escutador global para garantir clique no botão Pular (mesmo se houver overlays)
  document.addEventListener('click', (e) => {
    const skipTarget = e.target && e.target.closest ? e.target.closest('#onboarding-btn-skip, .onboarding-skip-top-btn, [data-action="skip-onboarding"]') : null;
    if (skipTarget) {
      e.preventDefault();
      e.stopPropagation();
      completeOnboarding();
    }
  }, true);

  if (btnNext) {
    btnNext.addEventListener('click', (e) => {
      e.preventDefault();
      triggerHaptic();
      if (currentCard < cards.length - 1) {
        updateCard(currentCard + 1);
      } else {
        completeOnboarding();
      }
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', (e) => {
      e.preventDefault();
      triggerHaptic();
      if (currentCard > 0) {
        updateCard(currentCard - 1);
      }
    });
  }

  if (btnSkip) {
    btnSkip.addEventListener('click', (e) => {
      e.preventDefault();
      completeOnboarding();
    });
  }

  // Suporte a clique direto nos Dots de paginação
  dots.forEach((dot, index) => {
    dot.addEventListener('click', (e) => {
      e.preventDefault();
      triggerHaptic();
      updateCard(index);
    });
  });

  // Gestos de Touch Swipe nos cards do Onboarding
  const slidesContainer = onboardingModal.querySelector('.onboarding-slides-container');
  if (slidesContainer) {
    let startX = 0;
    let startY = 0;

    slidesContainer.addEventListener('touchstart', (e) => {
      if (e.touches && e.touches.length > 0) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    }, { passive: true });

    slidesContainer.addEventListener('touchend', (e) => {
      if (!e.changedTouches || e.changedTouches.length === 0) return;
      const deltaX = e.changedTouches[0].clientX - startX;
      const deltaY = e.changedTouches[0].clientY - startY;

      // Garantir que é um gesto predominantemente horizontal
      if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY)) {
        triggerHaptic();
        if (deltaX < 0) {
          // Swipe para a esquerda (Avançar)
          if (currentCard < cards.length - 1) {
            updateCard(currentCard + 1);
          } else {
            completeOnboarding();
          }
        } else {
          // Swipe para a direita (Voltar)
          if (currentCard > 0) {
            updateCard(currentCard - 1);
          }
        }
      }
    }, { passive: true });
  }

  // Previne zoom por duplo toque em qualquer lugar do aplicativo no iPhone
  let lastTap = 0;
  document.addEventListener('touchend', (e) => {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) {
      return;
    }
    const currentTime = new Date().getTime();
    const tapLength = currentTime - lastTap;
    if (tapLength < 300 && tapLength > 0) {
      e.preventDefault();
    }
    lastTap = currentTime;
  }, { passive: false });

  // Persistência do "Lembrar de Mim"
  const loginForm = document.querySelector('form[action*="login_submit"]') || document.querySelector('.auth-form');
  const usernameInput = document.getElementById('username');
  const rememberCheckbox = document.querySelector('input[name="remember_me"]');

  if (loginForm && usernameInput) {
    try {
      const savedUser = localStorage.getItem('natrave_remember_username');
      if (savedUser) {
        usernameInput.value = savedUser;
        if (rememberCheckbox) {
          rememberCheckbox.checked = true;
        }
      }
    } catch (e) { }

    loginForm.addEventListener('submit', () => {
      try {
        if (rememberCheckbox && rememberCheckbox.checked) {
          localStorage.setItem('natrave_remember_username', usernameInput.value.trim());
        } else {
          localStorage.removeItem('natrave_remember_username');
        }
      } catch (e) { }
    });
  }

  // Animação 3D Flip do Card (Login x Cadastro x Recuperar Senha x Entrar Clube x Criar Clube)
  const cardFlipInner = document.getElementById('authCardFlipInner');
  const btnShowRegister = document.getElementById('btn-show-register');
  const btnShowLogin = document.getElementById('btn-show-login');
  const btnShowForgot = document.getElementById('btn-show-forgot') || document.querySelector('.auth-forgot-link');
  const btnForgotBack = document.getElementById('btn-forgot-back');
  const btnShowJoinClub = document.getElementById('btn-show-join-club');
  const btnShowCreateClub = document.getElementById('btn-show-create-club');

  if (cardFlipInner) {
    if (btnShowRegister) {
      btnShowRegister.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped-forgot', 'is-flipped-join-club', 'is-flipped-create-club');
        cardFlipInner.classList.add('is-flipped', 'is-flipped-register');
      });
    }

    if (btnShowLogin) {
      btnShowLogin.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped', 'is-flipped-register', 'is-flipped-forgot', 'is-flipped-join-club', 'is-flipped-create-club');
      });
    }

    if (btnShowForgot) {
      btnShowForgot.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped', 'is-flipped-register', 'is-flipped-join-club', 'is-flipped-create-club');
        cardFlipInner.classList.add('is-flipped-forgot');
        const emailInput = document.getElementById('forgot_email');
        if (emailInput) setTimeout(() => emailInput.focus(), 350);
      });
    }

    if (btnForgotBack) {
      btnForgotBack.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped-forgot', 'is-flipped-register', 'is-flipped-join-club', 'is-flipped-create-club', 'is-flipped');
      });
    }

    if (btnShowJoinClub) {
      btnShowJoinClub.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped', 'is-flipped-register', 'is-flipped-forgot', 'is-flipped-create-club');
        cardFlipInner.classList.add('is-flipped', 'is-flipped-join-club');
        if (window.filtrarClubesBuscaCard) window.filtrarClubesBuscaCard('');
      });
    }

    if (btnShowCreateClub) {
      btnShowCreateClub.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped', 'is-flipped-register', 'is-flipped-forgot', 'is-flipped-join-club');
        cardFlipInner.classList.add('is-flipped', 'is-flipped-create-club');
      });
    }

    document.querySelectorAll('.js-back-to-login').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped', 'is-flipped-register', 'is-flipped-forgot', 'is-flipped-join-club', 'is-flipped-create-club');
      });
    });
  }

  // Funções Globais de Busca e Seleção de Clube no Card
  let clubeSelecionadoCard = null;

  window.filtrarClubesBuscaCard = async function(query) {
    const listWrap = document.getElementById('joinClubResultsList');
    if (!listWrap) return;

    try {
      const resp = await fetch('/api/clube/buscar?q=' + encodeURIComponent(query || ''));
      const data = await resp.json();
      const clubes = data.clubes || [];

      if (clubes.length === 0) {
        listWrap.innerHTML = `
          <div style="text-align: center; padding: 1.2rem; color: #94a3b8; font-size: 0.84rem;">
            Nenhum clube encontrado para "${query}".
          </div>
        `;
        return;
      }

      listWrap.innerHTML = clubes.map(c => `
        <div class="mc-club-item" onclick='selecionarClubeNoCard(${JSON.stringify(c)})'>
          <div>
            <div class="mc-club-name">${c.nome}</div>
            <div class="mc-club-code-badge">Código: <span class="mc-club-code-num">${c.codigo_formatado}</span></div>
          </div>
          <span class="mc-club-join-pill">Entrar</span>
        </div>
      `).join('');
    } catch (e) {
      console.error('Erro ao buscar clubes:', e);
    }
  };

  let usuarioAutenticadoClube = null;

  window.selecionarClubeNoCard = function(clube) {
    clubeSelecionadoCard = clube;
    document.getElementById('joinStepSearch').style.display = 'none';
    document.getElementById('joinStepChoice').style.display = 'block';
    document.getElementById('joinStepInlineLogin').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'none';

    document.getElementById('chosenClubName').textContent = clube.nome;
    document.getElementById('chosenClubBadge').textContent = 'Clube ' + clube.codigo_formatado;

    const lbl1 = document.getElementById('inlineLoginClubName');
    if (lbl1) lbl1.textContent = clube.nome;
    const lbl2 = document.getElementById('inlineRegisterClubName');
    if (lbl2) lbl2.textContent = clube.nome;
  };

  window.abrirStepInlineLogin = function() {
    document.getElementById('joinStepChoice').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'none';
    if (document.getElementById('joinStepJudgeLogin')) document.getElementById('joinStepJudgeLogin').style.display = 'none';
    const inlinePane = document.getElementById('joinStepInlineLogin');
    if (inlinePane) {
      inlinePane.style.display = 'block';
      const userInput = document.getElementById('joinUsername');
      if (userInput && userInput.value === 'admin') {
        userInput.value = '';
      }
    }
  };

  window.abrirStepAdminLogin = function() {
    document.getElementById('joinStepChoice').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'none';
    if (document.getElementById('joinStepJudgeLogin')) document.getElementById('joinStepJudgeLogin').style.display = 'none';
    const inlinePane = document.getElementById('joinStepInlineLogin');
    if (inlinePane) {
      inlinePane.style.display = 'block';
      const userInput = document.getElementById('joinUsername');
      if (userInput) {
        userInput.value = 'admin';
      }
      const pwdInput = document.getElementById('joinPassword');
      if (pwdInput) {
        pwdInput.focus();
      }
    }
  };

  window.abrirStepInlineRegister = function() {
    document.getElementById('joinStepChoice').style.display = 'none';
    document.getElementById('joinStepInlineLogin').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    if (document.getElementById('joinStepJudgeLogin')) document.getElementById('joinStepJudgeLogin').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'block';

    const lbl = document.getElementById('inlineRegisterClubName');
    if (lbl && clubeSelecionadoCard) lbl.textContent = clubeSelecionadoCard.nome;

    if (typeof goToRegStep === 'function') {
      goToRegStep(1);
    }
  };

  window.abrirStepJudgeLogin = function() {
    document.getElementById('joinStepChoice').style.display = 'none';
    document.getElementById('joinStepInlineLogin').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'none';
    const judgePane = document.getElementById('joinStepJudgeLogin');
    if (judgePane) {
      judgePane.style.display = 'block';
      const lbl = document.getElementById('judgeLoginClubName');
      if (lbl && clubeSelecionadoCard) lbl.textContent = clubeSelecionadoCard.nome;
    }
  };

  window.voltarParaEscolhaClube = function() {
    document.getElementById('joinStepInlineLogin').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'none';
    if (document.getElementById('joinStepJudgeLogin')) document.getElementById('joinStepJudgeLogin').style.display = 'none';
    document.getElementById('joinStepChoice').style.display = 'block';
  };

  window.voltarParaBuscaClube = function() {
    clubeSelecionadoCard = null;
    document.getElementById('joinStepChoice').style.display = 'none';
    document.getElementById('joinStepInlineLogin').style.display = 'none';
    document.getElementById('joinStepConfirmAccount').style.display = 'none';
    document.getElementById('joinStepInlineRegister').style.display = 'none';
    if (document.getElementById('joinStepJudgeLogin')) document.getElementById('joinStepJudgeLogin').style.display = 'none';
    document.getElementById('joinStepSearch').style.display = 'block';
  };

  window.voltarFluxoClube = function() {
    const confirmAccountPane = document.getElementById('joinStepConfirmAccount');
    const inlineLoginPane = document.getElementById('joinStepInlineLogin');
    const inlineRegisterPane = document.getElementById('joinStepInlineRegister');
    const judgePane = document.getElementById('joinStepJudgeLogin');
    const choicePane = document.getElementById('joinStepChoice');
    const searchPane = document.getElementById('joinStepSearch');

    // 1. Se estiver na confirmação de perfil vinculado -> volta para o login de conta
    if (confirmAccountPane && confirmAccountPane.style.display !== 'none') {
      confirmAccountPane.style.display = 'none';
      if (inlineLoginPane) inlineLoginPane.style.display = 'block';
      return;
    }

    // 2. Se estiver no cadastro do clube (Wizard 5 passos) -> navega 1 passo atrás por vez
    if (inlineRegisterPane && inlineRegisterPane.style.display !== 'none') {
      if (typeof currentRegStep === 'number' && currentRegStep > 1) {
        goToRegStep(currentRegStep - 1);
        return;
      }
      window.voltarParaEscolhaClube();
      return;
    }

    // 3. Se estiver em outro formulário interno (Login ou Juiz) -> volta para a escolha de acesso do clube
    if ((inlineLoginPane && inlineLoginPane.style.display !== 'none') ||
        (judgePane && judgePane.style.display !== 'none')) {
      window.voltarParaEscolhaClube();
      return;
    }

    // 4. Se estiver nas opções de acesso do clube (Passo 2) -> volta para a busca de clubes (Passo 1)
    if (choicePane && choicePane.style.display !== 'none' && searchPane) {
      window.voltarParaBuscaClube();
      return;
    }

    // 5. Se estiver na busca de clubes (Passo 1) ou topo -> volta para a frente do card (Login Principal)
    if (cardFlipInner && cardFlipInner.classList.contains('is-flipped-join-club')) {
      cardFlipInner.classList.remove('is-flipped', 'is-flipped-join-club', 'is-flipped-register', 'is-flipped-forgot', 'is-flipped-create-club');
    } else if (window.history && window.history.length > 1) {
      window.history.back();
    }
  };

  function obterCodigoClubeContexto() {
    if (clubeSelecionadoCard && (clubeSelecionadoCard.codigo_formatado || clubeSelecionadoCard.codigo)) {
      return clubeSelecionadoCard.codigo_formatado || clubeSelecionadoCard.codigo;
    }
    if (window.TARGET_CLUBE_INITIAL && (window.TARGET_CLUBE_INITIAL.codigo_formatado || window.TARGET_CLUBE_INITIAL.codigo)) {
      return window.TARGET_CLUBE_INITIAL.codigo_formatado || window.TARGET_CLUBE_INITIAL.codigo;
    }
    if (window.CURRENT_CLUBE_CODIGO) {
      return window.CURRENT_CLUBE_CODIGO;
    }
    return '001';
  }

  window.submeterInlineLoginClube = async function() {
    const userIn = document.getElementById('joinUsername');
    const passIn = document.getElementById('joinPassword');
    const msgBox = document.getElementById('joinInlineLoginMsg');

    const username = userIn ? userIn.value.trim() : '';
    const senha = passIn ? passIn.value.trim() : '';

    if (!username || !senha) {
      if (msgBox) {
        msgBox.textContent = 'Por favor, informe seu usuário e senha.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    try {
      const resp = await fetch('/api/clube/entrar-com-conta-existente', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          username: username,
          senha: senha,
          clube_codigo: obterCodigoClubeContexto()
        })
      });
      const data = await resp.json();

      if (data.sucesso && data.requer_confirmacao) {
        usuarioAutenticadoClube = data.user;
        document.getElementById('confirmUserNome').textContent = data.user.nome;
        document.getElementById('confirmClubNome').textContent = data.clube.nome;

        document.getElementById('joinStepInlineLogin').style.display = 'none';
        document.getElementById('joinStepConfirmAccount').style.display = 'block';
      } else {
        if (msgBox) {
          msgBox.textContent = data.mensagem || 'Usuário ou senha incorretos.';
          msgBox.style.color = '#ef4444';
        }
      }
    } catch (e) {
      if (msgBox) {
        msgBox.textContent = 'Erro ao conectar ao servidor.';
        msgBox.style.color = '#ef4444';
      }
    }
  };

  window.confirmarEntradaNoClube = async function() {
    const msgBox = document.getElementById('joinConfirmMsg');
    const cod = (clubeSelecionadoCard && (clubeSelecionadoCard.codigo_formatado || clubeSelecionadoCard.codigo)) || obterCodigoClubeContexto();
    if (!usuarioAutenticadoClube) return;

    try {
      const resp = await fetch('/api/clube/confirmar-entrada', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          user_id: usuarioAutenticadoClube.id,
          clube_codigo: cod
        })
      });
      const data = await resp.json();

      if (data.sucesso && data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        if (msgBox) {
          msgBox.textContent = data.mensagem || 'Não foi possível associar a este clube.';
          msgBox.style.color = '#ef4444';
        }
      }
    } catch (e) {
      if (msgBox) {
        msgBox.textContent = 'Erro de conexão com o servidor.';
        msgBox.style.color = '#ef4444';
      }
    }
  };

  // --- VERIFICAÇÃO INSTANTÂNEA E NAVEGAÇÃO DO WIZARD DE CADASTRO NO CLUBE (3 PASSOS) ---
  let inlineUserCheckDebounce = null;
  let inlineUsernameValid = false;

  function updateWizardDots(step) {
    const d1 = document.getElementById('wizardDot1');
    const d2 = document.getElementById('wizardDot2');
    const d3 = document.getElementById('wizardDot3');
    if (d1) d1.style.background = step >= 1 ? '#22c55e' : 'rgba(255, 255, 255, 0.2)';
    if (d2) d2.style.background = step >= 2 ? '#22c55e' : 'rgba(255, 255, 255, 0.2)';
    if (d3) d3.style.background = step >= 3 ? '#22c55e' : 'rgba(255, 255, 255, 0.2)';
  }

  window.validarNomeInstantaneo = function(val) {
    const statusEl = document.getElementById('regNomeStatus');
    const wrapEl = document.getElementById('regNomeWrap');
    const nome = (val || '').trim();
    const partes = nome.split(/\s+/).filter(Boolean);

    if (!statusEl) return true;

    if (nome.length === 0) {
      statusEl.style.display = 'none';
      statusEl.textContent = '';
      if (wrapEl) wrapEl.style.borderColor = 'rgba(255, 255, 255, 0.14)';
      return false;
    }

    if (partes.length < 2) {
      statusEl.style.display = 'block';
      statusEl.style.color = '#f59e0b';
      statusEl.textContent = '⚠ Digite seu nome e sobrenome (mínimo 2 nomes)';
      if (wrapEl) wrapEl.style.borderColor = '#f59e0b';
      return false;
    }

    statusEl.style.display = 'block';
    statusEl.style.color = '#10b981';
    statusEl.textContent = '✓ Nome completo válido';
    if (wrapEl) wrapEl.style.borderColor = '#10b981';
    return true;
  };

  window.validarUsernameInstantaneo = function(val) {
    const statusEl = document.getElementById('regUsernameStatus');
    const wrapEl = document.getElementById('regUsernameWrap');
    const username = (val || '').trim().toLowerCase();
    inlineUsernameValid = false;

    if (inlineUserCheckDebounce) clearTimeout(inlineUserCheckDebounce);

    if (!statusEl) return;

    if (username.length === 0) {
      statusEl.style.display = 'none';
      statusEl.textContent = '';
      if (wrapEl) wrapEl.style.borderColor = 'rgba(255, 255, 255, 0.14)';
      return;
    }

    if (username.length < 3) {
      statusEl.style.display = 'block';
      statusEl.style.color = '#f59e0b';
      statusEl.textContent = '⚠ Mínimo de 3 caracteres';
      if (wrapEl) wrapEl.style.borderColor = '#f59e0b';
      return;
    }

    const usernameRegex = /^[a-z0-9._]{3,30}$/;
    if (!usernameRegex.test(username)) {
      statusEl.style.display = 'block';
      statusEl.style.color = '#ef4444';
      statusEl.textContent = '✗ Apenas letras, números, ponto ou underline';
      if (wrapEl) wrapEl.style.borderColor = '#ef4444';
      return;
    }

    statusEl.style.display = 'block';
    statusEl.style.color = '#94a3b8';
    statusEl.textContent = 'Verificando disponibilidade do @...';
    if (wrapEl) wrapEl.style.borderColor = '#3b82f6';

    inlineUserCheckDebounce = setTimeout(async () => {
      try {
        const res = await fetch(`/checar-username?username=${encodeURIComponent(username)}`);
        const data = await res.json();
        if (data.available) {
          inlineUsernameValid = true;
          statusEl.style.color = '#10b981';
          statusEl.textContent = `✓ ${data.message || '@ disponível'}`;
          if (wrapEl) wrapEl.style.borderColor = '#10b981';
        } else {
          inlineUsernameValid = false;
          statusEl.style.color = '#ef4444';
          statusEl.textContent = `✗ ${data.message || '@ indisponível'}`;
          if (wrapEl) wrapEl.style.borderColor = '#ef4444';
        }
      } catch (err) {
        statusEl.style.color = '#f59e0b';
        statusEl.textContent = '⚠ Erro ao verificar disponibilidade';
      }
    }, 250);
  };

  window.validarSenhaInstantanea = function(val) {
    const statusEl = document.getElementById('regSenhaStatus');
    const wrapEl = document.getElementById('regSenhaWrap');
    const senha = (val || '').trim();

    if (!statusEl) return true;

    if (senha.length === 0) {
      statusEl.style.display = 'none';
      statusEl.textContent = '';
      if (wrapEl) wrapEl.style.borderColor = 'rgba(255, 255, 255, 0.14)';
      return false;
    }

    if (senha.length < 6) {
      statusEl.style.display = 'block';
      statusEl.style.color = '#f59e0b';
      statusEl.textContent = `⚠ Faltam ${6 - senha.length} caracteres (mínimo 6)`;
      if (wrapEl) wrapEl.style.borderColor = '#f59e0b';
      return false;
    }

    statusEl.style.display = 'block';
    statusEl.style.color = '#10b981';
    statusEl.textContent = '✓ Senha segura!';
    if (wrapEl) wrapEl.style.borderColor = '#10b981';
    return true;
  };

  window.avancarWizardPasso2 = function() {
    const elNome = document.getElementById('regNome');
    const val = elNome ? elNome.value : '';
    if (!window.validarNomeInstantaneo(val)) {
      if (elNome) elNome.focus();
      return;
    }
    const s1 = document.getElementById('joinRegStep1');
    const s2 = document.getElementById('joinRegStep2');
    if (s1) s1.style.display = 'none';
    if (s2) s2.style.display = 'block';
    updateWizardDots(2);
  };

  window.avancarWizardPasso3 = function() {
    const elUser = document.getElementById('regUsername');
    const username = elUser ? elUser.value.trim().toLowerCase() : '';
    const statusEl = document.getElementById('regUsernameStatus');

    if (!username || username.length < 3) {
      if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.style.color = '#ef4444';
        statusEl.textContent = '⚠ Digite um @ de usuário válido (mínimo 3 caracteres)';
      }
      if (elUser) elUser.focus();
      return;
    }

    if (!inlineUsernameValid) {
      if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.style.color = '#ef4444';
        statusEl.textContent = '⚠ O @ escolhido não está disponível. Escolha outro.';
      }
      if (elUser) elUser.focus();
      return;
    }

    const s2 = document.getElementById('joinRegStep2');
    const s3 = document.getElementById('joinRegStep3');
    if (s2) s2.style.display = 'none';
    if (s3) s3.style.display = 'block';
    updateWizardDots(3);
  };

  window.voltarWizardPasso1 = function() {
    const s1 = document.getElementById('joinRegStep1');
    const s2 = document.getElementById('joinRegStep2');
    if (s2) s2.style.display = 'none';
    if (s1) s1.style.display = 'block';
    updateWizardDots(1);
  };

  window.voltarWizardPasso2 = function() {
    const s2 = document.getElementById('joinRegStep2');
    const s3 = document.getElementById('joinRegStep3');
    if (s3) s3.style.display = 'none';
    if (s2) s2.style.display = 'block';
    updateWizardDots(2);
  };

  window.selecionarPosicao = function(pos) {
    const inputPos = document.getElementById('reg_posicao');
    if (inputPos) inputPos.value = pos;

    const cardLinha = document.getElementById('posCardLinha');
    const cardGoleiro = document.getElementById('posCardGoleiro');

    if (pos === 'Linha') {
      if (cardLinha) {
        cardLinha.style.background = 'rgba(34, 197, 94, 0.14)';
        cardLinha.style.border = '2px solid #22c55e';
        cardLinha.style.boxShadow = '0 4px 14px rgba(34, 197, 94, 0.15)';
        const icon = cardLinha.querySelector('.pos-card-icon');
        if (icon) icon.style.color = '#22c55e';
      }
      if (cardGoleiro) {
        cardGoleiro.style.background = 'rgba(255, 255, 255, 0.04)';
        cardGoleiro.style.border = '1px solid rgba(255, 255, 255, 0.12)';
        cardGoleiro.style.boxShadow = 'none';
        const icon = cardGoleiro.querySelector('.pos-card-icon');
        if (icon) icon.style.color = '#64748b';
      }
    } else {
      if (cardGoleiro) {
        cardGoleiro.style.background = 'rgba(34, 197, 94, 0.14)';
        cardGoleiro.style.border = '2px solid #22c55e';
        cardGoleiro.style.boxShadow = '0 4px 14px rgba(34, 197, 94, 0.15)';
        const icon = cardGoleiro.querySelector('.pos-card-icon');
        if (icon) icon.style.color = '#22c55e';
      }
      if (cardLinha) {
        cardLinha.style.background = 'rgba(255, 255, 255, 0.04)';
        cardLinha.style.border = '1px solid rgba(255, 255, 255, 0.12)';
        cardLinha.style.boxShadow = 'none';
        const icon = cardLinha.querySelector('.pos-card-icon');
        if (icon) icon.style.color = '#64748b';
      }
    }
  };

  window.submeterInlineCadastroClube = async function() {
    const elNome = document.getElementById('reg_nome') || document.getElementById('regNome');
    const elEmail = document.getElementById('reg_email');
    const elUser = document.getElementById('reg_username') || document.getElementById('regUsername');
    const elPos = document.getElementById('reg_posicao') || document.getElementById('regPosicao');
    const elSenha = document.getElementById('reg_password') || document.getElementById('regSenha');
    const msgBox = document.getElementById('reg-step5-status') || document.getElementById('joinInlineRegMsg');
    const btnNext = document.getElementById('reg-btn-next');

    const nome = elNome ? elNome.value.trim() : '';
    const email = elEmail ? elEmail.value.trim() : '';
    const username = elUser ? elUser.value.trim().toLowerCase() : '';
    const posicao = elPos ? elPos.value : 'Linha';
    const senha = elSenha ? elSenha.value.trim() : '';

    if (msgBox) {
      msgBox.style.display = 'none';
      msgBox.textContent = '';
    }

    if (btnNext) {
      btnNext.disabled = true;
      btnNext.innerHTML = '<span>Criando conta e entrando...</span>';
    }

    try {
      const resp = await fetch('/api/clube/cadastrar-e-entrar', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          nome: nome,
          email: email,
          username: username,
          posicao: posicao,
          senha: senha,
          clube_codigo: obterCodigoClubeContexto()
        })
      });
      const data = await resp.json();

      if (data.sucesso && data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        if (msgBox) {
          msgBox.textContent = data.mensagem || 'Não foi possível criar a conta.';
          msgBox.className = 'reg-live-status reg-live-status--err';
          msgBox.style.display = 'block';
        }
        if (btnNext) {
          btnNext.disabled = false;
          btnNext.innerHTML = '<span>Continuar</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; margin-left: 6px;"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
        }
      }
    } catch (e) {
      if (msgBox) {
        msgBox.textContent = 'Erro ao conectar ao servidor.';
        msgBox.className = 'reg-live-status reg-live-status--err';
        msgBox.style.display = 'block';
      }
      if (btnNext) {
        btnNext.disabled = false;
        btnNext.innerHTML = '<span>Continuar</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; margin-left: 6px;"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
      }
    }
  };

  window.submeterEntradaJuizClube = async function() {
    const passIn = document.getElementById('joinJudgeSenha');
    const msgBox = document.getElementById('joinJudgeLoginMsg');

    const senhaJuiz = passIn ? passIn.value.trim() : '';

    if (!senhaJuiz) {
      if (msgBox) {
        msgBox.textContent = 'Por favor, informe a senha do juiz.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    try {
      const resp = await fetch('/api/clube/entrar-como-juiz', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          clube_codigo: obterCodigoClubeContexto(),
          senha_juiz: senhaJuiz
        })
      });
      const data = await resp.json();

      if (data.sucesso && data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        if (msgBox) {
          msgBox.textContent = data.mensagem || 'Senha do Juiz incorreta.';
          msgBox.style.color = '#ef4444';
        }
      }
    } catch (e) {
      if (msgBox) {
        msgBox.textContent = 'Erro ao conectar ao servidor.';
        msgBox.style.color = '#ef4444';
      }
    }
  };

  /* FLUXO CRIAR CLUBE DO ZERO */
  let corTemaClubeSelecionadoCard = 'neon-green';
  window.selecionarCorCard = function(radioInput, hexColor) {
    document.querySelectorAll('.mc-color-dot').forEach(dot => {
      dot.classList.remove('is-active');
    });
    if (radioInput) {
      corTemaClubeSelecionadoCard = radioInput.value || 'neon-green';
      const parentLabel = radioInput.closest('.mc-color-dot');
      if (parentLabel) parentLabel.classList.add('is-active');
    }
  };

  let timerCardCreate = null;
  let timerAdminEmail = null;

  function setFieldVisualState(wrap, feedback, state, msg) {
    if (wrap) {
      wrap.classList.remove('is-valid', 'is-invalid', 'is-warning');
      if (state) wrap.classList.add(state);
    }
    if (feedback) {
      if (!msg) {
        feedback.style.display = 'none';
        feedback.textContent = '';
      } else {
        feedback.style.display = 'block';
        feedback.textContent = msg;
        if (state === 'is-valid') feedback.style.color = '#10b981';
        else if (state === 'is-invalid') feedback.style.color = '#ef4444';
        else if (state === 'is-warning') feedback.style.color = '#f59e0b';
        else feedback.style.color = '#94a3b8';
      }
    }
  }

  // 1. VALIDAÇÃO INSTANTÂNEA: NOME DO CLUBE
  window.validarNomeCardCriarClube = function(val) {
    clearTimeout(timerCardCreate);
    const feedback = document.getElementById('createClubCardFeedback');
    const wrap = document.getElementById('wrapCreateClubName');
    const nome = (val || '').trim();

    if (!nome) {
      setFieldVisualState(wrap, feedback, '', '');
      return;
    }
    if (nome.length < 2) {
      setFieldVisualState(wrap, feedback, 'is-warning', '⚠ O nome do clube deve ter no mínimo 2 caracteres.');
      return;
    }

    setFieldVisualState(wrap, feedback, '', 'Verificando disponibilidade no NaTrave...');

    timerCardCreate = setTimeout(async () => {
      try {
        const resp = await fetch('/api/clube/validar-nome', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({ nome: nome })
        });
        const data = await resp.json();
        if (data.disponivel) {
          setFieldVisualState(wrap, feedback, 'is-valid', '✓ ' + (data.mensagem || 'Nome de clube disponível!'));
        } else {
          setFieldVisualState(wrap, feedback, 'is-invalid', '✗ ' + (data.mensagem || 'Já existe um clube com este nome.'));
        }
      } catch (e) {
        setFieldVisualState(wrap, feedback, 'is-warning', '⚠ Não foi possível verificar o nome no momento.');
      }
    }, 250);
  };

  // 2. VALIDAÇÃO INSTANTÂNEA: E-MAIL DO ADMIN (VERIFICAÇÃO NA BASE COMPLETA)
  window.validarEmailAdminInstantaneo = function(val) {
    clearTimeout(timerAdminEmail);
    const feedback = document.getElementById('createRegEmailFeedback');
    const wrap = document.getElementById('wrapCreateRegEmail');
    const email = (val || '').trim().toLowerCase();

    if (!email) {
      setFieldVisualState(wrap, feedback, '', '');
      return;
    }

    if (!email.includes('@') || !email.split('@')[1]?.includes('.')) {
      setFieldVisualState(wrap, feedback, 'is-warning', '⚠ Digite um formato válido (ex: seu-email@exemplo.com)');
      return;
    }

    setFieldVisualState(wrap, feedback, '', 'Consultando e-mail na base de dados...');

    timerAdminEmail = setTimeout(async () => {
      try {
        const resp = await fetch(`/checar-email?email=${encodeURIComponent(email)}`);
        const data = await resp.json();
        if (data.available) {
          setFieldVisualState(wrap, feedback, 'is-valid', '✓ E-mail disponível para criar o clube!');
        } else {
          setFieldVisualState(wrap, feedback, 'is-warning', 'ℹ E-mail já cadastrado no NaTrave. Se for sua conta, use sua senha para vincular.');
        }
      } catch (e) {
        setFieldVisualState(wrap, feedback, 'is-warning', '⚠ Erro ao consultar a base de e-mails.');
      }
    }, 250);
  };

  // 3. VALIDAÇÃO INSTANTÂNEA: SENHA DO ADMIN
  window.validarSenhaAdminInstantaneo = function(val) {
    const feedback = document.getElementById('createRegSenhaFeedback');
    const wrap = document.getElementById('wrapCreateRegSenha');
    const senha = (val || '').trim();

    if (!senha) {
      setFieldVisualState(wrap, feedback, '', '');
      return;
    }

    if (senha.length < 6) {
      setFieldVisualState(wrap, feedback, 'is-warning', `⚠ Mínimo 6 caracteres (faltam ${6 - senha.length})`);
    } else {
      setFieldVisualState(wrap, feedback, 'is-valid', '✓ Senha de administrador válida!');
    }
  };

  // 4. VALIDAÇÃO INSTANTÂNEA: SENHA DO JUIZ
  window.validarSenhaJuizInstantaneo = function(val) {
    const feedback = document.getElementById('createRegSenhaJuizFeedback');
    const wrap = document.getElementById('wrapCreateRegSenhaJuiz');
    const senha = (val || '').trim();

    if (!senha) {
      setFieldVisualState(wrap, feedback, '', '');
      return;
    }

    if (senha.length < 4) {
      setFieldVisualState(wrap, feedback, 'is-warning', `⚠ Mínimo 4 caracteres (faltam ${4 - senha.length})`);
    } else {
      setFieldVisualState(wrap, feedback, 'is-valid', '✓ Senha do Juiz definida!');
    }
  };

  function atualizarHeaderCriacaoClube(passo) {
    const sub = document.getElementById('createClubHeaderSub');
    const dot1 = document.getElementById('createClubDot1');
    const dot2 = document.getElementById('createClubDot2');
    const dot3 = document.getElementById('createClubDot3');
    const num = document.getElementById('createClubStepNum');

    if (num) num.textContent = String(passo);
    if (dot1) dot1.style.background = '#22c55e';

    if (passo === 1) {
      if (sub) sub.textContent = 'Passo 1: Identificação do Clube';
      if (dot2) dot2.style.background = 'rgba(255,255,255,0.2)';
      if (dot3) dot3.style.background = 'rgba(255,255,255,0.2)';
    } else if (passo === 2) {
      if (sub) sub.textContent = 'Passo 2: Conta do Administrador';
      if (dot2) dot2.style.background = '#22c55e';
      if (dot3) dot3.style.background = 'rgba(255,255,255,0.2)';
    } else if (passo === 3) {
      if (sub) sub.textContent = 'Passo 3: Acesso do Juiz e Confirmação';
      if (dot2) dot2.style.background = '#22c55e';
      if (dot3) dot3.style.background = '#22c55e';
    }
  }

  window.avancarCriacaoClubeStep2 = function() {
    const input = document.getElementById('inputCreateClubNameCard');
    const val = input ? input.value.trim() : '';
    const feedback = document.getElementById('createClubCardFeedback');
    if (!val || val.length < 2) {
      if (feedback) {
        feedback.textContent = 'Informe um nome com pelo menos 2 caracteres.';
        feedback.style.color = '#ef4444';
      }
      if (input) input.focus();
      return;
    }
    const lbl = document.getElementById('targetNewClubName');
    if (lbl) lbl.textContent = val;
    const summaryClub = document.getElementById('summaryClubName');
    if (summaryClub) summaryClub.textContent = val;

    atualizarHeaderCriacaoClube(2);
    document.getElementById('createStepDetails').style.display = 'none';
    document.getElementById('createStepAdminAuth').style.display = 'block';
    const step3 = document.getElementById('createStepJudgeAuth');
    if (step3) step3.style.display = 'none';

    // Foco automático no e-mail
    setTimeout(() => {
      const emailIn = document.getElementById('createRegEmail');
      if (emailIn) emailIn.focus();
    }, 100);
  };

  window.avancarCriacaoClubeStep3 = function() {
    const emailIn = document.getElementById('createRegEmail');
    const email = emailIn ? emailIn.value.trim() : '';
    const senhaIn = document.getElementById('createRegSenha');
    const senha = senhaIn ? senhaIn.value.trim() : '';
    const msgBox = document.getElementById('createStep2Msg');

    if (!email || !email.includes('@') || !email.includes('.')) {
      if (msgBox) {
        msgBox.textContent = 'Por favor, informe um e-mail válido para o Admin.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    if (!senha || senha.length < 6) {
      if (msgBox) {
        msgBox.textContent = 'A senha do Admin deve ter pelo menos 6 caracteres.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    if (msgBox) msgBox.textContent = '';

    const summaryEmail = document.getElementById('summaryAdminEmail');
    if (summaryEmail) summaryEmail.textContent = email;

    atualizarHeaderCriacaoClube(3);
    document.getElementById('createStepAdminAuth').style.display = 'none';
    const step3 = document.getElementById('createStepJudgeAuth');
    if (step3) step3.style.display = 'block';

    // Foco na senha do juiz
    setTimeout(() => {
      const juizIn = document.getElementById('createRegSenhaJuiz');
      if (juizIn) juizIn.focus();
    }, 100);
  };

  window.voltarParaPasso1CriarClube = function() {
    atualizarHeaderCriacaoClube(1);
    const step2 = document.getElementById('createStepAdminAuth');
    if (step2) step2.style.display = 'none';
    const step3 = document.getElementById('createStepJudgeAuth');
    if (step3) step3.style.display = 'none';
    document.getElementById('createStepDetails').style.display = 'block';
  };

  window.voltarParaPasso2CriarClube = function() {
    atualizarHeaderCriacaoClube(2);
    const step3 = document.getElementById('createStepJudgeAuth');
    if (step3) step3.style.display = 'none';
    const step2 = document.getElementById('createStepAdminAuth');
    if (step2) step2.style.display = 'block';
  };

  window.voltarFluxoCriarClube = function() {
    const step3 = document.getElementById('createStepJudgeAuth');
    if (step3 && step3.style.display !== 'none') {
      window.voltarParaPasso2CriarClube();
      return;
    }
    const step2 = document.getElementById('createStepAdminAuth');
    if (step2 && step2.style.display !== 'none') {
      window.voltarParaPasso1CriarClube();
      return;
    }

    if (cardFlipInner && cardFlipInner.classList.contains('is-flipped-create-club')) {
      cardFlipInner.classList.remove('is-flipped', 'is-flipped-join-club', 'is-flipped-register', 'is-flipped-forgot', 'is-flipped-create-club');
    } else if (window.history && window.history.length > 1) {
      window.history.back();
    }
  };

  window.processarCriacaoClubeComCadastro = async function() {
    const input = document.getElementById('inputCreateClubNameCard');
    const nomeClube = input ? input.value.trim() : '';
    const nome = document.getElementById('createRegNome') ? document.getElementById('createRegNome').value.trim() : 'Administrador';
    const emailIn = document.getElementById('createRegEmail');
    const email = emailIn ? emailIn.value.trim() : '';
    const username = document.getElementById('createRegUsername') ? document.getElementById('createRegUsername').value.trim() : 'admin';
    const senha = document.getElementById('createRegSenha') ? document.getElementById('createRegSenha').value.trim() : '';
    const senhaJuizIn = document.getElementById('createRegSenhaJuiz');
    const senhaJuiz = senhaJuizIn ? senhaJuizIn.value.trim() : '';
    const msgBox = document.getElementById('createInlineRegMsg');

    if (!nomeClube) {
      if (msgBox) {
        msgBox.textContent = 'Por favor, informe o nome do clube no Passo 1.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    if (!email || !email.includes('@')) {
      if (msgBox) {
        msgBox.textContent = 'Por favor, informe um e-mail válido para o Admin.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    if (!senha || senha.length < 6) {
      if (msgBox) {
        msgBox.textContent = 'A senha do Admin deve ter no mínimo 6 caracteres.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    if (!senhaJuiz) {
      if (msgBox) {
        msgBox.textContent = 'Por favor, defina a senha do Juiz do clube.';
        msgBox.style.color = '#ef4444';
      }
      return;
    }

    try {
      const resp = await fetch('/api/clube/criar-com-autenticacao', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          nome_clube: nomeClube,
          cor_tema: corTemaClubeSelecionadoCard,
          modo_auth: 'novo',
          nome: nome,
          email: email,
          username: username,
          senha: senha,
          senha_juiz: senhaJuiz
        })
      });
      let data = {};
      try {
        data = await resp.json();
      } catch (jsonErr) {
        data = { mensagem: 'Ocorreu um erro no servidor. Tente novamente.' };
      }
      if (data.sucesso && data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        if (msgBox) {
          msgBox.textContent = data.mensagem || 'Não foi possível criar o clube.';
          msgBox.style.color = '#ef4444';
        }
      }
    } catch (e) {
      if (msgBox) {
        msgBox.textContent = 'Erro ao conectar ao servidor. Verifique sua conexão e tente novamente.';
        msgBox.style.color = '#ef4444';
      }
    }
  };

  // Handler AJAX para formulário de Recuperar Senha
  const forgotForm = document.getElementById('forgot-password-form');
  const forgotStatus = document.getElementById('forgot-status-msg');
  const btnForgotSubmit = document.getElementById('btn-forgot-submit');

  if (forgotForm) {
    forgotForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const emailInput = document.getElementById('forgot_email');
      const emailVal = emailInput ? emailInput.value.trim() : '';

      if (!emailVal) return;

      if (btnForgotSubmit) {
        btnForgotSubmit.disabled = true;
        btnForgotSubmit.innerHTML = '<span>Enviando...</span>';
      }

      try {
        const formData = new FormData(forgotForm);
        const response = await fetch(forgotForm.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        const data = await response.json();

        if (forgotStatus) {
          forgotStatus.style.display = 'flex';
          if (data.ok) {
            forgotStatus.className = 'auth-message auth-message--success';
            forgotStatus.innerHTML = `<span>${data.sucesso || 'Link de recuperação enviado com sucesso! Verifique seu e-mail.'}</span>`;
            if (emailInput) emailInput.value = '';
          } else {
            forgotStatus.className = 'auth-message auth-message--warning';
            forgotStatus.innerHTML = `<span>${data.erro || 'Erro ao enviar e-mail. Tente novamente.'}</span>`;
          }
        }
      } catch (err) {
        if (forgotStatus) {
          forgotStatus.style.display = 'flex';
          forgotStatus.className = 'auth-message auth-message--warning';
          forgotStatus.innerHTML = '<span>Erro ao conectar com o servidor. Tente novamente.</span>';
        }
      } finally {
        if (btnForgotSubmit) {
          btnForgotSubmit.disabled = false;
          btnForgotSubmit.innerHTML = '<span>Enviar Link de Recuperação</span>';
        }
      }
    });
  }

  // ============================================================
  // CONTROLLER DO WIZARD DE CADASTRO (1 A 5 PERGUNTA POR VEZ)
  // ============================================================
  const regForm = document.getElementById('reg-wizard-form');
  const regCounter = document.getElementById('reg-wizard-counter');
  const regProgressFill = document.getElementById('reg-wizard-progress');
  const regErrorBox = document.getElementById('reg-wizard-error');
  const regErrorMsg = document.getElementById('reg-wizard-error-msg');
  const regBtnPrev = document.getElementById('reg-btn-prev');
  const regBtnNext = document.getElementById('reg-btn-next');
  const regBtnFinish = document.getElementById('reg-btn-finish');

  const regNomeInput = document.getElementById('reg_nome');
  const regEmailInput = document.getElementById('reg_email');
  const regPasswordInput = document.getElementById('reg_password');
  const regUsernameInput = document.getElementById('reg_username');
  const regConfirmHidden = document.getElementById('reg_confirmar_password_hidden');

  const regNomeStatus = document.getElementById('reg-nome-status');
  const regEmailStatus = document.getElementById('reg-email-status');
  const regPwdStatus = document.getElementById('reg-pwd-status');
  const regUserStatus = document.getElementById('reg-user-status');
  const regStep5Status = document.getElementById('reg-step5-status');

  const regSummaryName = document.getElementById('reg-summary-name-val');
  const regSummaryUser = document.getElementById('reg-summary-user-val');

  let currentRegStep = 1;
  let emailValidAndAvailable = false;
  let usernameValidAndAvailable = false;
  let emailDebounceTimer = null;
  let usernameDebounceTimer = null;

  function showError(msg, step) {
    const activeStep = step || currentRegStep;
    let targetStatus = null;
    let targetInput = null;

    if (activeStep === 1) {
      targetStatus = regNomeStatus;
      targetInput = regNomeInput;
    } else if (activeStep === 2) {
      targetStatus = regEmailStatus;
      targetInput = regEmailInput;
    } else if (activeStep === 3) {
      targetStatus = regPwdStatus;
      targetInput = regPasswordInput;
    } else if (activeStep === 4) {
      targetStatus = regUserStatus;
      targetInput = regUsernameInput;
    } else if (activeStep === 5) {
      targetStatus = regStep5Status;
    }

    if (targetStatus) {
      targetStatus.textContent = msg;
      targetStatus.className = 'reg-live-status reg-live-status--err';
      targetStatus.style.display = 'block';
    }
    if (targetInput) {
      targetInput.classList.add('is-invalid');
      targetInput.focus();
    }
  }

  function clearError() {
    [regNomeStatus, regEmailStatus, regPwdStatus, regUserStatus, regStep5Status].forEach(st => {
      if (st && st.classList.contains('reg-live-status--err')) {
        st.style.display = 'none';
        st.textContent = '';
      }
    });
    [regNomeInput, regEmailInput, regPasswordInput, regUsernameInput].forEach(inp => {
      if (inp) inp.classList.remove('is-invalid');
    });
  }

  function goToRegStep(step) {
    clearError();
    currentRegStep = Math.max(1, Math.min(3, step));

    document.querySelectorAll('.js-reg-step').forEach(pane => {
      const paneStep = parseInt(pane.getAttribute('data-step'), 10);
      if (paneStep === currentRegStep) {
        pane.style.display = 'block';
        pane.classList.add('active');
      } else {
        pane.style.display = 'none';
        pane.classList.remove('active');
      }
    });

    if (regCounter) regCounter.innerHTML = `<strong style="color: #22c55e;">${currentRegStep}</strong> de 3`;
    
    // Atualizar dots de progresso
    const d1 = document.getElementById('wizardDot1');
    const d2 = document.getElementById('wizardDot2');
    const d3 = document.getElementById('wizardDot3');
    if (d1) d1.style.background = currentRegStep >= 1 ? '#22c55e' : 'rgba(255,255,255,0.2)';
    if (d2) d2.style.background = currentRegStep >= 2 ? '#22c55e' : 'rgba(255,255,255,0.2)';
    if (d3) d3.style.background = currentRegStep >= 3 ? '#22c55e' : 'rgba(255,255,255,0.2)';

    if (regBtnPrev) {
      regBtnPrev.style.visibility = currentRegStep > 1 ? 'visible' : 'hidden';
    }

    if (regBtnNext) {
      regBtnNext.style.display = 'flex';
      if (currentRegStep === 3) {
        if (regSummaryName && regNomeInput) regSummaryName.textContent = regNomeInput.value.trim() || 'Atleta';
        if (regSummaryUser && regUsernameInput) regSummaryUser.textContent = `@${regUsernameInput.value.trim() || 'username'}`;
        const summaryEmail = document.getElementById('reg-summary-email-val');
        if (summaryEmail && regEmailInput) summaryEmail.textContent = regEmailInput.value.trim();
        const summaryAvatar = document.getElementById('reg-summary-avatar-initial');
        if (summaryAvatar && regNomeInput && regNomeInput.value.trim().length > 0) {
          summaryAvatar.textContent = regNomeInput.value.trim()[0].toUpperCase();
        }

        const summaryPos = document.getElementById('reg-summary-pos-val');
        const posEl = document.getElementById('reg_posicao');
        const posVal = posEl ? posEl.value : 'Linha';
        if (summaryPos) {
          if (posVal === 'Goleiro') {
            summaryPos.innerHTML = `<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 20V5a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v15"/></svg> <span>Goleiro</span>`;
            summaryPos.style.background = 'rgba(56, 189, 248, 0.12)';
            summaryPos.style.borderColor = 'rgba(56, 189, 248, 0.25)';
            summaryPos.style.color = '#38bdf8';
          } else {
            summaryPos.innerHTML = `<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> <span>Linha</span>`;
            summaryPos.style.background = 'rgba(34, 197, 94, 0.12)';
            summaryPos.style.borderColor = 'rgba(34, 197, 94, 0.25)';
            summaryPos.style.color = '#4ade80';
          }
        }
      }
    }
  }

  // Validação ao vivo do Nome (Card 1)
  if (regNomeInput) {
    regNomeInput.addEventListener('input', () => {
      regNomeInput.classList.remove('is-invalid');
      const val = regNomeInput.value.trim();
      const partes = val.split(/\s+/).filter(Boolean);

      if (regNomeStatus) {
        if (!val) {
          regNomeStatus.style.display = 'none';
          regNomeStatus.textContent = '';
        } else if (partes.length < 2) {
          regNomeStatus.textContent = 'Informe nome e sobrenome';
          regNomeStatus.className = 'reg-live-status reg-live-status--err';
          regNomeStatus.style.display = 'block';
        } else {
          regNomeStatus.textContent = 'Nome válido!';
          regNomeStatus.className = 'reg-live-status reg-live-status--ok';
          regNomeStatus.style.display = 'block';
        }
      }
    });
  }

  // Validação ao vivo do E-mail (Card 1)
  if (regEmailInput) {
    regEmailInput.addEventListener('input', () => {
      regEmailInput.classList.remove('is-invalid');
      const email = regEmailInput.value.trim();
      emailValidAndAvailable = false;
      if (emailDebounceTimer) clearTimeout(emailDebounceTimer);

      if (!email || !email.includes('@') || !email.split('@')[1]?.includes('.')) {
        if (regEmailStatus) {
          regEmailStatus.textContent = email.length > 0 ? 'Digite um e-mail em formato válido' : '';
          regEmailStatus.className = 'reg-live-status reg-live-status--err';
          regEmailStatus.style.display = email.length > 0 ? 'block' : 'none';
        }
        return;
      }

      if (regEmailStatus) {
        regEmailStatus.textContent = 'Verificando e-mail...';
        regEmailStatus.className = 'reg-live-status reg-live-status--loading';
        regEmailStatus.style.display = 'block';
      }

      emailDebounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/checar-email?email=${encodeURIComponent(email)}`);
          const data = await res.json();
          emailValidAndAvailable = Boolean(data.available);
          if (regEmailStatus) {
            regEmailStatus.textContent = data.message || (data.available ? 'E-mail disponível!' : 'E-mail já cadastrado');
            regEmailStatus.className = data.available ? 'reg-live-status reg-live-status--ok' : 'reg-live-status reg-live-status--err';
          }
        } catch (err) {
          console.warn('Erro ao checar e-mail:', err);
        }
      }, 250);
    });
  }

  // Validação ao vivo do Username (Card 2)
  if (regUsernameInput) {
    regUsernameInput.addEventListener('input', () => {
      const username = regUsernameInput.value.trim();
      usernameValidAndAvailable = false;
      if (usernameDebounceTimer) clearTimeout(usernameDebounceTimer);

      if (!username || username.length < 3) {
        if (regUserStatus) {
          regUserStatus.textContent = username.length > 0 ? 'Mínimo de 3 caracteres' : '';
          regUserStatus.className = 'reg-live-status reg-live-status--err';
          regUserStatus.style.display = username.length > 0 ? 'block' : 'none';
        }
        return;
      }

      if (regUserStatus) {
        regUserStatus.textContent = 'Verificando @username...';
        regUserStatus.className = 'reg-live-status reg-live-status--loading';
        regUserStatus.style.display = 'block';
      }

      usernameDebounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/checar-username?username=${encodeURIComponent(username)}`);
          const data = await res.json();
          usernameValidAndAvailable = Boolean(data.available);
          if (regUserStatus) {
            regUserStatus.textContent = data.message || (data.available ? 'Usuário disponível!' : 'Usuário indisponível');
            regUserStatus.className = data.available ? 'reg-live-status reg-live-status--ok' : 'reg-live-status reg-live-status--err';
          }
        } catch (err) {
          console.warn('Erro ao checar username:', err);
        }
      }, 250);
    });
  }

  // Validação ao vivo da Senha (Card 3)
  if (regPasswordInput) {
    regPasswordInput.addEventListener('input', () => {
      const pwd = regPasswordInput.value;
      if (regConfirmHidden) regConfirmHidden.value = pwd;

      if (!pwd || pwd.length < 6) {
        if (regPwdStatus) {
          regPwdStatus.textContent = pwd.length > 0 ? `Faltam ${6 - pwd.length} caracteres (mínimo 6)` : '';
          regPwdStatus.className = 'reg-live-status reg-live-status--err';
          regPwdStatus.style.display = pwd.length > 0 ? 'block' : 'none';
        }
      } else {
        if (regPwdStatus) {
          regPwdStatus.textContent = 'Senha válida!';
          regPwdStatus.className = 'reg-live-status reg-live-status--ok';
          regPwdStatus.style.display = 'block';
        }
      }
    });
  }

  // Avanço entre os Passos do Wizard
  if (regBtnNext) {
    regBtnNext.addEventListener('click', async (e) => {
      e.preventDefault();
      triggerHaptic();

      // Card 1: Nome + E-mail
      if (currentRegStep === 1) {
        const nome = regNomeInput ? regNomeInput.value.trim() : '';
        const partes = nome.split(/\s+/).filter(Boolean);
        if (!nome || partes.length < 2) {
          showError('Por favor, digite seu nome e sobrenome.');
          return;
        }

        const email = regEmailInput ? regEmailInput.value.trim() : '';
        if (!email || !email.includes('@')) {
          showError('Por favor, informe um e-mail válido.');
          return;
        }

        // Sugerir Username para o Card 2 caso ainda esteja vazio
        try {
          const sugRes = await fetch(`/sugerir-username?nome=${encodeURIComponent(nome)}`);
          const sugData = await sugRes.json();
          if (sugData.suggestion && regUsernameInput && !regUsernameInput.value) {
            regUsernameInput.value = sugData.suggestion;
            usernameValidAndAvailable = Boolean(sugData.available);
            if (regUserStatus) {
              regUserStatus.textContent = sugData.message || 'Username sugerido disponível!';
              regUserStatus.className = sugData.available ? 'reg-live-status reg-live-status--ok' : 'reg-live-status reg-live-status--err';
              regUserStatus.style.display = 'block';
            }
          }
        } catch (sugErr) {
          console.warn('Erro ao obter sugestão de username:', sugErr);
        }

        goToRegStep(2);
        return;
      }

      // Card 2: Username + Posição
      if (currentRegStep === 2) {
        const username = regUsernameInput ? regUsernameInput.value.trim() : '';
        if (!username || username.length < 3) {
          showError('Escolha um nome de usuário com pelo menos 3 caracteres.');
          return;
        }

        goToRegStep(3);
        return;
      }

      // Card 3: Senha + Submissão
      if (currentRegStep === 3) {
        const pwd = regPasswordInput ? regPasswordInput.value : '';
        if (!pwd || pwd.length < 6) {
          showError('A senha deve ter pelo menos 6 caracteres.');
          return;
        }
        await window.submeterInlineCadastroClube();
        return;
      }
    });
  }

  if (regBtnPrev) {
    regBtnPrev.addEventListener('click', (e) => {
      e.preventDefault();
      triggerHaptic();
      goToRegStep(currentRegStep - 1);
    });
  }

  // Submissão Final do Wizard
  if (regForm) {
    regForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      triggerHaptic();
      await window.submeterInlineCadastroClube();
    });
  }

  // Resetar Wizard ao virar para o cadastro
  if (btnShowRegister) {
    btnShowRegister.addEventListener('click', () => {
      goToRegStep(1);
    });
  }
  const socialBtns = document.querySelectorAll('.js-social-login');
  const socialModal = document.getElementById('social-username-modal');
  const socialUsernameForm = document.getElementById('social-username-form');
  const socialEmailHidden = document.getElementById('social_email_hidden');
  const socialNomeHidden = document.getElementById('social_nome_hidden');
  const socialModalUserInfo = document.getElementById('social-modal-user-info');

  const socialAuthInputModal = document.getElementById('social-auth-input-modal');
  const socialAuthDirectForm = document.getElementById('social-auth-direct-form');
  const socialAuthProviderHidden = document.getElementById('social_auth_provider');
  const socialAuthEmailInput = document.getElementById('social_auth_email_input');
  const socialAuthNomeInput = document.getElementById('social_auth_nome_input');
  const socialAuthCancelBtn = document.getElementById('social-auth-cancel-btn');
  const socialProviderBadge = document.getElementById('social-provider-badge');
  const socialProviderTitle = document.getElementById('social-provider-title');
  const socialProviderSubtitle = document.getElementById('social-provider-subtitle');

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  async function submitSocialAuth(provider, email, nome, social_id) {
    try {
      const resp = await fetch('/social-login', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ provider, email, nome, social_id: social_id || `${provider}_${Date.now()}` })
      });
      const rawText = await resp.text();
      let data = {};
      try {
        data = JSON.parse(rawText);
      } catch (parseErr) {
        console.error('Resposta não-JSON de /social-login:', resp.status, rawText);
        alert(`Erro HTTP ${resp.status} no login social`);
        return;
      }

      if (data.success) {
        if (data.status === 'logged_in') {
          window.location.href = data.redirect_url || '/perfil';
        } else if (data.status === 'need_username') {
          if (socialEmailHidden) socialEmailHidden.value = data.email;
          if (socialNomeHidden) socialNomeHidden.value = data.nome;

          const autofillNome = document.getElementById('social-autofill-nome');
          if (autofillNome) autofillNome.textContent = data.nome || 'Atleta NaTrave';

          const autofillEmail = document.getElementById('social-autofill-email');
          if (autofillEmail) autofillEmail.textContent = data.email || '';

          const providerTag = document.getElementById('social-provider-imported-tag');
          if (providerTag) {
            providerTag.textContent = `✓ Autenticado via ${provider === 'apple' ? 'Apple ID' : 'Google'}`;
          }

          if (socialModalUserInfo) {
            socialModalUserInfo.textContent = `Olá, ${data.nome}! Seus dados foram autenticados via ${provider === 'apple' ? 'Apple ID' : 'Google'}. Confirme sua posição e escolha seu username no NaTrave:`;
          }
          const usernameInput = document.getElementById('social_username_input');
          if (usernameInput) {
            try {
              const sugRes = await fetch(`/sugerir-username?nome=${encodeURIComponent(data.nome || data.email)}`);
              const sugData = await sugRes.json();
              if (sugData && sugData.suggestion) {
                usernameInput.value = sugData.suggestion;
                usernameInput.dispatchEvent(new Event('input'));
              } else {
                const sugestao = (data.nome || (data.email ? data.email.split('@')[0] : '')).toLowerCase().replace(/[^a-z0-9_]/g, '');
                usernameInput.value = sugestao;
                usernameInput.dispatchEvent(new Event('input'));
              }
            } catch (sugErr) {
              const sugestao = (data.nome || (data.email ? data.email.split('@')[0] : '')).toLowerCase().replace(/[^a-z0-9_]/g, '');
              usernameInput.value = sugestao;
              usernameInput.dispatchEvent(new Event('input'));
            }
          }
          if (socialModal) socialModal.style.display = 'flex';
        }
      } else {
        alert(data.error || 'Erro no login social');
      }
    } catch (fetchErr) {
      console.error('Erro na requisição social-login:', fetchErr);
    }
  }

  function parseJwtEmail(token) {
    if (!token) return '';
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
      const payload = JSON.parse(jsonPayload);
      return payload.email || '';
    } catch (e) {
      return '';
    }
  }

  // Processa token retornado no fragmento da URL após OAuth do Google (ex: #access_token=...)
  if (window.location.hash && window.location.hash.includes('access_token=')) {
    try {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const accessToken = hashParams.get('access_token');
      if (accessToken) {
        history.replaceState(null, '', window.location.pathname + window.location.search);
        fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${accessToken}` }
        }).then(r => r.json()).then(async userInfo => {
          if (userInfo && userInfo.email) {
            await submitSocialAuth('google', userInfo.email, userInfo.name || 'Atleta Google', userInfo.sub || `google_${Date.now()}`);
          }
        }).catch(err => console.error('Erro ao ler token OAuth da URL:', err));
      }
    } catch (hErr) {
      console.warn('Erro ao processar hash OAuth:', hErr);
    }
  }

  function openSocialInputModal(provider) {
    if (!socialAuthInputModal) return;
    if (socialAuthProviderHidden) socialAuthProviderHidden.value = provider;

    if (provider === 'apple') {
      if (socialProviderBadge) socialProviderBadge.textContent = ' APPLE ID';
      if (socialProviderTitle) socialProviderTitle.textContent = 'Entrar com Apple';
      if (socialProviderSubtitle) socialProviderSubtitle.textContent = 'Conecte sua conta do Apple ID para entrar no NaTrave:';
    } else {
      if (socialProviderBadge) socialProviderBadge.textContent = '🌐 GOOGLE ACCOUNT';
      if (socialProviderTitle) socialProviderTitle.textContent = 'Entrar com Google';
      if (socialProviderSubtitle) socialProviderSubtitle.textContent = 'Conecte sua conta do Google para entrar no NaTrave:';
    }

    if (socialAuthEmailInput) socialAuthEmailInput.value = '';
    if (socialAuthNomeInput) socialAuthNomeInput.value = '';

    socialAuthInputModal.style.display = 'flex';
    if (socialAuthEmailInput) setTimeout(() => socialAuthEmailInput.focus(), 300);
  }

  socialBtns.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      triggerHaptic();
      const provider = (btn.getAttribute('data-provider') || 'google').toLowerCase();

      // 1. Fluxo de Autenticação Oficial com Apple ID
      if (provider === 'apple') {
        // 1a. Tenta Sign-In nativo do iOS (Xcode / Capacitor App Sheet Oficial da Apple)
        const applePlugin = (window.Capacitor && window.Capacitor.Plugins) ? 
          (window.Capacitor.Plugins.SignInWithApple || window.Capacitor.Plugins.AppleSignIn) : null;

        if (applePlugin) {
          try {
            const result = await applePlugin.authorize({
              clientId: window.APPLE_CLIENT_ID || 'pt.natrave.app',
              redirectURI: 'https://natrave.pt/social-login',
              scopes: 'email name',
              state: 'natrave_state',
              nonce: 'natrave_nonce'
            });
            const res = (result && result.response) ? result.response : (result || {});
            const social_id = res.user || `apple_${Date.now()}`;
            const extractedEmail = res.email || parseJwtEmail(res.identityToken) || `apple_${social_id.substring(0, 10)}@apple.com`;
            const nome = [res.givenName, res.familyName].filter(Boolean).join(' ') || 'Atleta Apple';
            if (extractedEmail || social_id) {
              await submitSocialAuth('apple', extractedEmail, nome, social_id);
              return;
            }
          } catch (err) {
            console.warn('Sign In with Apple nativo cancelado ou falhou:', err);
          }
        }

        // 1b. Tenta SDK Web Oficial da Apple ID em navegadores (Safari/Chrome/Web Popup)
        const clientId = window.APPLE_CLIENT_ID || 'pt.natrave.web';
        const redirectUri = window.location.origin + '/social-login';

        if (window.AppleID && window.AppleID.auth) {
          try {
            window.AppleID.auth.init({
              clientId: clientId,
              scope: 'name email',
              redirectURI: redirectUri,
              state: 'natrave_apple_state',
              usePopup: true
            });
            const res = await window.AppleID.auth.signIn();
            const userObj = res.user || {};
            const extractedEmail = (res.authorization ? parseJwtEmail(res.authorization.id_token) : '') || (userObj.email || '');
            const nome = userObj.name ? `${userObj.name.firstName || ''} ${userObj.name.lastName || ''}`.trim() : 'Atleta Apple';
            if (extractedEmail) {
              await submitSocialAuth('apple', extractedEmail, nome, `apple_${Date.now()}`);
              return;
            }
          } catch (e) {
            console.warn('AppleID Web SDK popup error, tentando redirecionamento:', e);
          }
        }

        // 1c. Fallback de Redirecionamento Oficial Web para o Apple ID OAuth 2.0 (na página oficial da Apple)
        const appleOAuthUrl = `https://appleid.apple.com/auth/authorize?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code%20id_token&scope=name%20email&response_mode=query`;
        window.location.href = appleOAuthUrl;
        return;
      }

      // 2. Fluxo de Autenticação com Google
      if (provider === 'google') {
        // 2a. Tenta Sign-In nativo do Google no iOS (Xcode / Capacitor GoogleAuth)
        const googlePlugin = (window.Capacitor && window.Capacitor.Plugins) ? window.Capacitor.Plugins.GoogleAuth : null;
        if (googlePlugin) {
          try {
            const clientId = window.GOOGLE_CLIENT_ID || '87998320853-mfkte5ili1uuvud8jdq6pvcp0kmknhrs.apps.googleusercontent.com';
            if (typeof googlePlugin.initialize === 'function') {
              await googlePlugin.initialize({
                clientId: clientId,
                scopes: ['profile', 'email'],
                grantOfflineAccess: true
              });
            }
            const result = await googlePlugin.signIn();
            const email = result.email || '';
            const nome = result.name || result.displayName || 'Atleta NaTrave';
            const social_id = result.id || `google_${Date.now()}`;
            if (email) {
              await submitSocialAuth('google', email, nome, social_id);
              return;
            }
          } catch (err) {
            console.warn('Google Sign-In nativo cancelado ou falhou:', err);
          }
        }

        // 2b. Tenta SDK Web / GIS Oficial do Google
        const clientId = window.GOOGLE_CLIENT_ID || '87998320853-mfkte5ili1uuvud8jdq6pvcp0kmknhrs.apps.googleusercontent.com';
        if (window.google && window.google.accounts && window.google.accounts.oauth2) {
          try {
            const client = window.google.accounts.oauth2.initTokenClient({
              client_id: clientId,
              scope: 'email profile',
              callback: async (tokenResponse) => {
                if (tokenResponse && tokenResponse.access_token) {
                  try {
                    const userInfo = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                      headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
                    }).then(r => r.json());
                    if (userInfo && userInfo.email) {
                      await submitSocialAuth('google', userInfo.email, userInfo.name || 'Atleta Google', userInfo.sub || `google_${Date.now()}`);
                    }
                  } catch (userErr) {
                    console.error('Erro ao buscar perfil do Google:', userErr);
                  }
                }
              }
            });
            client.requestAccessToken();
            return;
          } catch (gErr) {
            console.warn('Google GIS SDK erro:', gErr);
          }
        }

        // 2c. Fallback de Redirecionamento Oficial Web para o Google OAuth 2.0
        const googleOAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(window.location.origin + '/login')}&response_type=token&scope=email%20profile`;
        window.location.href = googleOAuthUrl;
        return;
      }
    });
  });

  if (socialAuthCancelBtn && socialAuthInputModal) {
    socialAuthCancelBtn.addEventListener('click', () => {
      socialAuthInputModal.style.display = 'none';
    });
  }

  if (socialAuthDirectForm) {
    socialAuthDirectForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      triggerHaptic();
      const provider = socialAuthProviderHidden ? socialAuthProviderHidden.value : 'google';
      const email = socialAuthEmailInput ? socialAuthEmailInput.value.trim() : '';
      const nome = socialAuthNomeInput ? socialAuthNomeInput.value.trim() : '';

      if (!email) return;

      if (socialAuthInputModal) socialAuthInputModal.style.display = 'none';
      await submitSocialAuth(provider, email, nome || (provider === 'apple' ? 'Atleta Apple' : 'Atleta Google'), `${provider}_${Date.now()}`);
    });
  }

  // Verificador instantâneo de disponibilidade de @username em tempo real
  const socialUsernameInput = document.getElementById('social_username_input');
  const usernameStatus = document.getElementById('social_username_status');
  const usernameBtn = document.getElementById('social_username_btn');
  let checkDebounceTimer = null;

  if (socialUsernameInput) {
    socialUsernameInput.addEventListener('input', () => {
      const val = socialUsernameInput.value.trim();
      if (checkDebounceTimer) clearTimeout(checkDebounceTimer);

      if (!val || val.length < 3) {
        if (usernameStatus) {
          usernameStatus.textContent = val.length > 0 ? '⚠ Mínimo de 3 caracteres' : '';
          usernameStatus.style.color = '#f59e0b';
        }
        if (usernameBtn) {
          usernameBtn.disabled = true;
          usernameBtn.style.opacity = '0.5';
        }
        return;
      }

      checkDebounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/checar-username?username=${encodeURIComponent(val)}`);
          const data = await res.json();
          if (usernameStatus) {
            usernameStatus.textContent = data.message || '';
            usernameStatus.style.color = data.available ? '#10b981' : '#ef4444';
          }
          if (usernameBtn) {
            usernameBtn.disabled = !data.available;
            usernameBtn.style.opacity = data.available ? '1' : '0.5';
          }
        } catch (err) {
          console.warn('Erro ao checar username:', err);
        }
      }, 250);
    });
  }

  if (socialUsernameForm) {
    socialUsernameForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      triggerHaptic();
      const email = socialEmailHidden ? socialEmailHidden.value : '';
      const nome = socialNomeHidden ? socialNomeHidden.value : '';
      const val = socialUsernameInput ? socialUsernameInput.value.trim() : '';
      const posicaoSelect = document.getElementById('social_posicao_select');
      const posicao = posicaoSelect ? posicaoSelect.value : 'linha';

      if (!val) return;

      try {
        const resp = await fetch('/social-complete-username', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({ email, nome, username: val, posicao: posicao })
        });
        const data = await resp.json();
        if (data.success && data.redirect_url) {
          window.location.href = data.redirect_url;
        } else {
          alert(data.error || 'Erro ao criar conta com username');
        }
      } catch (err) {
        alert('Erro de conexão ao concluir cadastro');
      }
    });
  }

  const initEmail = socialEmailHidden ? socialEmailHidden.value.trim() : '';
  const initNome = socialNomeHidden ? socialNomeHidden.value.trim() : '';
  const initProvider = (document.getElementById('social_provider_hidden')?.value || 'apple').trim();
  const initSocialId = (document.getElementById('social_id_hidden')?.value || '').trim();

  if (initEmail) {
    submitSocialAuth(initProvider, initEmail, initNome, initSocialId);
  }

  updateCard(0);
});

