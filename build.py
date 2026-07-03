#!/usr/bin/env python3
"""
build.py — Sérotine site generator
====================================
Usage: python3 build.py [data/articles.csv [data/membres.csv]]

Defaults: data/articles.csv  data/membres.csv  (run from repo root)

Génère l'ensemble du site :
  1. Injecte le bloc JS `const ARTICLES = [...]` dans index.html
  2. Met à jour la section Archives dans index.html
  3. Génère les pages articles dans articles/{id}/index.html  (URLs propres, sans .html)
  4. Génère 404.html
  5. Génère sitemap.xml
  6. Met à jour comite/index.html depuis membres.csv

Issue metadata (ISSUE_META) and member CSV path are the only things to update
when adding a new issue or new members.
"""

import csv
import os
import re
import sys
from collections import defaultdict
from datetime import date
from html import escape

# ══════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════

ARTICLES_DIR = "articles"
INDEX_FILE   = "index.html"
SITEMAP_FILE = "sitemap.xml"
PAGE_404     = "404.html"
COMITE_FILE  = "comite/index.html"
SITE_URL     = "https://serotine.fr"
OG_IMAGE     = f"{SITE_URL}/media/serotine_logo.png"

# Issue metadata: issue number → (cover image, heyzine base URL, date label)
ISSUE_META = {
    5: ("media/Serotine5.jpg", "https://heyzine.com/flip-book/c5bd9067c1.html",  "Mai 2026"),
    4: ("media/Serotine4.jpg", "https://heyzine.com/flip-book/5edd108961.html", "Mars 2026"),
    3: ("media/Serotine3.jpg", "https://heyzine.com/flip-book/d5c17bee9a.html",  "Février 2026"),
    2: ("media/Serotine2.jpg", "https://heyzine.com/flip-book/5f6791f646.html",  "Décembre 2025"),
    1: ("media/Serotine1.jpg", "https://heyzine.com/flip-book/78d38fd9ec.html",  "Novembre 2025"),
}

TOPIC_LABELS = {
    "astrophysique": "Astrophysique",
    "biologie":      "Biologie",
    "physique":      "Physique",
    "psychologie":   "Psychologie",
    "sociologie":    "Sociologie",
}

TYPE_LABELS = {
    "article":    "Article",
    "jeu":        "Jeu",
    "poesie":     "Poésie",
    "merveilles": "7 Merveilles",
}

TAG_LABELS = {**TOPIC_LABELS, **TYPE_LABELS}

TOPIC_CSS = {
    "astrophysique": ("1e3a5f", "1e3a5f"),
    "biologie":      ("2d5a3d", "2d5a3d"),
    "physique":      ("8b3a2a", "8b3a2a"),
    "psychologie":   ("6b4c8b", "6b4c8b"),
    "sociologie":    ("4b6b3a", "3a5a28"),
}

TYPE_CSS = {
    "article":    ("3a475a", "3a475a"),
    "jeu":        ("b8860b", "8a6008"),
    "poesie":     ("3a5a5a", "3a5a5a"),
    "merveilles": ("3a5a5a", "3a5a5a"),
}

TAG_CSS = {**TOPIC_CSS, **TYPE_CSS}

FIELDS = ["id", "title", "author", "topic", "type", "issue", "issueLabel", "href", "season", "image"]


# ══════════════════════════════════════════════
#  1. CSV LOADER + VALIDATOR (articles)
# ══════════════════════════════════════════════

