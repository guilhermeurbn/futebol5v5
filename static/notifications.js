/* ============================================================
   🔔 NATRAVE 5v5 - NOTIFICAÇÕES LOCAIS (Capacitor / iOS)
   ============================================================ */
(function () {
  window.scheduleLocalNotification = async function (title, body, delaySeconds) {
    delaySeconds = delaySeconds || 1;
    try {
      if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.LocalNotifications) {
        const perm = await window.Capacitor.Plugins.LocalNotifications.requestPermissions();
        if (perm.display === 'granted') {
          await window.Capacitor.Plugins.LocalNotifications.schedule({
            notifications: [
              {
                title: title || 'NaTrave 5v5',
                body: body || 'A votação do jogo está disponível!',
                id: Math.floor(Date.now() / 1000),
                schedule: { at: new Date(Date.now() + delaySeconds * 1000) },
                sound: null,
                attachments: null,
                actionTypeId: '',
                extra: null
              }
            ]
          });
        }
      } else if ('Notification' in window && Notification.permission === 'granted') {
        setTimeout(() => {
          new Notification(title || 'NaTrave 5v5', { body: body || 'A votação do jogo está disponível!' });
        }, delaySeconds * 1000);
      }
    } catch (e) {
      console.warn('Local Notification error:', e);
    }
  };
})();
