#!/usr/bin/env python3
"""
generate_site.py — Sérotine site generator
============================================
Usage: python generate_site.py articles.csv

Reads articles.csv and automatically:
  1. Injects the JS `const ARTICLES = [...]` block into index.html
  2. Generates all HTML files in the articles/ folder
  3. Generates the Archives section in index.html
  4. Adds OpenGraph / meta tags to every article page
  5. Generates a 404.html page
  6. Generates a sitemap.xml
  7. Validates the CSV and reports malformed rows

Run from the root of the Serotine_fork directory.
"""

import csv
import os
import re
import sys
from collections import defaultdict
from datetime import date

# ══════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════

ARTICLES_DIR = "articles"
INDEX_FILE   = "index.html"
SITEMAP_FILE = "sitemap.xml"
PAGE_404     = "404.html"
SITE_URL     = "https://serotine-webzine.github.io/Serotine"
OG_IMAGE     = f"{SITE_URL}/media/serotine_logo.png"

# Issue metadata: issue number → (cover image, heyzine base URL, date label)
ISSUE_META = {
    4: ("media/Serotine4.jpg", "https://heyzine.com/flip-book/5edd108961.html", "Mars 2026"),
    3: ("media/Serotine3.jpg", "https://heyzine.com/flip-book/d5c17bee9a.html",  "Février 2026"),
    2: ("media/Serotine2.jpg", "https://heyzine.com/flip-book/5f6791f646.html",  "Décembre 2025"),
    1: ("media/Serotine1.jpg", "https://heyzine.com/flip-book/78d38fd9ec.html",  "Novembre 2025"),
}

TOPIC_LABELS = {
    "astrophysique": "🌌 Astrophysique",
    "biologie":      "🦠 Biologie",
    "physique":      "🧲 Physique",
    "psychologie":   "🧠 Psychologie",
    "sociologie":    "🤝 Sociologie",
}

TYPE_LABELS = {
    "article": "✒️ Article",
    "jeu":     "🎲 Jeu",
    "poesie":  "🎶 Poésie",
}

TAG_LABELS = {**TOPIC_LABELS, **TYPE_LABELS}  # kept for article page rendering

TOPIC_CSS = {
    "astrophysique": ("1e3a5f", "1e3a5f"),
    "biologie":      ("2d5a3d", "2d5a3d"),
    "physique":      ("8b3a2a", "8b3a2a"),
    "psychologie":   ("6b4c8b", "6b4c8b"),
    "sociologie":    ("4b6b3a", "3a5a28"),
}

TYPE_CSS = {
    "article": ("3a475a", "3a475a"),
    "jeu":     ("b8860b", "8a6008"),
    "poesie":  ("3a5a5a", "3a5a5a"),
}

TAG_CSS = {**TOPIC_CSS, **TYPE_CSS}  # kept for CSS generation

FIELDS = ["id", "title", "author", "topic", "type", "issue", "issueLabel", "href"]


# ══════════════════════════════════════════════
#  1. CSV LOADER + VALIDATOR
# ══════════════════════════════════════════════

def load_articles(csv_path: str) -> list[dict]:
    """Parse articles.csv with validation. Prints warnings for bad rows."""
    articles = []
    warnings = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, skipinitialspace=True)
        next(reader)  # skip header

        for line_num, row in enumerate(reader, start=2):
            # Drop empty trailing fields (rows end with a trailing comma)
            while row and not row[-1].strip():
                row.pop()

            # ── Validate column count ─────────────────────────────────────
            if len(row) < 8:
                warnings.append(
                    f"  ⚠  Ligne {line_num}: seulement {len(row)} colonnes "
                    f"(attendu 8) — ligne ignorée.\n     Contenu: {row}"
                )
                continue

            art = dict(zip(FIELDS, [c.strip().strip('"') for c in row]))

            # ── Validate id ───────────────────────────────────────────────
            if not art["id"] or not re.match(r'^[\w-]+$', art["id"]):
                warnings.append(
                    f"  ⚠  Ligne {line_num}: id invalide '{art['id']}' — ligne ignorée."
                )
                continue

            # ── Validate issue number ─────────────────────────────────────
            try:
                art["issue"] = int(art["issue"])
            except ValueError:
                warnings.append(
                    f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                    f"numéro de numéro invalide '{art['issue']}' — ligne ignorée."
                )
                continue

            # ── Validate required fields ──────────────────────────────────
            for field in ("title", "author", "href", "topic", "type"):
                if not art[field]:
                    warnings.append(
                        f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                        f"champ '{field}' vide."
                    )

            # ── Validate href ─────────────────────────────────────────────
            if art["href"] and not art["href"].startswith("http"):
                warnings.append(
                    f"  ⚠  Ligne {line_num} (id='{art['id']}'): "
                    f"href ne ressemble pas à une URL: '{art['href']}'"
                )

            # ── Validate topic / type values ──────────────────────────────
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

            # Derive flip from id
            art["flip"] = f"articles/{art['id']}.html"

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
#  JS DATA BLOCK
# ══════════════════════════════════════════════