def load_articles(csv_path: str) -> list[dict]:
    """Parse articles.csv with validation. Prints warnings for bad rows."""
    articles = []
    warnings = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, skipinitialspace=True)
        next(reader)  # skip header

        for line_num, row in enumerate(reader, start=2):
            while row and not row[-1].strip():
                row.pop()

            if len(row) < 8:
                warnings.append(
                    f"  ⚠  Ligne {line_num}: seulement {len(row)} colonnes "
                    f"(attendu au moins 8) — ligne ignorée.\n     Contenu: {row}"
                )
                continue

            while len(row) < 10:
                row.append('')

            art = dict(zip(FIELDS, [c.strip().strip('"') for c in row]))

            if not art["id"] or not re.match(r'^[\w-]+$', art["id"]):
                warnings.append(
                    f"  ⚠  Ligne {line_num}: id invalide '{art['id']}' — ligne ignorée."
                )
                continue

            try:
                art["issue"] = int(art["issue"])
            except ValueError:
                warnings.append(
                    f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                    f"numéro invalide '{art['issue']}' — ligne ignorée."
                )
                continue

            if art["season"]:
                try:
                    art["season"] = int(art["season"])
                except ValueError:
                    art["season"] = (art["issue"] - 1) // 4 + 1
            else:
                art["season"] = (art["issue"] - 1) // 4 + 1

            for field in ("title", "author", "href", "topic", "type"):
                if not art[field]:
                    warnings.append(
                        f"  ⚠  Ligne {line_num} (id='{art['id']}'): champ '{field}' vide."
                    )

            if art["href"] and not art["href"].startswith("http"):
                warnings.append(
                    f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                    f"href ne ressemble pas à une URL: '{art['href']}'"
                )

            if art["topic"] and art["topic"] not in TOPIC_LABELS:
                warnings.append(
                    f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                    f"topic inconnu '{art['topic']}' — valeurs attendues: {list(TOPIC_LABELS)}"
                )
            if art["type"] and art["type"] not in TYPE_LABELS:
                warnings.append(
                    f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                    f"type inconnu '{art['type']}' — valeurs attendues: {list(TYPE_LABELS)}"
                )

            # Clean URL: articles/{id}/ (no .html)
            art["flip"] = f"articles/{art['id']}/"
            articles.append(art)

    if warnings:
        print(f"\n{'─'*60}")
        print(f"⚠  {len(warnings)} avertissement(s) CSV :")
        for w in warnings:
            print(w)
        print(f"{'─'*60}\n")
    else:
        print("  ✓ CSV valide, aucune anomalie détectée.")

    return articles


# ══════════════════════════════════════════════
#  2. JS DATA BLOCK
# ══════════════════════════════════════════════

def js_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def generate_js_data(articles: list[dict]) -> str:
    lines = ["const ARTICLES = ["]
    for a in articles:
        raw_img = a.get("image", "")
        img = raw_img[3:] if raw_img.startswith("../") else raw_img
        lines.append(
            f'  {{ id:"{js_escape(a["id"])}", '
            f'title:"{js_escape(a["title"])}", '
            f'author:"{js_escape(a["author"])}", '
            f'topic:"{js_escape(a["topic"])}", '
            f'type:"{js_escape(a["type"])}", '
            f'issue:{a["issue"]}, '
            f'season:{a["season"]}, '
            f'issueLabel:"{js_escape(a["issueLabel"])}", '
            f'href:"{js_escape(a["href"])}", '
            f'flip:"{js_escape(a["flip"])}", '
            f'image:"{js_escape(img)}" }},'
        )
    lines.append("];")
    return "\n".join(lines)


# ══════════════════════════════════════════════
#  3. ARCHIVES HTML BLOCK
# ══════════════════════════════════════════════

def generate_archives_html(articles: list[dict]) -> str:
    by_issue = defaultdict(list)
    for a in articles:
        by_issue[a["issue"]].append(a)

    cards = []
    for issue_num in sorted(by_issue.keys(), reverse=True):
        issue_articles = by_issue[issue_num]
        meta     = ISSUE_META.get(issue_num, (f"media/Serotine{issue_num}.jpg", "#", ""))
        cover    = meta[0]
        base_url = meta[1]
        date_lbl = meta[2]
        season   = (issue_num - 1) // 4 + 1
        count    = len(issue_articles)
        plural   = "s" if count > 1 else ""

        cards.append(f"""\
        <div class="issue-card">
          <div class="issue-cover"><a href="{base_url}" target="_blank"><img src="{cover}" alt="#{issue_num}"></a></div>
          <div class="issue-info">
            <div class="issue-season">Saison {season} · #{issue_num}</div>
            <div class="issue-date">{date_lbl}</div>
            <div class="issue-count">{count} article{plural}</div>
            <a href="{base_url}" target="_blank" class="issue-read-btn">Lire →</a>
          </div>
        </div>""")

    all_cards = "\n".join(cards)
    return f"""\
  <!-- ARCHIVES -->
  <section class="section" id="archives">
    <h2 class="section-title">Tous les numéros <small>Archives</small></h2>
    <div class="issues-grid">
{all_cards}
    </div>
  </section>"""


