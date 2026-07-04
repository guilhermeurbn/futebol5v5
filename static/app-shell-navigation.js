(function () {
  if (window.NaTraveAppShellNav) return;

  var pageCache = new Map();
  var stateCache = new Map();
  var MAX_CACHE_ENTRIES = 24;
  var navCounter = 0;
  var pageHookRegistry = [];

  function pageKeyFromUrl(url) {
    var parsed = new URL(url, window.location.origin);
    return parsed.pathname + parsed.search;
  }

  function currentPageKey() {
    return pageKeyFromUrl(window.location.href);
  }

  function getAppContent() {
    return document.querySelector('[data-app-content]');
  }

  function trimCache(cache) {
    while (cache.size > MAX_CACHE_ENTRIES) {
      var oldestKey = cache.keys().next().value;
      cache.delete(oldestKey);
    }
  }

  function normalizeClassTokens(value) {
    return String(value || '')
      .split(/\s+/)
      .map(function (token) { return token.trim(); })
      .filter(Boolean);
  }

  function ensureCsrf(root) {
    if (window.NaTraveCSRF && typeof window.NaTraveCSRF.ensureFormTokens === 'function') {
      window.NaTraveCSRF.ensureFormTokens(root);
    }
  }

  function getFieldIdentifier(el, indexByName) {
    if (el.id) return 'id:' + el.id;

    var name = el.getAttribute('name');
    if (name) {
      var idx = indexByName[name] || 0;
      indexByName[name] = idx + 1;
      return 'name:' + name + ':' + idx;
    }

    return null;
  }

  function captureFieldState(root) {
    var fields = Array.from(root.querySelectorAll('input, select, textarea'));
    var indexByName = {};
    var state = {};

    fields.forEach(function (el) {
      var key = getFieldIdentifier(el, indexByName);
      if (!key || el.disabled) return;

      var tag = el.tagName.toLowerCase();
      var type = (el.getAttribute('type') || '').toLowerCase();

      if (tag === 'input' && (type === 'checkbox' || type === 'radio')) {
        state[key] = { checked: !!el.checked };
        return;
      }

      if (tag === 'select' && el.multiple) {
        state[key] = {
          values: Array.from(el.selectedOptions).map(function (opt) { return opt.value; })
        };
        return;
      }

      state[key] = { value: el.value };
    });

    return state;
  }

  function restoreFieldState(root, fieldState) {
    if (!fieldState) return;

    var fields = Array.from(root.querySelectorAll('input, select, textarea'));
    var indexByName = {};

    fields.forEach(function (el) {
      var key = getFieldIdentifier(el, indexByName);
      if (!key || !Object.prototype.hasOwnProperty.call(fieldState, key)) return;

      var value = fieldState[key];
      var tag = el.tagName.toLowerCase();
      var type = (el.getAttribute('type') || '').toLowerCase();

      if (tag === 'input' && (type === 'checkbox' || type === 'radio')) {
        el.checked = !!value.checked;
      } else if (tag === 'select' && el.multiple && Array.isArray(value.values)) {
        Array.from(el.options).forEach(function (opt) {
          opt.selected = value.values.indexOf(opt.value) >= 0;
        });
      } else if (typeof value.value === 'string') {
        el.value = value.value;
      }

      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  function saveStateFor(url) {
    var content = getAppContent();
    if (!content) return;

    var key = pageKeyFromUrl(url);
    stateCache.set(key, {
      scrollY: window.scrollY,
      fields: captureFieldState(content)
    });
    trimCache(stateCache);
  }

  function restoreStateFor(url, options) {
    var content = getAppContent();
    if (!content) return;

    var key = pageKeyFromUrl(url);
    var state = stateCache.get(key);

    if (state) {
      restoreFieldState(content, state.fields);
    }

    if (options && options.fromPop && state) {
      window.scrollTo(0, state.scrollY || 0);
      return;
    }

    window.scrollTo(0, 0);
  }

  function sameOriginUrl(href) {
    try {
      var url = new URL(href, window.location.href);
      return url.origin === window.location.origin ? url : null;
    } catch (error) {
      return null;
    }
  }

  function extractPagePayload(html, url) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(html, 'text/html');
    var content = doc.querySelector('[data-app-content]');
    if (!content) return null;

    return {
      url: new URL(url, window.location.href).href,
      key: pageKeyFromUrl(url),
      title: doc.title,
      bodyClass: doc.body ? doc.body.className : document.body.className,
      contentHtml: content.innerHTML
    };
  }

  function fetchPage(url) {
    var key = pageKeyFromUrl(url);
    if (pageCache.has(key)) return Promise.resolve(pageCache.get(key));

    return fetch(url, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Navigation fetch failed: ' + res.status);
        return res.text();
      })
      .then(function (html) {
        var payload = extractPagePayload(html, url);
        if (!payload) throw new Error('Unable to parse app content from response');
        pageCache.set(key, payload);
        trimCache(pageCache);
        return payload;
      });
  }

  function executeInlineScripts(root) {
    var scripts = Array.from(root.querySelectorAll('script'));
    scripts.forEach(function (oldScript) {
      var newScript = document.createElement('script');

      Array.from(oldScript.attributes).forEach(function (attr) {
        newScript.setAttribute(attr.name, attr.value);
      });

      if (oldScript.textContent) {
        newScript.textContent = oldScript.textContent;
      }

      oldScript.replaceWith(newScript);
    });
  }

  function updateBodyClass(nextBodyClass) {
    var nextTokens = normalizeClassTokens(nextBodyClass);
    var merged = new Set(nextTokens);

    merged.add('app-shell');

    ['has-mobile-dock', 'is-swipe-preview', 'is-nav-loading'].forEach(function (cls) {
      if (document.body.classList.contains(cls)) {
        merged.add(cls);
      }
    });

    document.body.className = Array.from(merged).join(' ');
  }

  function registerPageHook(hook) {
    if (typeof hook === 'function') {
      pageHookRegistry.push({
        init: hook
      });
      return;
    }

    if (!hook || typeof hook.init !== 'function') return;
    pageHookRegistry.push(hook);
  }

  function runPageHooks(url) {
    var context = {
      url: url,
      pathname: new URL(url, window.location.href).pathname,
      root: getAppContent()
    };

    pageHookRegistry.forEach(function (hook) {
      try {
        if (typeof hook.test === 'function' && !hook.test(context)) return;
        hook.init(context);
      } catch (error) {
        console.warn('Page hook failed', error);
      }
    });

    document.dispatchEvent(new CustomEvent('natrave:page-init', {
      detail: context
    }));
  }

  function renderPayload(payload, options) {
    var content = getAppContent();
    if (!content) return;

    content.innerHTML = payload.contentHtml;
    document.title = payload.title;
    updateBodyClass(payload.bodyClass);
    ensureCsrf(content);
    executeInlineScripts(content);

    if (window.NaTraveMobileNav && typeof window.NaTraveMobileNav.refresh === 'function') {
      window.NaTraveMobileNav.refresh();
    }

    restoreStateFor(payload.url, {
      fromPop: !!(options && options.fromPop)
    });

    runPageHooks(payload.url);

    document.dispatchEvent(new CustomEvent('natrave:navigation-complete', {
      detail: {
        url: payload.url,
        fromPop: !!(options && options.fromPop)
      }
    }));
  }

  function shouldUseTransition() {
    return (
      typeof document.startViewTransition === 'function' &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function prefetchLikelyTargets(root) {
    var scope = root instanceof Element ? root : document;
    var links = Array.from(scope.querySelectorAll('.nav-tabs .nav-tab[href], a[data-prefetch][href]'));

    links.slice(0, 6).forEach(function (link) {
      var url = sameOriginUrl(link.href);
      if (!url) return;
      var key = pageKeyFromUrl(url.href);
      if (key === currentPageKey() || pageCache.has(key)) return;
      fetchPage(url.href).catch(function () {});
    });
  }

  function setLoading(loading) {
    document.body.classList.toggle('is-nav-loading', !!loading);
  }

  function navigateTo(url, options) {
    options = options || {};
    var parsed = sameOriginUrl(url);
    if (!parsed) {
      window.location.href = url;
      return Promise.resolve(false);
    }

    var targetHref = parsed.href;
    var targetKey = pageKeyFromUrl(targetHref);
    var currentKey = currentPageKey();

    if (!options.fromPop && targetKey === currentKey) {
      if (parsed.hash) {
        var targetId = parsed.hash.slice(1);
        var hashTarget = targetId ? document.getElementById(targetId) : null;
        if (hashTarget) {
          hashTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
      return Promise.resolve(false);
    }

    saveStateFor(window.location.href);
    setLoading(true);
    var currentNavToken = ++navCounter;

    return fetchPage(targetHref)
      .then(function (payload) {
        if (currentNavToken !== navCounter) return;

        var doRender = function () {
          renderPayload(payload, options);
        };

        if (shouldUseTransition()) {
          var vt = document.startViewTransition(doRender);
          return vt.finished.catch(function () {});
        }

        doRender();
      })
      .then(function () {
        if (currentNavToken !== navCounter) return;

        if (!options.fromPop) {
          if (options.replace) {
            history.replaceState({ appShell: true }, '', targetHref);
          } else {
            history.pushState({ appShell: true }, '', targetHref);
          }
        }

        prefetchLikelyTargets(getAppContent());
      })
      .catch(function () {
        window.location.href = targetHref;
      })
      .finally(function () {
        if (currentNavToken === navCounter) {
          setLoading(false);
        }
      });
  }

  function isNavigableAnchor(anchor, event) {
    if (!anchor || !anchor.href) return false;
    if (anchor.target && anchor.target !== '_self') return false;
    if (anchor.hasAttribute('download')) return false;
    if (anchor.getAttribute('rel') === 'external') return false;
    if (anchor.dataset.noSpa != null) return false;
    if (event.defaultPrevented) return false;
    if (event.button !== 0) return false;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;

    var url = sameOriginUrl(anchor.href);
    if (!url) return false;
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return false;

    if (url.hash && pageKeyFromUrl(url.href) === currentPageKey()) {
      return false;
    }

    return true;
  }

  function installNavigationListeners() {
    document.addEventListener('click', function (event) {
      var target = event.target;
      if (!(target instanceof Element)) return;
      var anchor = target.closest('a[href]');
      if (!isNavigableAnchor(anchor, event)) return;

      event.preventDefault();
      navigateTo(anchor.href, { replace: false });
    });

    window.addEventListener('popstate', function () {
      navigateTo(window.location.href, { fromPop: true, replace: true });
    });

    function prefetchFromEvent(event) {
      var target = event.target;
      if (!(target instanceof Element)) return;
      var anchor = target.closest('a[href]');
      if (!anchor) return;

      var url = sameOriginUrl(anchor.href);
      if (!url) return;
      var key = pageKeyFromUrl(url.href);
      if (key === currentPageKey() || pageCache.has(key)) return;
      fetchPage(url.href).catch(function () {});
    }

    document.addEventListener('pointerenter', prefetchFromEvent, true);
    document.addEventListener('touchstart', prefetchFromEvent, { passive: true, capture: true });
  }

  function init() {
    var content = getAppContent();
    if (!content) return;

    if ('scrollRestoration' in history) {
      history.scrollRestoration = 'manual';
    }

    saveStateFor(window.location.href);
    installNavigationListeners();
    prefetchLikelyTargets(content);
    runPageHooks(window.location.href);
  }

  window.NaTraveAppShellNav = {
    init: init,
    navigateTo: navigateTo,
    registerPageHook: registerPageHook,
    prefetch: function (url) {
      return fetchPage(url);
    }
  };

  window.NaTravePageHooks = Object.assign({}, window.NaTravePageHooks, {
    register: registerPageHook
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