def js_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def generate_js_data(articles: list[dict]) -> str:
    lines = ["const ARTICLES = ["]
    for a in articles:
        lines.append(
            f'  {{ id:"{js_escape(a["id"])}", '
            f'title:"{js_escape(a["title"])}", '
            f'author:"{js_escape(a["author"])}", '
            f'topic:"{js_escape(a["topic"])}", '
            f'type:"{js_escape(a["type"])}", '
            f'issue:{a["issue"]}, '
            f'issueLabel:"{js_escape(a["issueLabel"])}", '
            f'href:"{js_escape(a["href"])}", '
            f'flip:"{js_escape(a["flip"])}" }},'
        )
    lines.append("];")
    return "\n".join(lines)


# ══════════════════════════════════════════════
#  2. ARCHIVES HTML BLOCK
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

        items = "\n".join(
            f'              <li>'
            f'<a href="{a["href"]}" target="_blank">{a["title"]}</a> '
            f'</li>'
            for a in issue_articles
        )

        cards.append(f"""\
        <div class="issue-card">
          <div class="issue-cover"><a href="{base_url}" target="_blank"><img src="{cover}" alt="#{issue_num}"></a></div>
          <div class="issue-info">
            <div class="issue-number">#{issue_num}</div><div class="issue-date">{date_lbl}</div>
            <ul class="issue-articles">
{items}
            </ul>
          </div>
        </div>""")

    cards_html = "\n".join(cards)
    return f"""\
  <!-- ARCHIVES -->
  <section class="section" id="archives">
    <h2 class="section-title">Anciens numéros <small>Tous les numéros</small></h2>
    <details open>
      <summary>Saison 1</summary>
      <div class="issues-grid">
{cards_html}
      </div>
    </details>
  </section>"""


# ══════════════════════════════════════════════
#  3. ARTICLE PAGE GENERATOR (with OpenGraph)
# ══════════════════════════════════════════════

def tag_css_rule(tag: str) -> str:
    bg, fg = TAG_CSS.get(tag, ("888", "555"))
    return f'.tag-{tag} {{ background:#{bg}14; color:#{fg}; border:1px solid #{bg}28; }}'

def render_tag_html(key: str, value: str) -> str:
    label = TAG_LABELS.get(value, value)
    return f'<span class="tag tag-{value}" data-filter="{key}" data-value="{value}">{label}</span>'