# ══════════════════════════════════════════════
#  4. ARTICLE PAGE GENERATOR
# ══════════════════════════════════════════════

def tag_css_rule(tag: str) -> str:
    bg, fg = TAG_CSS.get(tag, ("888", "555"))
    return f'.tag-{tag} {{ background:#{bg}14; color:#{fg}; border:1px solid #{bg}28; }}'

def render_tag_html(key: str, value: str) -> str:
    label = TAG_LABELS.get(value, value)
    return f'<span class="tag tag-{value}" data-filter="{key}" data-value="{value}">{label}</span>'

def generate_article_html(article: dict) -> str:
    tags_html  = render_tag_html("topic", article["topic"]) + "\n        " + render_tag_html("type", article["type"])
    parts      = article["issueLabel"].split("·")
    issue_num  = parts[0].strip()
    issue_date = parts[1].strip() if len(parts) > 1 else ""
    page_url   = f"{SITE_URL}/articles/{article['id']}/"
    description = f"Article de {article['author']} dans Sérotine {article['issueLabel']}."

    return f"""\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{article["title"]} — Sérotine</title>
  <meta name="description" content="{description}">

  <link rel="canonical" href="{page_url}">

  <meta property="og:type"        content="article">
  <meta property="og:title"       content="{article["title"]} — Sérotine">
  <meta property="og:description" content="{description}">
  <meta property="og:url"         content="{page_url}">
  <meta property="og:image"       content="{OG_IMAGE}">
  <meta property="og:site_name"   content="Sérotine, un souffle de science">
  <meta property="article:author" content="{article["author"]}">

  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="{article["title"]} — Sérotine">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image"       content="{OG_IMAGE}">

  <link rel="stylesheet" href="../../css/serotine.css">
</head>
<body>
  <nav>
    <a href="../.." class="nav-brand">Sérotine <em>— un souffle de science</em></a>
    <button class="nav-toggle" id="menuToggle" aria-label="Menu"><span></span><span></span><span></span></button>
    <ul class="nav-links" id="navLinks">
      <li><a href="../../#dernier">Dernier numéro</a></li>
      <li><a href="../../#explorer">Explorer</a></li>
      <li><a href="../../#archives">Archives</a></li>
      <li><a href="../../#podcast">Podcast</a></li>
      <li><a href="../../comite/">Comité</a></li>
      <li><a href="https://www.auroralpes.fr/" target="_blank">AurorAlpes</a></li>
    </ul>
  </nav>

  <div class="wrap">
    <a href="../.." class="back-link">← Retour au webzine</a>
    <header class="article-header">
      <div class="article-meta">
        <span class="article-issue">Sérotine {issue_num} · {issue_date}</span>
        {tags_html}
        <span class="article-author">{article["author"]}</span>
      </div>
      <h1 class="article-title">{article["title"]}</h1>
      <a href="{article["href"]}" target="_blank" class="read-original">
        Lire l'article dans le webzine
      </a>
    </header>
    <div class="comments-section">
      <div class="comments-label">Commentaires</div>
      <script src="https://utteranc.es/client.js"
          repo="Serotine-webzine/Serotine"
          issue-term="pathname"
          theme="preferred-color-scheme"
          crossorigin="anonymous"
          async>
      </script>
    </div>
  </div>

  <footer>
    <p>Sérotine, un souffle de science — par <a href="https://www.auroralpes.fr/" target="_blank">AurorAlpes</a></p>
  </footer>

  <script>
    const t = document.getElementById('menuToggle'), n = document.getElementById('navLinks');
    t.addEventListener('click', () => n.classList.toggle('open'));
    n.querySelectorAll('a').forEach(a => a.addEventListener('click', () => n.classList.remove('open')));
  </script>
</body>
</html>"""


