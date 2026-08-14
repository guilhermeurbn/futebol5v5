/**
 * ⚽ NATRAVE 5v5 - CONTROLLER DE ONBOARDING & MODO APP
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

  // Animação 3D Flip do Card (Login x Cadastro)
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
          if (socialModalUserInfo) {
            socialModalUserInfo.textContent = `Olá, ${data.nome}! O seu e-mail foi autenticado via ${provider === 'apple' ? 'Apple ID' : 'Google'}. Escolha o seu @username no NaTrave:`;
          }
          const usernameInput = document.getElementById('social_username_input');
          if (usernameInput) {
            const sugestao = (data.nome || (data.email ? data.email.split('@')[0] : '')).toLowerCase().replace(/[^a-z0-9_]/g, '');
            usernameInput.value = sugestao;
            usernameInput.dispatchEvent(new Event('input'));
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

  socialBtns.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      triggerHaptic();
      const provider = (btn.getAttribute('data-provider') || 'google').toLowerCase();

      // 1. Fluxo de Autenticação com Apple ID
      if (provider === 'apple') {
        // 1a. Tenta Sign-In nativo do iOS (Xcode / Capacitor App Sheet Oficial da Apple)
        const applePlugin = (window.Capacitor && window.Capacitor.Plugins) ? 
          (window.Capacitor.Plugins.SignInWithApple || window.Capacitor.Plugins.AppleSignIn) : null;

        if (applePlugin) {
          try {
            const result = await applePlugin.authorize({
              clientId: 'pt.natrave.app',
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

        // 1b. Tenta SDK Web Oficial da Apple ID em navegadores (Safari/Chrome/Web)
        if (window.AppleID && window.AppleID.auth) {
          try {
            window.AppleID.auth.init({
              clientId: 'pt.natrave.app',
              scope: 'name email',
              redirectURI: window.location.origin + '/social-login',
              state: 'natrave_state',
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
            console.warn('AppleID Web SDK error:', e);
          }
        }
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

      if (!val) return;

      try {
        const resp = await fetch('/social-complete-username', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({ email, nome, username: val })
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

