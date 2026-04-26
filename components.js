/**
 * components.js — Sérotine
 * Navigation et footer partagés entre toutes les pages.
 * Modifier ce fichier pour mettre à jour l'ensemble du site.
 */

(function () {

  /* ── Détection de la page active ─────────────────────────────────────── */
  const currentPage = location.pathname.split('/').pop() || 'index.html';

  function isActive(href) {
    const page = href.split('/').pop().split('#')[0];
    return currentPage === page;
  }

  /* ── Navigation ──────────────────────────────────────────────────────── */
  const links = [
    { href: 'index.html#dernier',  label: 'Dernier numéro' },
    { href: 'index.html#explorer', label: 'Explorer' },
    { href: 'index.html#archives', label: 'Archives' },
    { href: 'index.html#podcast',  label: 'Podcast' },
    { href: 'comite.html',         label: 'Organisation' },
    { href: 'https://www.auroralpes.fr/', label: 'AurorAlpes', external: true },
  ];

  const navHTML = `
<nav>
  <a href="index.html" class="nav-brand">
    <img src="media/serotine_logo.svg" alt="Logo Sérotine" class="logo-xsmall">
    érotine, <em>un souffle de science</em>
  </a>
  <button class="nav-toggle" id="menuToggle" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
  <ul class="nav-links" id="navLinks">
    ${links.map(l => {
      const active = isActive(l.href) ? ' class="active"' : '';
      const ext = l.external ? ' target="_blank"' : '';
      return `<li><a href="${l.href}"${active}${ext}>${l.label}</a></li>`;
    }).join('\n    ')}
  </ul>
</nav>`;

  /* ── Footer ──────────────────────────────────────────────────────────── */
  const footerHTML = `
<footer>
  <p><strong>Sérotine, un souffle de science</strong> — par <a href="https://www.auroralpes.fr/" target="_blank">AurorAlpes</a></p>
  <p>Espace commentaire développé à partir du projet <a href="https://github.com/utterance/utterances" target="_blank">utterances</a> par <a href="https://github.com/jdanyow" target="_blank">jdanyow</a></p>
  <div class="footer-logo">
    <a href="https://www.auroralpes.fr/" target="_blank">
      <img src="media/auroralpes_logo_fil.png" alt="Logo AurorAlpes" class="logo-footer">
    </a>
  </div>
  <div class="footer-links">
    <a href="mentions-legales.html">Mentions légales</a>
    <a href="PRIVACY-POLICY.md">Politique de confidentialité</a>
  </div>
  <p class="footer-copyright">© AurorAlpes 2026</p>
</footer>`;

  /* ── Injection ───────────────────────────────────────────────────────── */
  // Nav : remplace le placeholder <nav id="nav-placeholder"></nav>
  const navPlaceholder = document.getElementById('nav-placeholder');
  if (navPlaceholder) navPlaceholder.outerHTML = navHTML;

  // Footer : remplace le placeholder <footer id="footer-placeholder"></footer>
  const footerPlaceholder = document.getElementById('footer-placeholder');
  if (footerPlaceholder) footerPlaceholder.outerHTML = footerHTML;

  /* ── Mobile nav (gestion du menu burger) ────────────────────────────── */
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