# ══════════════════════════════════════════════
#  5. 404 PAGE
# ══════════════════════════════════════════════

def generate_404() -> str:
    return """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page introuvable — Sérotine</title>
  <link rel="stylesheet" href="css/serotine.css">
</head>
<body class="error-page">
  <div class="code">404</div>
  <h1>Cette page s'est perdue dans les étoiles…</h1>
  <p>L'article ou la page que vous cherchez n'existe pas ou a été déplacé.</p>
  <a href="/" class="home-link" id="home-link">← Retour à l'accueil</a>
  <p class="brand">Sérotine, <em>un souffle de science</em></p>
  <script>
    // Testing under GitHub Pages (/Serotine_fork/) needs the repo subpath;
    // production at serotine.fr serves from the root. Remove once GitHub
    // Pages testing ends.
    if (location.hostname.endsWith('.github.io')) {
      document.getElementById('home-link').href = '/Serotine_fork/';
    }
  </script>
</body>
</html>"""


# ══════════════════════════════════════════════
#  6. SITEMAP
# ══════════════════════════════════════════════

def generate_sitemap(articles: list[dict]) -> str:
    today = date.today().isoformat()
    urls = [
        f"""\
  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>""",
        f"""\
  <url>
    <loc>{SITE_URL}/comite/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.8</priority>
  </url>""",
    ]
    for a in articles:
        urls.append(f"""\
  <url>
    <loc>{SITE_URL}/{a["flip"]}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.7</priority>
  </url>""")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )


# ══════════════════════════════════════════════
#  7. CLEANUP LEGACY FLAT ARTICLE FILES
# ══════════════════════════════════════════════

def cleanup_flat_articles(articles: list[dict]) -> None:
    """Remove old articles/{id}.html files replaced by articles/{id}/index.html."""
    removed = 0
    for article in articles:
        old_path = os.path.join(ARTICLES_DIR, f"{article['id']}.html")
        if os.path.exists(old_path):
            os.remove(old_path)
            print(f"  🗑  Supprimé : {old_path}")
            removed += 1
    if removed:
        print(f"  → {removed} ancien(s) fichier(s) plat(s) supprimé(s).")


# ══════════════════════════════════════════════
#  8. INDEX.HTML INJECTOR
# ══════════════════════════════════════════════

def inject_index(articles: list[dict]) -> None:
    if not os.path.exists(INDEX_FILE):
        print(f"  ⚠  {INDEX_FILE} introuvable — injection ignorée.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    js_new   = generate_js_data(articles)
    js_match = re.search(r'const ARTICLES = \[.*?^\s*];', html, re.DOTALL | re.MULTILINE)
    if js_match:
        html = html[:js_match.start()] + js_new + html[js_match.end():]
        print("  ✓ Bloc ARTICLES injecté dans index.html")
    else:
        print("  ⚠  Bloc 'const ARTICLES = [' introuvable dans index.html")

    archives_new   = generate_archives_html(articles)
    archives_match = re.search(r'<!-- ARCHIVES -->.*?</section>', html, re.DOTALL)
    if archives_match:
        html = html[:archives_match.start()] + archives_new + html[archives_match.end():]
        print("  ✓ Section Archives injectée dans index.html")
    else:
        print("  ⚠  Section '<!-- ARCHIVES -->' introuvable dans index.html")

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)


# ══════════════════════════════════════════════
#  9. CSV LOADER + VALIDATOR (membres)
# ══════════════════════════════════════════════

VALID_TYPES    = ("comite", "ancien_membre", "membre_projet")
MEMBRE_FIELDS  = ("Nom", "Rôle", "Biographie", "URL", "Type", "Image", "Speciality")
DEFAULT_IMAGE  = ""

