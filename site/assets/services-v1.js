/* Explicit opt-in. No SDK, tracker request, or chat connection before consent. */
(() => {
  'use strict';
  const configNode = document.getElementById('site-service-config');
  if (!configNode) return;
  let config;
  try { config = JSON.parse(configNode.textContent); } catch (_) { return; }
  const hasAnalytics = /^G-[A-Z0-9]{6,20}$/.test(config.ga4Id || '');
  const hasChat = /^[A-Za-z0-9]{5,40}$/.test(config.jivoId || '') && config.jivoApproved === true;
  if (!hasAnalytics && !hasChat) return;
  const networkAllowed = config.networkEnabled === true && location.protocol === 'https:' &&
    location.hostname === 'eglitisonline.com' &&
    !document.querySelector('meta[name="robots"]')?.content.includes('noindex');
  const storageKey = 'eglitisonline.privacy';
  const maxAge = 180 * 24 * 60 * 60 * 1000;
  const paths = {'/': 'Главная', '/about.html': 'Обо мне', '/approach.html': 'Подход',
    '/prices.html': 'Цены', '/articles.html': 'Статьи', '/contact.html': 'Контакты',
    '/privacy.html': 'Приватность', '/terms.html': 'Условия',
    '/articles/kak-ponyat-problemu.html': 'Статья 1', '/articles/kak-brosit-pit.html': 'Статья 2'};
  let choice = null;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved?.version === config.consentVersion && typeof saved.analytics === 'boolean' &&
        Number.isFinite(saved.time) && Date.now() >= saved.time && Date.now() - saved.time < maxAge) choice = saved;
  } catch (_) { /* Storage unavailable: deny until explicit choice in this document. */ }
  let analyticsAllowed = hasAnalytics && choice?.analytics === true;
  let analyticsLoaded = false;
  let chatLoaded = false;
  let chatLoading = false;
  let chatRequested = false;
  let pendingChat = false;
  let opener = null;
  let loadTimeout;

  const privacyLink = '/privacy.html#services';
  const status = document.createElement('p');
  status.className = 'service-status'; status.setAttribute('role', 'status');
  document.querySelector('.footer-contact')?.append(status);
  const announce = message => { status.textContent = message; };

  const store = analytics => {
    choice = {version: config.consentVersion, analytics, time: Date.now()};
    try { localStorage.setItem(storageKey, JSON.stringify(choice)); } catch (_) {}
  };
  const safeReferrer = () => {
    try {
      const url = new URL(document.referrer);
      return /^(www\.)?(google\.(com|ru|fi|lv)|bing\.com|t\.me|telegram\.org|facebook\.com|vk\.com|eglitisonline\.com)$/.test(url.hostname)
        ? url.origin + '/' : '';
    } catch (_) { return ''; }
  };
  const pageFields = () => ({page_location: 'https://eglitisonline.com' + (paths[location.pathname] ? location.pathname : '/'),
    page_title: paths[location.pathname] || 'Сайт', page_referrer: safeReferrer()});
  // Campaign values are fixed enums, never user-entered free text or ad identifiers.
  const campaign = {};
  const query = new URLSearchParams(location.search);
  const campaignEnums = {utm_source: ['telegram', 'whatsapp', 'max', 'google', 'bing', 'partner'],
    utm_medium: ['social', 'referral', 'cpc', 'email'], utm_campaign: ['launch_2026', 'articles_2026', 'partners_2026']};
  Object.entries(campaignEnums).forEach(([key, allowed]) => {
    const value = query.get(key);
    if (allowed.includes(value)) campaign[{utm_source: 'campaign_source', utm_medium: 'campaign_medium',
      utm_campaign: 'campaign_name'}[key]] = value;
  });
  const event = (name, fields = {}) => {
    if (!networkAllowed || !analyticsAllowed || !analyticsLoaded) return;
    window.gtag('event', name, {...pageFields(), ...fields, send_to: config.ga4Id});
  };
  const loadAnalytics = () => {
    if (!networkAllowed || !analyticsAllowed || analyticsLoaded) return;
    // Provider SDKs also inspect document.location; remove arbitrary text before loading.
    if (location.search || location.hash) history.replaceState(null, '', location.pathname);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('consent', 'default', {analytics_storage: 'denied', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied'});
    window.gtag('consent', 'update', {analytics_storage: 'granted', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied'});
    window.gtag('js', new Date());
    window.gtag('config', config.ga4Id, {send_page_view: false, allow_google_signals: false,
      allow_ad_personalization_signals: false, cookie_expires: 90 * 24 * 60 * 60,
      cookie_update: false, ...pageFields(), ...campaign});
    const tag = document.createElement('script'); tag.async = true;
    tag.src = 'https://www.googletagmanager.com/gtag/js?id=' + config.ga4Id;
    tag.referrerPolicy = 'no-referrer';
    tag.onerror = () => { analyticsLoaded = false; };
    document.head.append(tag); analyticsLoaded = true;
    event('page_view');
  };
  const clearProviderCookies = () => {
    document.cookie.split(';').forEach(cookie => {
      const name = cookie.trim().split('=')[0];
      if (!/^(_ga($|_)|_gid$|_gat|_gcl_|jv_|jv|JIVO)/.test(name)) return;
      ['', 'eglitisonline.com', '.eglitisonline.com'].forEach(domain => {
        document.cookie = name + '=; Max-Age=0; path=/; SameSite=Lax' + (domain ? '; domain=' + domain : '');
      });
    });
  };
  // The provider may rewrite its session cookie during the old document's unload.
  // Remove residual cookies again in the new document when consent is absent.
  if (!analyticsAllowed) clearProviderCookies();

  const dialog = document.createElement('dialog');
  dialog.className = 'privacy-dialog'; dialog.setAttribute('aria-labelledby', 'privacy-heading');
  dialog.innerHTML = '<h2 id="privacy-heading">Настройки приватности</h2>' +
    '<p>Сайт и мессенджеры доступны независимо от выбранных настроек.</p>' +
    (hasAnalytics ? '<label class="consent-option"><input id="analytics-choice" type="checkbox"><span>Разрешить статистику посещений Google Analytics.</span></label><p class="consent-detail">Учитываются просмотры и выбор способа связи. Содержание переписки, контакты и сведения о здоровье в статистику не отправляются.</p>' : '') +
    (hasChat ? '<div class="chat-consent"><h3>Чат на сайте</h3><p>Чат работает через Jivo. Для записи достаточно организационного вопроса; медицинскую историю отправлять не нужно.</p><label class="consent-option"><input id="chat-choice" type="checkbox"><span>Я явно соглашаюсь на обработку моего сообщения и технических данных Владимиром Эглитисом через Jivo, включая сведения о здоровье, если я сам решу их сообщить.</span></label></div>' : '') +
    '<p><a href="' + privacyLink + '">Подробнее об обработке данных</a>. Согласие можно отозвать в этих настройках или написать на email из политики.</p><p class="consent-error" role="alert" hidden></p>' +
    '<div class="consent-actions"><button type="button" class="consent-button consent-save">Сохранить выбор</button><button type="button" class="consent-button consent-deny">Отклонить всё</button><button type="button" class="consent-button consent-close">Закрыть</button></div>';
  document.body.append(dialog);
  const analyticsInput = dialog.querySelector('#analytics-choice');
  const chatInput = dialog.querySelector('#chat-choice');
  const consentError = dialog.querySelector('.consent-error');
  const closeDialog = () => { dialog.close(); pendingChat = false; opener?.focus(); };
  const openDialog = (startChat, target) => {
    pendingChat = startChat; opener = target;
    consentError.hidden = true;
    if (analyticsInput) analyticsInput.checked = analyticsAllowed;
    if (chatInput) chatInput.checked = false;
    dialog.querySelector('.consent-save').textContent = startChat ? 'Открыть чат' : 'Сохранить выбор';
    dialog.showModal();
  };
  dialog.querySelector('.consent-close').addEventListener('click', closeDialog);
  dialog.addEventListener('cancel', () => { pendingChat = false; });
  dialog.addEventListener('close', () => { pendingChat = false; opener?.focus(); });
  dialog.addEventListener('click', e => { if (e.target === dialog) closeDialog(); });

  const banner = document.createElement('section');
  banner.className = 'privacy-banner'; banner.setAttribute('aria-label', 'Статистика посещений');
  banner.innerHTML = '<h2>Статистика посещений</h2><p>Разрешить Google Analytics учитывать просмотры и выбор способа связи?</p><div class="consent-actions"><button type="button" class="consent-button consent-accept">Разрешить</button><button type="button" class="consent-button consent-reject">Без статистики</button><button type="button" class="consent-button consent-settings">Настройки</button></div>';
  if (hasAnalytics && !choice) document.body.append(banner);
  const updateAnalytics = allowed => {
    const reload = (analyticsLoaded && !allowed) || chatRequested;
    analyticsAllowed = hasAnalytics && allowed; store(analyticsAllowed); banner.remove();
    if (reload) {
      if (hasAnalytics) window['ga-disable-' + config.ga4Id] = true;
      clearProviderCookies();
      // A new document releases provider scripts, connections and third-party frames.
      location.reload(); return true;
    }
    if (analyticsAllowed) loadAnalytics();
    return false;
  };
  banner.querySelector('.consent-accept').addEventListener('click', () => updateAnalytics(true));
  banner.querySelector('.consent-reject').addEventListener('click', () => updateAnalytics(false));
  banner.querySelector('.consent-settings').addEventListener('click', e => openDialog(false, e.currentTarget));
  dialog.querySelector('.consent-deny').addEventListener('click', () => {
    const reload = updateAnalytics(false); if (!reload) closeDialog();
  });
  const loadChat = () => {
    if (!networkAllowed) { announce('Чат доступен на публичном сайте. Можно использовать мессенджеры.'); return; }
    if (chatLoaded) { window.jivo_api?.open({start: 'chat'}); return; }
    if (chatLoading) return;
    chatLoading = true; chatRequested = true; announce('Открываю чат…');
    // Query and fragment are not needed for chat. Never forward their free text.
    if (location.search || location.hash) history.replaceState(null, '', location.pathname);
    const fail = () => { clearTimeout(loadTimeout); chatLoading = false; announce('Чат не загрузился. Напишите Владимиру через Telegram, WhatsApp или MAX.'); };
    window.jivo_onLoadCallback = () => {
      clearTimeout(loadTimeout); chatLoaded = true; chatLoading = false;
      window.jivo_api.setWidgetColor('#806342', '#806342');
      window.jivo_api.open({start: 'chat'}); announce('');
    };
    const tag = document.createElement('script'); tag.async = true;
    tag.src = 'https://code.jivosite.com/widget/' + config.jivoId;
    tag.referrerPolicy = 'no-referrer'; tag.onerror = fail;
    loadTimeout = setTimeout(fail, 20000); document.head.append(tag);
    event('chat_open_request', {contact_method: 'site_chat'});
  };
  dialog.querySelector('.consent-save').addEventListener('click', () => {
    if (pendingChat && !chatInput?.checked) {
      consentError.textContent = 'Для чата нужно отметить отдельное согласие. Можно выбрать мессенджер без подключения Jivo.';
      consentError.hidden = false; chatInput?.focus(); return;
    }
    const shouldChat = pendingChat && chatInput?.checked;
    const reload = updateAnalytics(analyticsInput?.checked || false);
    if (!reload) { closeDialog(); if (shouldChat) loadChat(); }
  });
  const settings = document.createElement('button'); settings.type = 'button';
  settings.className = 'footer-privacy-settings'; settings.textContent = 'Настройки приватности';
  settings.addEventListener('click', e => openDialog(false, e.currentTarget));
  document.querySelector('.footer-legal')?.append(settings);
  if (hasChat) {
    const makeChatButton = () => {
      const button = document.createElement('button'); button.type = 'button';
      button.className = 'site-chat-trigger'; button.textContent = 'Чат на сайте';
      button.addEventListener('click', e => chatLoaded ? window.jivo_api.open({start: 'chat'}) : openDialog(true, e.currentTarget));
      return button;
    };
    document.querySelector('.footer-contact')?.append(makeChatButton());
    document.querySelector('main .contact-email')?.after(makeChatButton());
  }
  document.addEventListener('click', e => {
    const link = e.target.closest('a[href]'); if (!link) return;
    const href = link.getAttribute('href');
    const channel = href.startsWith('https://t.me/') ? 'telegram' : href.startsWith('https://wa.me/') ? 'whatsapp' :
      href.startsWith('https://max.ru/u/') ? 'max' : href.startsWith('mailto:') ? 'email' : '';
    const placement = link.closest('footer') ? 'footer' : link.closest('header') ? 'header' :
      link.closest('.hero') ? 'hero' : link.closest('.primary-channels') ? 'contacts' : 'body';
    if (channel) event('contact_click', {contact_method: channel, placement});
    else if (/^(\.\.\/)?contact\.html$/.test(href) || href === '/contact.html') event('contact_intent', {placement});
  });
  loadAnalytics();
})();