def generate_article_html(article: dict) -> str:
    tag_styles  = "\n    ".join(tag_css_rule(t) for t in TAG_CSS)
    tags_html   = render_tag_html("topic", article["topic"]) + "\n        " + render_tag_html("type", article["type"])
    parts       = article["issueLabel"].split("·")
    issue_num   = parts[0].strip()
    issue_date  = parts[1].strip() if len(parts) > 1 else ""
    page_url    = f"{SITE_URL}/articles/{article['id']}.html"
    description = f"Article de {article['author']} dans Sérotine {article['issueLabel']}."

    return f"""\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{article["title"]} — Sérotine</title>
  <meta name="description" content="{description}">

  <!-- OpenGraph -->
  <meta property="og:type"        content="article">
  <meta property="og:title"       content="{article["title"]} — Sérotine">
  <meta property="og:description" content="{description}">
  <meta property="og:url"         content="{page_url}">
  <meta property="og:image"       content="{OG_IMAGE}">
  <meta property="og:site_name"   content="Sérotine, un souffle de science">
  <meta property="article:author" content="{article["author"]}">

  <!-- Twitter Card -->
  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="{article["title"]} — Sérotine">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image"       content="{OG_IMAGE}">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --ink: #1a1410; --paper: #f8f4ee; --cream: #f0e9dc;
      --accent: #2d5a3d; --muted: #7a6f63; --border: rgba(26,20,16,.15);
    }}
    body {{ background: var(--paper); color: var(--ink); font-family: 'DM Sans', sans-serif; font-weight: 300; line-height: 1.7; }}
    nav {{
      position: sticky; top: 0; z-index: 100; background: var(--ink);
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 2rem; height: 56px; box-shadow: 0 2px 14px rgba(0,0,0,.4);
    }}
    .nav-brand {{ font-family: 'Playfair Display', serif; font-size: 1.05rem; color: var(--paper); text-decoration: none; }}
    .nav-brand em {{ font-style: italic; color: #c8b89a; }}
    .nav-links {{ display: flex; gap: 1.75rem; list-style: none; }}
    .nav-links a {{ color: #c8b89a; text-decoration: none; font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; transition: color .2s; }}
    .nav-links a:hover {{ color: #fff; }}
    .nav-toggle {{ display: none; background: none; border: none; cursor: pointer; padding: 6px; flex-direction: column; gap: 5px; }}
    .nav-toggle span {{ display: block; width: 22px; height: 2px; background: var(--paper); }}
    @media (max-width: 720px) {{
      .nav-toggle {{ display: flex; }}
      .nav-links {{ display: none; position: fixed; top: 56px; left: 0; right: 0; background: var(--ink); flex-direction: column; gap: 0; padding: 1rem 0; }}
      .nav-links.open {{ display: flex; }}
      .nav-links li a {{ display: block; padding: .75rem 2rem; }}
    }}
    .wrap {{ max-width: 760px; margin: 0 auto; padding: 3rem 2rem 5rem; }}
    .back-link {{ display: inline-flex; align-items: center; gap: .4rem; color: var(--muted); font-size: .78rem; text-decoration: none; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 2.25rem; transition: color .2s; }}
    .back-link:hover {{ color: var(--accent); }}
    .article-header {{ border-bottom: 2px solid var(--ink); padding-bottom: 1.25rem; margin-bottom: 2.5rem; }}
    .article-meta {{ display: flex; align-items: center; gap: .75rem; flex-wrap: wrap; margin-bottom: .75rem; }}
    .article-issue {{ font-size: .72rem; font-weight: 500; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }}
    .article-author {{ font-size: .78rem; color: var(--muted); }}
    .article-title {{ font-family: 'Playfair Display', serif; font-size: clamp(1.5rem,4vw,2.2rem); font-weight: 400; line-height: 1.25; margin-top: .6rem; }}
    .read-original {{ display: inline-flex; align-items: center; gap: .5rem; margin-top: 1.5rem; background: var(--ink); color: var(--paper); font-size: .82rem; font-weight: 500; letter-spacing: .04em; padding: .55rem 1.3rem; border-radius: 99px; text-decoration: none; transition: opacity .2s; }}
    .read-original:hover {{ opacity: .8; }}
    .comments-section {{ margin-top: 3rem; padding-top: 2rem; border-top: 1px solid var(--border); }}
    .comments-label {{ font-size: .7rem; font-weight: 500; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin-bottom: 1.5rem; }}
    footer {{ background: var(--ink); color: #a09080; text-align: center; padding: 2rem; font-size: .8rem; }}
    footer a {{ color: #c8b89a; }}
    .tag {{ display: inline-block; font-size: .68rem; font-weight: 500; letter-spacing: .07em; text-transform: uppercase; padding: .15rem .55rem; border-radius: 99px; }}
    {tag_styles}
  </style>
</head>
<body>
  <nav>
    <a href="../index.html" class="nav-brand">Sérotine <em>— un souffle de science</em></a>
    <button class="nav-toggle" id="menuToggle" aria-label="Menu"><span></span><span></span><span></span></button>
    <ul class="nav-links" id="navLinks">
      <li><a href="../index.html#dernier">Dernier numéro</a></li>
      <li><a href="../index.html#explorer">Explorer</a></li>
      <li><a href="../index.html#archives">Archives</a></li>
      <li><a href="../index.html#podcast">Podcast</a></li>
      <li><a href="https://www.auroralpes.fr/" target="_blank">AurorAlpes</a></li>
    </ul>
  </nav>

  <div class="wrap">
    <a href="../index.html" class="back-link">← Retour au webzine</a>
    <header class="article-header">
      <div class="article-meta">
        <span class="article-issue">Sérotine {issue_num} · {issue_date}</span>
        {tags_html}
        <span class="article-author">✍ {article["author"]}</span>
      </div>
      <h1 class="article-title">{article["title"]}</h1>
      <a href="{article["href"]}" target="_blank" class="read-original">
        📖 Lire l'article dans le webzine
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
#  4. 404 PAGE
# ══════════════════════════════════════════════

def generate_404() -> str:
    return """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page introuvable — Sérotine</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root { --ink: #1a1410; --paper: #f8f4ee; --accent: #2d5a3d; --muted: #7a6f63; }
    body {
      background: var(--ink); color: var(--paper);
      font-family: 'DM Sans', sans-serif; font-weight: 300;
      min-height: 100vh; display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      text-align: center; padding: 2rem;
    }
    .code {
      font-family: 'Playfair Display', serif;
      font-size: clamp(5rem, 20vw, 10rem);
      font-weight: 400; color: #c8b89a; line-height: 1; opacity: .35;
    }
    h1 {
      font-family: 'Playfair Display', serif;
      font-size: clamp(1.4rem, 4vw, 2rem);
      font-weight: 400; margin: 1.5rem 0 .75rem;
    }
    p { color: #a09080; max-width: 400px; font-size: .92rem; line-height: 1.8; }
    .home-link {
      display: inline-flex; align-items: center; gap: .5rem;
      margin-top: 2.5rem;
      background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.18);
      color: #e8d8c0; font-size: .85rem; font-weight: 500;
      letter-spacing: .06em; padding: .65rem 1.6rem;
      border-radius: 99px; text-decoration: none; transition: background .2s;
    }
    .home-link:hover { background: rgba(255,255,255,.15); }
    .brand { margin-top: 3rem; font-family: 'Playfair Display', serif; font-size: .9rem; color: #7a6f63; }
    .brand em { font-style: italic; color: #c8b89a; }
  </style>
</head>
<body>
  <div class="code">404</div>
  <h1>Cette page s'est perdue dans les étoiles…</h1>
  <p>L'article ou la page que vous cherchez n'existe pas ou a été déplacé.</p>
  <a href="index.html" class="home-link">← Retour à l'accueil</a>
  <p class="brand">Sérotine, <em>un souffle de science</em></p>
</body>
</html>"""


# ══════════════════════════════════════════════
#  5. SITEMAP
# ══════════════════════════════════════════════

def generate_sitemap(articles: list[dict]) -> str:
    today = date.today().isoformat()
    urls = [f"""\
  <url>
    <loc>{SITE_URL}/index.html</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>"""]
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
#  6. INDEX.HTML INJECTOR
# ══════════════════════════════════════════════

def inject_index(articles: list[dict]) -> None:
    """Patches index.html in-place: JS data block + archives section."""
    if not os.path.exists(INDEX_FILE):
        print(f"  ⚠  {INDEX_FILE} introuvable — injection ignorée.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # ── Inject JS ARTICLES block ──────────────────────────────────────────
    js_new   = generate_js_data(articles)
    js_match = re.search(r'const ARTICLES = \[.*?^];', html, re.DOTALL | re.MULTILINE)
    if js_match:
        html = html[:js_match.start()] + js_new + html[js_match.end():]
        print("  ✓ Bloc ARTICLES injecté dans index.html")
    else:
        print("  ⚠  Bloc 'const ARTICLES = [' introuvable dans index.html")

    # ── Inject Archives section ───────────────────────────────────────────
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
#  MAIN
# ══════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_site.py articles.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Erreur : fichier introuvable : {csv_path}")
        sys.exit(1)

    print(f"\n📂  Chargement de {csv_path}…")
    articles = load_articles(csv_path)
    print(f"✓  {len(articles)} articles chargés.\n")

    # 1+3 — Inject index.html (JS data block + Archives section)
    print("📄  Mise à jour de index.html…")
    inject_index(articles)

    # 2 — Generate article pages (with OpenGraph meta)
    print(f"\n📝  Génération des pages articles dans '{ARTICLES_DIR}/'…")
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    for article in articles:
        path = os.path.join(ARTICLES_DIR, f"{article['id']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(generate_article_html(article))
        print(f"  ✓ {path}")

    # 4 — Generate 404 page
    print(f"\n🚫  Génération de {PAGE_404}…")
    with open(PAGE_404, "w", encoding="utf-8") as f:
        f.write(generate_404())
    print(f"  ✓ {PAGE_404}")

    # 5 — Generate sitemap
    print(f"\n🗺   Génération de {SITEMAP_FILE}…")
    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(generate_sitemap(articles))
    print(f"  ✓ {SITEMAP_FILE}  ({len(articles) + 1} URLs)")

    print(f"\n✅  Terminé — {len(articles)} articles, 404, sitemap, index mis à jour.\n")


if __name__ == "__main__":
    main()