def load_membres(csv_path: str) -> dict[str, list[dict]]:
    grouped: dict[str, list] = {t: [] for t in VALID_TYPES}
    warnings = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)

        if reader.fieldnames is None:
            print("  ✗ Le fichier CSV membres est vide.")
            sys.exit(1)

        missing = [c for c in MEMBRE_FIELDS if c not in reader.fieldnames]
        if missing:
            print(f"  ✗ Colonnes manquantes dans membres.csv : {missing}")
            sys.exit(1)

        for line_num, row in enumerate(reader, start=2):
            nom   = row.get("Nom", "").strip()
            type_ = row.get("Type", "").strip().lower()

            if not nom:
                warnings.append(f"  ⚠  Ligne {line_num} : colonne 'Nom' vide — ligne ignorée.")
                continue

            if type_ not in VALID_TYPES:
                warnings.append(
                    f"  ⚠  Ligne {line_num} ({nom}) : type inconnu '{type_}' "
                    f"— valeurs attendues : {VALID_TYPES} — ligne ignorée."
                )
                continue

            grouped[type_].append({
                "nom":        nom,
                "role":       row.get("Rôle", "").strip(),
                "bio":        row.get("Biographie", "").strip(),
                "url":        row.get("URL", "").strip(),
                "type":       type_,
                "image":      row.get("Image", "").strip(),
                "speciality": (row.get("Speciality") or "").strip(),
            })

    if warnings:
        print(f"\n{'─'*60}")
        print(f"⚠  {len(warnings)} avertissement(s) CSV membres :")
        for w in warnings:
            print(w)
        print(f"{'─'*60}\n")

    total = sum(len(v) for v in grouped.values())
    print(f"  ✓ {total} membres chargés  "
          f"({len(grouped['comite'])} comité, "
          f"{len(grouped['ancien_membre'])} anciens, "
          f"{len(grouped['membre_projet'])} projet)")
    return grouped


# ══════════════════════════════════════════════
#  10. COMITÉ — HTML CARD GENERATOR
# ══════════════════════════════════════════════

def render_avatar(membre: dict) -> str:
    img_src = membre["image"] if membre["image"] else "../media/icon_rond.png"
    img_tag = (
        f'<img src="{escape(img_src)}" alt="{escape(membre["nom"])}" '
        f'class="member-photo" loading="lazy">'
    )
    if membre["url"]:
        return (
            f'<div class="member-avatar">'
            f'<a href="{escape(membre["url"])}" target="_blank" rel="noopener" '
            f'aria-label="Profil de {escape(membre["nom"])}">{img_tag}</a>'
            f'</div>'
        )
    return f'<div class="member-avatar">{img_tag}</div>'


def render_card(membre: dict, compact: bool = False, show_badge: bool = False) -> str:
    avatar_html = render_avatar(membre)

    badge_html = (
        '<span class="badge-comite">Comité de rédaction</span>'
        if show_badge else ""
    )

    def _speciality_tags(raw: str) -> str:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        spans = "".join(f'<span class="badge-speciality">{escape(p)}</span>' for p in parts)
        return f'<div class="speciality-tags">{spans}</div>'

    speciality_html = _speciality_tags(membre["speciality"]) if membre.get("speciality") else ""

    bio_html = (
        f'<div class="member-bio">{escape(membre["bio"])}</div>'
        if membre["bio"] and not compact else ""
    )

    compact_cls = " compact" if compact else ""
    return f"""\
      <div class="member-card{compact_cls}">
        {avatar_html}
        <div class="member-name">{escape(membre["nom"])}</div>
        {badge_html}
        <div class="member-role">{escape(membre["role"])}</div>
        {bio_html}
        {speciality_html}
      </div>"""


def render_members_grid(membres: list[dict], compact: bool = False,
                        badge_types: tuple = ()) -> str:
    cards = "\n".join(
        render_card(m, compact, show_badge=(m["type"] in badge_types))
        for m in membres
    )
    return f'    <div class="members-grid">\n{cards}\n    </div>'


# ══════════════════════════════════════════════
#  11. COMITÉ — SECTION BUILDERS
# ══════════════════════════════════════════════

