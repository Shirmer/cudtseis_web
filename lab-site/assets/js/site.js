/* Shared navigation, homepage scroll position and explicit clipboard actions. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const header = document.querySelector('[data-header]');
  const button = document.querySelector('[data-menu]');
  const nav = document.getElementById('site-nav');
  const groups = Array.from(document.querySelectorAll('[data-nav-group]'));
  const isHome = document.body.dataset.page === 'home';
  const normalize = path => path.replace(/\/index\.html$/, '/') || '/';
  function setGroup(group, open) {
    const toggle = group.querySelector('[data-nav-toggle]');
    const submenu = group.querySelector('.nav-submenu');
    if (!toggle || !submenu) return;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? '收起资讯栏目' : '展开资讯栏目');
    submenu.hidden = !open;
  }
  function closeGroups() { groups.forEach(group => setGroup(group, false)); }
  function setMenu(open) {
    if (!header || !button) return;
    header.classList.toggle('open', open);
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? '关闭导航' : '打开导航');
    if (!open) closeGroups();
  }
  button?.addEventListener('click', () => setMenu(button.getAttribute('aria-expanded') !== 'true'));
  groups.forEach(group => group.querySelector('[data-nav-toggle]')?.addEventListener('click', () => {
    const open = group.querySelector('[data-nav-toggle]').getAttribute('aria-expanded') !== 'true';
    closeGroups();
    setGroup(group, open);
  }));
  nav?.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link) return;
    setMenu(false);
    if (link.hash && normalize(link.pathname) === normalize(location.pathname)) {
      const section = document.getElementById(link.hash.slice(1));
      if (section) { section.setAttribute('tabindex', '-1'); section.focus({ preventScroll: true }); }
    }
  });
  document.addEventListener('click', event => {
    if (header && !header.contains(event.target)) setMenu(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const openGroup = groups.find(group => group.querySelector('[data-nav-toggle]')?.getAttribute('aria-expanded') === 'true');
    if (openGroup) { setGroup(openGroup, false); openGroup.querySelector('[data-nav-toggle]').focus(); }
    else if (button?.getAttribute('aria-expanded') === 'true') { setMenu(false); button.focus(); }
  });
  window.matchMedia('(max-width: 760px)').addEventListener('change', () => setMenu(false));
  function setCurrent(section) {
    header?.querySelectorAll('a[data-section]').forEach(link => {
      if (link.dataset.section === section) link.setAttribute('aria-current', isHome ? 'location' : 'page');
      else link.removeAttribute('aria-current');
    });
    header?.querySelectorAll('a[data-category]').forEach(link => {
      if (!isHome && link.dataset.category === document.body.dataset.category) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  }
  if (isHome) {
    const sections = Array.from(document.querySelectorAll('main [data-nav-section]'));
    let queued = false;
    function updateFromScroll() {
      queued = false;
      const marker = (header?.getBoundingClientRect().height || 0) + 36;
      let current = 'top';
      for (const section of sections) {
        if (section.getBoundingClientRect().top <= marker) current = section.dataset.navSection;
      }
      if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        current = sections.at(-1)?.dataset.navSection || current;
      }
      setCurrent(current);
    }
    const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(updateFromScroll); } };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    window.addEventListener('hashchange', schedule);
    window.addEventListener('load', schedule);
    updateFromScroll();
  } else setCurrent(document.body.dataset.navSection || '');
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
