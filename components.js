/**
 * components.js — Sérotine
 * Navigation et footer partagés entre toutes les pages.
 * Modifier ce fichier pour mettre à jour l'ensemble du site.
 *
 * Uses absolute paths (/comite/, /mentions-legales/) so the file works
 * regardless of the page depth (root, comite/, articles/id/, …).
 *
 * Production lives at serotine.fr (site root), but during GitHub Pages
 * testing the repo is served under /Serotine_fork/ — BASE_PATH accounts
 * for that subpath and should be removed once GitHub Pages testing ends.
 */

(function () {

  /* ── Base path (repo subpath on GitHub Pages, empty on serotine.fr) ──── */
  const BASE_PATH = location.hostname.endsWith('.github.io') ? '/Serotine_fork' : '';

  /* ── Détection de la page active ─────────────────────────────────────── */
  const currentPath = location.pathname.replace(/\/$/, '') || '/';

  function isActive(href) {
    if (href.startsWith('http') || href.includes('#')) return false;
    const target = (BASE_PATH + href).replace(/\/$/, '') || '/';
    return currentPath === target;
  }

  /* ── Navigation ──────────────────────────────────────────────────────── */
  const NEWSLETTER_URL = 'https://framaforms.org/newsletter-serotine-1777624449';
  const links = [
    { href: '/#explorer', label: 'Articles' },
    { href: '/#podcast', label: 'Podcast' },
    { href: '/#archives', label: 'Archives' },
    { href: '/#soutenir', label: 'Nous soutenir' },
    { href: '/comite/', label: 'À propos' },
  ];

  const desktopLinks = links.map(l => {
    const active = isActive(l.href) ? ' active' : '';
    const current = active ? ' aria-current="page"' : '';
    return `<li><a class="nav-link${active}" href="${BASE_PATH}${l.href}"${current}>${l.label}</a></li>`;
  }).join('\n      ');

  const mobileLinks = links.map(l =>
    `<li><a href="${BASE_PATH}${l.href}">${l.label}</a></li>`
  ).join('\n      ');

  const navHTML = `
<a class="skip-link" href="#contenu">Aller au contenu</a>
<header class="site-header">
  <div class="site-progress" id="siteProgress"></div>
  <nav class="site-nav" aria-label="Navigation principale">
    <a class="brand" href="${BASE_PATH}/">
      <img src="${BASE_PATH}/media/serotine_logo.svg" alt=""><span>érotine</span><span class="sr-only">Sérotine, accueil</span>
    </a>
    <ul class="nav-list">
      ${desktopLinks}
      <li><a class="nav-cta" href="${NEWSLETTER_URL}" target="_blank" rel="noopener">Newsletter</a></li>
    </ul>
    <button class="nav-burger" id="menuToggle" type="button" aria-expanded="false" aria-controls="menu-mobile" aria-label="Menu">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
    </button>
  </nav>
  <ul class="menu-mobile" id="menu-mobile">
      ${mobileLinks}
      <li class="cta"><a href="${NEWSLETTER_URL}" target="_blank" rel="noopener">S'abonner à la newsletter</a></li>
  </ul>
</header>`;

  /* ── Footer ──────────────────────────────────────────────────────────── */
  const footerHTML = `
<footer class="site-footer">
  <div class="site-footer-in">
    <div class="site-footer-brand">
      <a href="https://www.auroralpes.fr/" target="_blank" rel="noopener"><img src="${BASE_PATH}/media/auroralpes_logo_fil.png" alt="AurorAlpes" height="40"></a>
      <p><strong>Sérotine, un souffle de science</strong><br>par AurorAlpes · © 2026</p>
    </div>
    <nav class="site-footer-links" aria-label="Liens légaux">
      <a href="${BASE_PATH}/mentions-legales/">Mentions légales</a>
      <a href="${BASE_PATH}/confidentialite/">Politique de confidentialité</a>
      <a href="${BASE_PATH}/comite/">À propos</a>
    </nav>
  </div>
</footer>`;

  /* ── Injection ───────────────────────────────────────────────────────── */
  const navPlaceholder = document.getElementById('nav-placeholder');
  if (navPlaceholder) navPlaceholder.outerHTML = navHTML;

  const footerPlaceholder = document.getElementById('footer-placeholder');
  if (footerPlaceholder) footerPlaceholder.outerHTML = footerHTML;

  /* ── Menu mobile + barre de progression ──────────────────────────────── */
  function initNav() {
    const toggle = document.getElementById('menuToggle');
    const menu = document.getElementById('menu-mobile');
    if (toggle && menu) {
      toggle.addEventListener('click', () => {
        const open = menu.classList.toggle('open');
        toggle.setAttribute('aria-expanded', open);
      });
      menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
        menu.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }));
    }

    const bar = document.getElementById('siteProgress');
    if (bar) {
      const update = () => {
        const h = document.documentElement, max = h.scrollHeight - h.clientHeight;
        bar.style.width = (max > 0 ? Math.min(100, h.scrollTop / max * 100) : 0) + '%';
      };
      window.addEventListener('scroll', update, { passive: true });
      window.addEventListener('resize', update);
      update();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNav);
  } else {
    initNav();
  }

})();