def build_anciens_section(membres: list[dict]) -> str:
    if not membres:
        return "    <!-- ANCIENS_START -->\n    <!-- ANCIENS_END -->"
    grid = render_members_grid(membres, compact=True)
    return f"""\
    <!-- ANCIENS_START -->
    <details class="anciens-details">
      <summary class="section-title anciens-summary">
        Anciens membres
      </summary>
{grid}
    </details>
    <!-- ANCIENS_END -->"""


def build_projet_section(membres_comite: list[dict], membres_projet: list[dict]) -> str:
    tous = membres_comite + membres_projet
    if not tous:
        return "    <!-- PROJET_START -->\n    <!-- PROJET_END -->"
    grid = render_members_grid(tous, badge_types=("comite",))
    return f"""\
    <!-- PROJET_START -->
    <h2 class="section-title">L'équipe <small>Membres du projet</small></h2>
{grid}
    <!-- PROJET_END -->"""


# ══════════════════════════════════════════════
#  12. COMITÉ — CSS INJECTION
# ══════════════════════════════════════════════

EXTRA_CSS = """\
    /* AVATAR */
    .member-avatar { width: 52px; height: 52px; border-radius: 50%; overflow: hidden; margin-bottom: .75rem; flex-shrink: 0; }
    .member-photo { width: 100%; height: 100%; object-fit: cover; }
    .member-initials {
      display: flex; align-items: center; justify-content: center;
      background: var(--ink); color: var(--paper);
      font-family: 'Playfair Display', serif; font-size: 1.1rem; font-weight: 400;
    }

    /* PASTILLE COMITÉ DE RÉDACTION */
    .badge-comite {
      display: inline-block;
      font-size: .65rem; font-weight: 200; letter-spacing: .04em; text-transform: uppercase;
      border: 1px solid var(--ink);
      border-radius: 3px; padding: .15em .5em;
      margin-bottom: .35rem;
      vertical-align: middle;
    }

    /* CARTE COMPACTE (anciens membres) */
    .member-card.compact { padding: 1rem 1.2rem; }
    .member-card.compact .member-avatar { width: 36px; height: 36px; font-size: .8rem; }

    /* ANCIENS MEMBRES — section dépliable */
    .anciens-details { margin-bottom: 3.5rem; }
    .anciens-details > .members-grid { margin-top: 1.5rem; }
    .anciens-summary {
      cursor: pointer; list-style: none; display: flex;
      align-items: baseline; gap: .75rem;
      margin-bottom: 0 !important;
    }
    .anciens-summary::-webkit-details-marker { display: none; }
    .anciens-summary .toggle-icon { font-size: .9rem; color: var(--muted); transition: transform .25s; }
    .anciens-details[open] .toggle-icon { transform: rotate(180deg); }

    /* CSS INJECTED BY generate.py — ne pas supprimer cette ligne */"""

CSS_MARKER = "/* CSS INJECTED BY generate.py — ne pas supprimer cette ligne */"
CSS_MARKER_LEGACY = "/* CSS INJECTED BY update_comite.py — ne pas supprimer cette ligne */"


# ══════════════════════════════════════════════
#  13. COMITÉ — INJECTOR
# ══════════════════════════════════════════════

