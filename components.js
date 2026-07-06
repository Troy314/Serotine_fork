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
    if (href.startsWith('http')) return false;
    const target = (BASE_PATH + href).split('#')[0].replace(/\/$/, '') || '/';
    return currentPath === target;
  }

  /* ── Navigation ──────────────────────────────────────────────────────── */
  const links = [
    { href: '/#explorer', label: 'Articles' },
    { href: '/#archives', label: 'Archives' },
    { href: '/#podcast', label: 'Podcast' },
    { href: '/comite/', label: 'À Propos' },
    { href: 'https://www.auroralpes.fr/', label: 'AurorAlpes', external: true },
  ];

  const navHTML = `
<nav>
  <a href="${BASE_PATH}/" class="nav-brand">
    <img src="${BASE_PATH}/media/serotine_logo.svg" alt="Logo Sérotine" class="logo-xsmall">
    érotine
  </a>
  <button class="nav-toggle" id="menuToggle" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
  <ul class="nav-links" id="navLinks">
    ${links.map(l => {
    const active = isActive(l.href) ? ' class="active"' : '';
    const ext = l.external ? ' target="_blank"' : '';
    const href = l.external ? l.href : BASE_PATH + l.href;
    return `<li><b><a href="${href}"${active}${ext}>${l.label}</a></b></li>`;
  }).join('\n    ')}
  </ul>
</nav>`;

  /* ── Footer ──────────────────────────────────────────────────────────── */
  const footerHTML = `
<footer>
  <p><strong>Sérotine, un souffle de science</strong> — par <a href="https://www.auroralpes.fr/" target="_blank">AurorAlpes</a></p>
  <div class="footer-logo">
    <a href="https://www.auroralpes.fr/" target="_blank">
      <img src="${BASE_PATH}/media/auroralpes_logo_fil.png" alt="Logo AurorAlpes" class="logo-footer">
    </a>
  </div>
  <div class="footer-links">
    <a href="${BASE_PATH}/mentions-legales/">Mentions légales</a>
    <a href="${BASE_PATH}/PRIVACY-POLICY.md">Politique de confidentialité</a>
  </div>
  <p class="footer-copyright">© AurorAlpes 2026</p>
  <p class="footer-credit">Site développé avec <a href="https://claude.ai" target="_blank" rel="noopener">Claude.ai</a></p>
</footer>`;

  /* ── Injection ───────────────────────────────────────────────────────── */
  const navPlaceholder = document.getElementById('nav-placeholder');
  if (navPlaceholder) navPlaceholder.outerHTML = navHTML;

  const footerPlaceholder = document.getElementById('footer-placeholder');
  if (footerPlaceholder) footerPlaceholder.outerHTML = footerHTML;

  /* ── Mobile nav ──────────────────────────────────────────────────────── */
  function initMobileNav() {
    const toggle = document.getElementById('menuToggle');
    const navLinks = document.getElementById('navLinks');
    if (!toggle || !navLinks) return;
    toggle.addEventListener('click', () => navLinks.classList.toggle('open'));
    navLinks.querySelectorAll('a').forEach(a =>
      a.addEventListener('click', () => navLinks.classList.remove('open'))
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMobileNav);
  } else {
    initMobileNav();
  }

})();
