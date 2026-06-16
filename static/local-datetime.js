(function () {
  function getLocale() {
    return (navigator.languages && navigator.languages[0]) || navigator.language || 'pt-BR';
  }

  function parseDate(value, dateOnly) {
    if (!value) return null;
    const normalized = dateOnly && !String(value).includes('T')
      ? String(value) + 'T00:00:00'
      : String(value);
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatDate(date, locale) {
    return new Intl.DateTimeFormat(locale, {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit'
    }).format(date);
  }

  function formatTime(date, locale) {
    return new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      hourCycle: 'h23'
    }).format(date);
  }

  function applyLocalDates(root) {
    const scope = root || document;
    const locale = getLocale();

    scope.querySelectorAll('[data-local-date]').forEach(function (element) {
      const date = parseDate(element.getAttribute('data-local-date'), true);
      if (!date) return;
      element.textContent = formatDate(date, locale);
      element.setAttribute('title', Intl.DateTimeFormat().resolvedOptions().timeZone || '');
    });

    scope.querySelectorAll('[data-local-datetime]').forEach(function (element) {
      const date = parseDate(element.getAttribute('data-local-datetime'), false);
      if (!date) return;
      element.textContent = formatDate(date, locale) + ' ' + formatTime(date, locale);
      element.setAttribute('title', Intl.DateTimeFormat().resolvedOptions().timeZone || '');
    });
  }

  window.NaTraveLocalDateTime = {
    apply: applyLocalDates,
    formatDateTime: function (value) {
      const date = parseDate(value, false);
      if (!date) return value || '';
      const locale = getLocale();
      return formatDate(date, locale) + ' ' + formatTime(date, locale);
    },
    formatDate: function (value) {
      const date = parseDate(value, true);
      if (!date) return value || '';
      return formatDate(date, getLocale());
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      applyLocalDates(document);
    });
  } else {
    applyLocalDates(document);
  }
})();