def inject_comite(grouped: dict[str, list], comite_path: str) -> None:
    if not os.path.exists(comite_path):
        print(f"  ✗ {comite_path} introuvable — injection abandonnée.")
        return

    with open(comite_path, "r", encoding="utf-8") as f:
        html = f.read()

    changed = False

    # Migrate legacy CSS marker
    if CSS_MARKER_LEGACY in html:
        html = html.replace(CSS_MARKER_LEGACY, CSS_MARKER)
        changed = True

    # Inject / update CSS block
    if CSS_MARKER not in html:
        html = html.replace("    /* MEMBER GRID */", EXTRA_CSS + "\n\n    /* MEMBER GRID */", 1)
        if CSS_MARKER not in html:
            html = html.replace("  </style>", EXTRA_CSS + "\n  </style>", 1)
        print("  ✓ Styles CSS injectés")
        changed = True
    else:
        old_css = re.search(r'/\* AVATAR \*/.*?/\* CSS INJECTED BY (?:generate|update_comite)\.py[^\*]*\*/', html, re.DOTALL)
        if old_css:
            html = html[:old_css.start()] + EXTRA_CSS + html[old_css.end():]
            print("  ✓ Styles CSS mis à jour")
            changed = True

    # Remove legacy COMITE_START/END block if present
    match_comite = re.search(r'<!-- COMITE_START -->.*?<!-- COMITE_END -->', html, re.DOTALL)
    if match_comite:
        html = html[:match_comite.start()] + html[match_comite.end():]
        print("  ℹ  Ancienne section COMITE_START/END supprimée")
        changed = True

    # Inject anciens section
    new_anciens = build_anciens_section(grouped["ancien_membre"])
    match = re.search(r'<!-- ANCIENS_START -->.*?<!-- ANCIENS_END -->', html, re.DOTALL)
    if match:
        html = html[:match.start()] + new_anciens.strip() + html[match.end():]
        print(f"  ✓ Section anciens mise à jour ({len(grouped['ancien_membre'])} membres)")
        changed = True
    else:
        print("  ⚠  Repère ANCIENS_START introuvable — section anciens non injectée.")

    # Inject équipe unifiée (comité + projet)
    new_projet = build_projet_section(grouped["comite"], grouped["membre_projet"])
    match = re.search(r'<!-- PROJET_START -->.*?<!-- PROJET_END -->', html, re.DOTALL)
    if match:
        html = html[:match.start()] + new_projet.strip() + html[match.end():]
        nb = len(grouped["comite"]) + len(grouped["membre_projet"])
        print(f"  ✓ Section équipe mise à jour ({nb} membres : "
              f"{len(grouped['comite'])} comité + {len(grouped['membre_projet'])} projet)")
        changed = True
    else:
        print("  ⚠  Repère PROJET_START introuvable — section équipe non injectée.")

    if changed:
        with open(comite_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n  ✅  {comite_path} mis à jour.")
    else:
        print("\n  ℹ  Aucune modification apportée à comite/index.html.")


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    csv_articles = args[0] if len(args) > 0 else "data/articles.csv"
    csv_membres  = args[1] if len(args) > 1 else "data/membres.csv"

    # ── Articles ─────────────────────────────────────────────────────────────
    if not os.path.exists(csv_articles):
        print(f"Erreur : fichier introuvable : {csv_articles}")
        sys.exit(1)

    print(f"\n📂  Chargement de {csv_articles}…")
    articles = load_articles(csv_articles)
    print(f"✓  {len(articles)} articles chargés.\n")

    print("📄  Mise à jour de index.html…")
    inject_index(articles)

    print(f"\n📝  Génération des pages articles dans '{ARTICLES_DIR}/'…")
    for article in articles:
        folder = os.path.join(ARTICLES_DIR, article["id"])
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "index.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(generate_article_html(article))
        print(f"  ✓ {path}")

    print(f"\n🧹  Suppression des anciens fichiers plats dans '{ARTICLES_DIR}/'…")
    cleanup_flat_articles(articles)

    print(f"\n🚫  Génération de {PAGE_404}…")
    with open(PAGE_404, "w", encoding="utf-8") as f:
        f.write(generate_404())
    print(f"  ✓ {PAGE_404}")

    print(f"\n🗺   Génération de {SITEMAP_FILE}…")
    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(generate_sitemap(articles))
    print(f"  ✓ {SITEMAP_FILE}  ({len(articles) + 2} URLs)")

    # ── Comité ───────────────────────────────────────────────────────────────
    if os.path.exists(csv_membres):
        print(f"\n📂  Chargement de {csv_membres}…")
        grouped = load_membres(csv_membres)
        print(f"\n📄  Mise à jour de {COMITE_FILE}…")
        inject_comite(grouped, COMITE_FILE)
    else:
        print(f"\n⚠   {csv_membres} introuvable — mise à jour du comité ignorée.")

    print(f"\n✅  Terminé — {len(articles)} articles, 404, sitemap, index, comité mis à jour.\n")


if __name__ == "__main__":
    main()
