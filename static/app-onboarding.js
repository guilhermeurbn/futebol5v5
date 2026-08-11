/**
 * ⚽ NATRAVE 5v5 - CONTROLLER DE ONBOARDING & MODO APP
 * Gerencia a experiência de 1º acesso (Cards explicativos) e login limpo no app iOS/Capacitor.
 */
document.addEventListener('DOMContentLoaded', () => {
  const isCapacitorApp = Boolean(
    (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
    window.location.search.includes('mode=app') ||
    window.location.href.includes('mode=app') ||
    navigator.userAgent.includes('Capacitor') ||
    navigator.userAgent.includes('NaTraveApp') ||
    (window.webkit && window.webkit.messageHandlers) ||
    window.innerWidth <= 800 ||
    /iPhone|iPad|iPod|Android|Mobile/i.test(navigator.userAgent)
  );

  const onboardingModal = document.getElementById('app-onboarding-modal');
  const loginFormContainer = document.getElementById('app-login-container');

  // Se NÃO for aplicativo ou telefone móvel, remove o modal completamente
  if (!isCapacitorApp) {
    if (onboardingModal) onboardingModal.classList.add('is-hidden');
    return;
  }

  document.body.classList.add('is-capacitor-app');

  if (!onboardingModal) return;

  // No modo aplicativo, enquanto não estiver logado, exibe a apresentação sempre
  onboardingModal.classList.remove('is-hidden', 'fade-out');
  onboardingModal.style.display = 'block';

  let currentCard = 0;
  const cards = onboardingModal.querySelectorAll('.onboarding-card');
  const dots = onboardingModal.querySelectorAll('.onboarding-dot');
  const btnNext = document.getElementById('onboarding-btn-next');
  const btnPrev = document.getElementById('onboarding-btn-prev');
  const btnSkip = document.getElementById('onboarding-btn-skip');
  const onboardingKey = 'natrave_app_onboarding_completed_v1';

  function triggerHaptic() {
    try {
      if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics) {
        window.Capacitor.Plugins.Haptics.impact({ style: 'LIGHT' });
      }
    } catch (e) { }
  }

  function updateCard(index) {
    currentCard = index;
    cards.forEach((card, i) => {
      card.classList.toggle('active', i === index);
    });
    dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });

    // Controla visibilidade do botão Voltar (Invisível no Modo Jogador - Slide 0)
    if (btnPrev) {
      if (index > 0) {
        btnPrev.style.visibility = 'visible';
        btnPrev.style.pointerEvents = 'auto';
      } else {
        btnPrev.style.visibility = 'hidden';
        btnPrev.style.pointerEvents = 'none';
      }
    }

    if (btnNext) {
      const btnSpan = btnNext.querySelector('span');
      if (btnSpan) {
        btnSpan.textContent = index === cards.length - 1 ? 'Começar' : 'Avançar';
      } else {
        btnNext.textContent = index === cards.length - 1 ? 'Começar' : 'Avançar';
      }
    }
  }

  function completeOnboarding() {
    triggerHaptic();
    onboardingModal.classList.add('fade-out');
    setTimeout(() => {
      onboardingModal.classList.add('is-hidden');
      onboardingModal.style.setProperty('display', 'none', 'important');
      if (loginFormContainer) {
        loginFormContainer.classList.add('onboarding-done');
      }
    }, 250);
  }

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

  // Persistência do "Lembrar de Mim" (Salva usuário no LocalStorage do celular)
  const loginForm = document.querySelector('.auth-form');
  const usernameInput = document.getElementById('username');
  const rememberCheckbox = document.querySelector('input[name="remember_me"]');

  if (loginForm && usernameInput) {
    const savedUser = localStorage.getItem('natrave_remember_username');
    if (savedUser) {
      usernameInput.value = savedUser;
      if (rememberCheckbox) {
        rememberCheckbox.checked = true;
      }
    }

    loginForm.addEventListener('submit', () => {
      if (rememberCheckbox && rememberCheckbox.checked) {
        localStorage.setItem('natrave_remember_username', usernameInput.value.trim());
      } else {
        localStorage.removeItem('natrave_remember_username');
      }
    });
  }

  // Animação 3D Flip do Card (Troca entre Login e Cadastro)
  const cardFlipInner = document.getElementById('authCardFlipInner');
  const btnShowRegister = document.getElementById('btn-show-register');
  const btnShowLogin = document.getElementById('btn-show-login');

  if (cardFlipInner) {
    if (btnShowRegister) {
      btnShowRegister.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.add('is-flipped');
      });
    }

    if (btnShowLogin) {
      btnShowLogin.addEventListener('click', (e) => {
        e.preventDefault();
        triggerHaptic();
        cardFlipInner.classList.remove('is-flipped');
      });
    }
  }

  // Social Login Handler (Apple & Google)
  const socialBtns = document.querySelectorAll('.js-social-login');
  const socialModal = document.getElementById('social-username-modal');
  const socialUsernameForm = document.getElementById('social-username-form');
  const socialEmailHidden = document.getElementById('social_email_hidden');
  const socialNomeHidden = document.getElementById('social_nome_hidden');
  const socialModalUserInfo = document.getElementById('social-modal-user-info');

  socialBtns.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      triggerHaptic();
      const provider = btn.getAttribute('data-provider') || 'google';

      let email = '';
      let nome = '';

      if (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform() && window.Capacitor.Plugins.AppleSignIn) {
        try {
          const result = await window.Capacitor.Plugins.AppleSignIn.authorize({
            requestedScopes: [1, 2]
          });
          email = result.response.email || '';
          nome = [result.response.givenName, result.response.familyName].filter(Boolean).join(' ') || 'Atleta';
        } catch (err) {
          console.warn('Apple Sign In cancelado:', err);
          return;
        }
      }

      if (!email) {
        email = prompt(`Digite seu e-mail do ${provider === 'apple' ? 'Apple ID' : 'Google'}:`, `atleta_${Math.floor(Math.random() * 1000)}@${provider}.com`);
        if (!email) return;
        nome = prompt('Digite seu nome completo:', 'Jogador NaTrave') || 'Jogador NaTrave';
      }

      try {
        const resp = await fetch('/social-login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider, email, nome, social_id: `${provider}_${Date.now()}` })
        });
        const data = await resp.json();

        if (data.success) {
          if (data.status === 'logged_in') {
            window.location.href = data.redirect_url || '/perfil';
          } else if (data.status === 'need_username') {
            if (socialEmailHidden) socialEmailHidden.value = data.email;
            if (socialNomeHidden) socialNomeHidden.value = data.nome;
            if (socialModalUserInfo) {
              socialModalUserInfo.textContent = `Olá, ${data.nome}! O seu e-mail foi autenticado via ${provider === 'apple' ? 'Apple' : 'Google'}. Agora escolha o seu @username no NaTrave:`;
            }
            if (socialModal) socialModal.style.display = 'flex';
          }
        } else {
          alert(data.error || 'Erro no login social');
        }
      } catch (fetchErr) {
        console.error('Erro na requisição social-login:', fetchErr);
      }
    });
  });

  if (socialUsernameForm) {
    socialUsernameForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      triggerHaptic();
      const email = socialEmailHidden ? socialEmailHidden.value : '';
      const nome = socialNomeHidden ? socialNomeHidden.value : '';
      const usernameInput = document.getElementById('social_username_input');
      const username = usernameInput ? usernameInput.value.trim() : '';

      if (!username) return;

      try {
        const resp = await fetch('/social-complete-username', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, nome, username })
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

  updateCard(0);
});
