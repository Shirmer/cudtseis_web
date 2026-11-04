/* Homepage: navigation only; all content remains visible without JavaScript. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const header = document.querySelector('[data-header]');
  const button = document.querySelector('[data-menu]');
  const nav = document.getElementById('site-nav');
  function setMenu(open) {
    if (!header || !button) return;
    header.classList.toggle('open', open);
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? '关闭导航' : '打开导航');
  }
  button?.addEventListener('click', () => setMenu(button.getAttribute('aria-expanded') !== 'true'));
  nav?.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    setMenu(false);
    if (link.hash && link.pathname === location.pathname) {
      const section = document.getElementById(link.hash.slice(1));
      if (section) {
        section.setAttribute('tabindex', '-1');
        section.focus({ preventScroll: true });
      }
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && button?.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      button.focus();
    }
  });
  window.matchMedia('(max-width: 760px)').addEventListener('change', () => setMenu(false));
  function updateCurrent() {
    const hash = document.body.dataset.navSection
      ? `index.html#${document.body.dataset.navSection}`
      : location.hash || '#top';
    nav?.querySelectorAll('a').forEach(link => {
      if (link.getAttribute('href') === hash) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  }
  window.addEventListener('hashchange', updateCurrent);
  updateCurrent();
  document.querySelectorAll('[data-year]').forEach(el => { el.textContent = String(new Date().getFullYear()); });
  document.querySelectorAll('[data-copy-wechat]').forEach(copyButton => {
    copyButton.addEventListener('click', async () => {
      const feedback = copyButton.closest('.wechat-science')?.querySelector('[data-wechat-feedback]');
      try {
        await navigator.clipboard.writeText(copyButton.dataset.copyWechat);
        if (feedback) feedback.textContent = copyButton.dataset.copySuccess || '已复制，可在微信中搜索并关注。';
      } catch {
        if (feedback) feedback.textContent = copyButton.dataset.copyFallback
          ? `${copyButton.dataset.copyFallback} ${copyButton.dataset.copyWechat}`
          : '请选中或长按上方公众号名称，复制后在微信中搜索。';
      }
    });
  });
})();
