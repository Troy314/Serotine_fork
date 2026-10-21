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
import unicodedata
from collections import defaultdict
from datetime import date
from html import escape
from urllib.parse import quote

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
    7: ("media/serotine7.webp", "https://serotine-webzine.aflip.in/ddd744c837.html",  "Septembre 2026"),
    6: ("media/serotine6.webp", "https://serotine-webzine.aflip.in/907e4e9b03.html",  "Juillet 2026"),
    5: ("media/serotine5.webp", "https://heyzine.com/flip-book/c5bd9067c1.html",  "Mai 2026"),
    4: ("media/serotine4.webp", "https://heyzine.com/flip-book/5edd108961.html", "Mars 2026"),
    3: ("media/serotine3.webp", "https://heyzine.com/flip-book/d5c17bee9a.html",  "Février 2026"),
    2: ("media/serotine2.webp", "https://heyzine.com/flip-book/5f6791f646.html",  "Décembre 2025"),
    1: ("media/serotine1.webp", "https://heyzine.com/flip-book/78d38fd9ec.html",  "Novembre 2025"),
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
#  2. HOME PAGE BLOCKS (hero, cartes, archives)
# ══════════════════════════════════════════════

MONTHS_SHORT = {
    "Janvier": "Janv.", "Février": "Févr.", "Mars": "Mars", "Avril": "Avr.",
    "Mai": "Mai", "Juin": "Juin", "Juillet": "Juil.", "Août": "Août",
    "Septembre": "Sept.", "Octobre": "Oct.", "Novembre": "Nov.", "Décembre": "Déc.",
}

def short_date(label: str) -> str:
    """'Septembre 2026' → 'Sept. 2026'."""
    parts = label.split()
    if len(parts) == 2:
        return f"{MONTHS_SHORT.get(parts[0], parts[0])} {parts[1]}"
    return label

def issue_info(issue_num: int) -> tuple[str, str, str]:
    return ISSUE_META.get(issue_num, (f"media/serotine{issue_num}.webp", "#", ""))

def generate_hero_html(articles: list[dict]) -> str:
    latest = max(a["issue"] for a in articles)
    cover, base_url, date_lbl = issue_info(latest)
    titles = "".join(
        '<li style="padding-left:14px;position:relative"><span style="position:absolute;left:0;top:.5em;'
        'width:7px;height:7px;background:#b1ed4e;border-radius:1px" aria-hidden="true"></span>'
        f'{escape(a["title"])}</li>'
        for a in articles if a["issue"] == latest
    )
    return f"""\
<div class="g-panel" style="display:grid;align-items:center;align-content:center;flex:1;width:100%;max-width:760px;margin:0 0 0 auto;gap:28px;background:#ffffff1a;border:1px solid #ffffff40;border-radius:4px;padding:28px">
            <a class="f-ring" href="{base_url}" target="_blank" rel="noopener" style="display:block"><img src="{cover}" alt="Couverture du numéro {latest} de Sérotine, {date_lbl.lower()}" style="display:block;width:100%;height:auto;border-radius:4px;box-shadow:0 10px 24px #0007"></a>
            <div><p style="margin:0 0 12px;font-size:14px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:#b1ed4e">À la une · N° {latest}</p><ul style="margin:0;padding:0;list-style:none;display:grid;gap:10px;font-size:18px;line-height:1.4">{titles}</ul><a class="f-ring-w" href="{base_url}" target="_blank" rel="noopener" style="display:inline-block;margin-top:20px;color:#b1ed4e;font-weight:700;font-size:17px">Lire le numéro →</a></div>
          </div>"""

def generate_cards_html(articles: list[dict]) -> str:
    cards = []
    for a in sorted(articles, key=lambda x: -x["issue"]):  # tri stable : ordre du CSV dans un même numéro
        raw_img = a.get("image", "")
        img = raw_img[3:] if raw_img.startswith("../") else raw_img
        topic_tag = (
            f'<span style="background:#db9ced;color:#65466e;padding:4px 8px;border-radius:2px;text-shadow:none">'
            f'{escape(TOPIC_LABELS.get(a["topic"], a["topic"]))}</span>'
        ) if a["topic"] else ""
        cards.append(f"""\
        <a class="art-card" data-topic="{escape(a["topic"])}" data-author="{escape(a["author"])}" href="{escape(a["href"])}" target="_blank" rel="noopener" style="position:relative;display:block;aspect-ratio:16/10;overflow:hidden;border-radius:4px;background:#65466e;color:#fff;text-decoration:none;border:1px solid #65466e33;transition:transform .25s,box-shadow .25s">
          <img src="{escape(img)}" alt="" loading="lazy" style="position:absolute;inset:0;display:block;width:100%;height:100%;object-fit:cover">
          <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:space-between;padding:14px 16px;text-shadow:0 1px 3px #000c,0 2px 12px #000a">
            <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase">
              <span style="background:#b1ed4e;color:#374620;padding:4px 8px;border-radius:2px;text-shadow:none">{escape(TYPE_LABELS.get(a["type"], a["type"]))}</span>
              {topic_tag}
              <span style="margin-left:auto;color:#fff;white-space:nowrap">N° {a["issue"]}</span>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-start;gap:6px;text-shadow:none">
              <p style="margin:0;font-size:13px;font-weight:700;background:#fcf8f8;color:#65466e;padding:4px 10px;border-radius:2px">{escape(a["author"])}</p>
              <h3 style="margin:0;font-family:Verdana,Geneva,Tahoma,sans-serif;font-weight:700;font-size:16px;line-height:1.3;background:#65466e;color:#fff;padding:6px 10px;border-radius:2px;border:1px solid #ffffff40">{escape(a["title"])}</h3>
            </div>
          </div>
        </a>""")
    return "\n".join(cards)

def generate_archives_html(articles: list[dict]) -> str:
    issues = sorted({a["issue"] for a in articles}, reverse=True)
    items = []
    for n in issues:
        cover, base_url, date_lbl = issue_info(n)
        season = (n - 1) // 4 + 1
        items.append(f"""\
          <a class="issue-link" href="{base_url}" target="_blank" rel="noopener" style="text-decoration:none;color:#65466e;display:block;flex:1 0 110px;min-width:110px;scroll-snap-align:start">
            <img src="{cover}" alt="Couverture du numéro {n}" loading="lazy" style="display:block;width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:4px;border:1px solid #65466e">
            <p style="margin:8px 0 0;font-weight:700;font-size:13px">N° {n} · {short_date(date_lbl)}</p>
            <p style="margin:0;font-size:12px;color:#65466e">Saison {season}</p>
          </a>""")
    return "\n".join(items)


# ══════════════════════════════════════════════
#  4. ARTICLE PAGE GENERATOR
# ══════════════════════════════════════════════

def generate_article_html(article: dict) -> str:
    parts      = article["issueLabel"].split("·")
    issue_num  = parts[0].strip()
    page_url   = f"{SITE_URL}/articles/{article['id']}/"
    description = f"Article de {article['author']} dans Sérotine {article['issueLabel']}."
    title      = escape(article["title"])
    raw_img    = article.get("image", "")
    img        = "../" + raw_img if raw_img.startswith("../") else "../../" + raw_img.lstrip("/")
    topic_html = (
        f'<span style="background:#f1e3f6;padding:4px 8px;border-radius:2px">'
        f'{escape(TOPIC_LABELS.get(article["topic"], article["topic"]))}</span>'
    ) if article["topic"] else ""
    type_label = escape(TYPE_LABELS.get(article["type"], article["type"]))

    return f"""\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Sérotine</title>
  <meta name="description" content="{escape(description)}">

  <link rel="icon" href="../../media/favicon.svg">
  <link rel="canonical" href="{page_url}">

  <meta property="og:type"        content="article">
  <meta property="og:title"       content="{title} — Sérotine">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url"         content="{page_url}">
  <meta property="og:image"       content="{OG_IMAGE}">
  <meta property="og:site_name"   content="Sérotine, un souffle de science">
  <meta property="article:author" content="{escape(article["author"])}">

  <meta name="twitter:card"        content="summary_large_image">
  <meta name="twitter:title"       content="{title} — Sérotine">
  <meta name="twitter:description" content="{escape(description)}">
  <meta name="twitter:image"       content="{OG_IMAGE}">

  <link rel="stylesheet" href="../../css/serotine.css">
</head>
<body>
  <nav id="nav-placeholder"></nav>

  <main id="contenu" style="max-width:800px;margin:0 auto;padding:32px 20px 72px">
    <a href="../../#explorer" style="display:inline-block;margin-bottom:28px;font-size:13px;letter-spacing:.06em;text-transform:uppercase">← Retour au webzine</a>
    <header style="padding-bottom:24px;margin-bottom:32px;border-bottom:3px solid #65466e">
      <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-bottom:16px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase">
        <span>Sérotine {escape(article["issueLabel"])}</span>
        {topic_html}
        <span style="background:#b1ed4e;color:#374620;padding:4px 8px;border-radius:2px">{type_label}</span>
      </div>
      <h1 style="margin:0 0 12px;font-size:clamp(24px,4.5vw,38px);line-height:1.25;letter-spacing:-.01em">{title}</h1>
      <p style="margin:0;font-size:15px">Par {escape(article["author"])}</p>
    </header>
    <img src="{img}" alt="" style="display:block;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:4px;border:1px solid #65466e33;margin-bottom:28px">
    <a class="btn-primary" href="{escape(article["href"])}" target="_blank" rel="noopener" style="display:inline-flex;gap:10px;align-items:center;background:#65466e;color:#fff;padding:16px 24px;border-radius:4px;font-weight:700;font-size:15px;text-decoration:none;transition:transform .2s,box-shadow .2s">Lire l'article dans le webzine <span aria-hidden="true">→</span></a>
    <section aria-labelledby="coms" style="margin-top:56px;padding-top:28px;border-top:1px solid #65466e33">
      <h2 id="coms" style="margin:0 0 20px;font-size:12px;letter-spacing:.12em;text-transform:uppercase">Commentaires</h2>
      <script src="https://utteranc.es/client.js"
          repo="Serotine-webzine/Serotine"
          issue-term="pathname"
          theme="preferred-color-scheme"
          crossorigin="anonymous"
          async>
      </script>
    </section>
  </main>

  <footer id="footer-placeholder"></footer>
  <script src="../../components.js"></script>
  <script src="../../grain.js"></script>
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
  <link rel="icon" href="/media/favicon.svg">
  <link rel="stylesheet" href="/css/serotine.css">
  <style>body{background:#302135;color:#fff}a{color:#b1ed4e}</style>
</head>
<body>
  <main class="g" style="min-height:100vh;background:linear-gradient(135deg,#302135e6,#302135b8),url('/media/hero.svg') center/cover no-repeat,#302135;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:32px 20px;overflow-x:hidden">
    <img src="/media/serotine_logo.svg" alt="" width="56" height="56" style="display:block;margin-bottom:24px">
    <p style="margin:0;font-weight:700;font-size:clamp(88px,22vw,180px);line-height:1;color:#b1ed4e">404</p>
    <h1 style="margin:20px 0 12px;font-size:clamp(20px,4vw,30px);line-height:1.3">Cette page s'est perdue dans les étoiles…</h1>
    <p style="margin:0;max-width:440px;font-size:15px;line-height:1.8">L'article ou la page que vous cherchez n'existe pas ou a été déplacé.</p>
    <a class="btn-lime" id="home-link" href="/" style="margin-top:36px;display:inline-flex;gap:10px;background:#b1ed4e;color:#374620;padding:15px 24px;border-radius:4px;font-weight:700;font-size:15px;text-decoration:none;transition:transform .2s,box-shadow .2s"><span aria-hidden="true">←</span> Retour à l'accueil</a>
    <p style="margin:40px 0 0;font-weight:700;font-size:14px">Sérotine, <span style="color:#b1ed4e">un souffle de science</span></p>
  </main>
  <script>
    // Testing under GitHub Pages (/Serotine_fork/) needs the repo subpath;
    // production at serotine.fr serves from the root. Remove once GitHub
    // Pages testing ends.
    if (location.hostname.endsWith('.github.io')) {
      document.getElementById('home-link').href = '/Serotine_fork/';
    }
  </script>
  <script src="/grain.js"></script>
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

def replace_block(html: str, name: str, content: str) -> str:
    """Replace what sits between <!-- NAME_START --> and <!-- NAME_END -->."""
    pat = re.compile(rf'(<!-- {name}_START -->).*?(<!-- {name}_END -->)', re.DOTALL)
    if not pat.search(html):
        print(f"  ⚠  Repère {name}_START introuvable dans {INDEX_FILE}")
        return html
    print(f"  ✓ Bloc {name} injecté dans {INDEX_FILE}")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n        {m.group(2)}", html, count=1)


def inject_index(articles: list[dict]) -> None:
    if not os.path.exists(INDEX_FILE):
        print(f"  ⚠  {INDEX_FILE} introuvable — injection ignorée.")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    html = replace_block(html, "HERO", "          " + generate_hero_html(articles))
    html = replace_block(html, "CARDS", generate_cards_html(articles))
    html = replace_block(html, "ARCHIVES", generate_archives_html(articles))

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

def initials(nom: str) -> str:
    return "".join(w[0] for w in nom.split()[:2]).upper()


def author_key(name: str) -> str:
    """Nom normalisé (sans accents, ordre des mots ignoré) : « Gay Charley » = « Charley GAY »."""
    base = unicodedata.normalize("NFD", name)
    base = "".join(c for c in base if not unicodedata.combining(c))
    return " ".join(sorted(base.lower().split()))


AUTHOR_KEYS: set[str] = set()   # rempli dans main() à partir de articles.csv


def render_card(membre: dict, show_badge: bool = False) -> str:
    nom = escape(membre["nom"])
    has_articles = author_key(membre["nom"]) in AUTHOR_KEYS
    href = f'../?author={quote(membre["nom"])}#explorer'
    if membre["image"]:
        avatar = (f'<img src="{escape(membre["image"])}" alt="" loading="lazy" width="88" height="88" '
                  'style="display:block;width:88px;height:88px;object-fit:cover;border-radius:4px;border:3px solid #b1ed4e">')
    else:
        avatar = ('<div aria-hidden="true" style="width:88px;height:88px;border-radius:4px;border:3px solid #b1ed4e;'
                  'background:#65466e;color:#b1ed4e;font-weight:700;font-size:28px;display:flex;align-items:center;'
                  f'justify-content:center">{escape(initials(membre["nom"]))}</div>')
    if membre["url"]:
        avatar = (f'<a class="avatar-link" href="{escape(membre["url"])}" target="_blank" rel="noopener" aria-label="Profil de {nom}" '
                  f'style="display:block;border-radius:4px;transition:transform .25s">{avatar}</a>')
    badge = (
        '<span style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;'
        'background:#b1ed4e;color:#374620;padding:3px 8px;border-radius:2px">Comité de rédaction</span>'
    ) if show_badge else ""
    link = (
        f'<a class="f-ring" href="{href}" style="margin-top:auto;padding-top:6px;font-size:13px;font-weight:700">'
        'Voir ses articles →</a>'
    ) if has_articles else ""
    return f"""\
        <li class="member-card" style="background:#fff;border:1px solid #65466e33;border-radius:4px;padding:22px 18px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:8px;transition:transform .25s,border-color .25s,box-shadow .25s">
          {avatar}
          <h3 style="margin:6px 0 0;font-size:16px">{nom}</h3>
          {badge}
          <p style="margin:0;font-size:13px;line-height:1.5">{escape(membre["role"])}</p>
          {link}
        </li>"""


def render_alumnus(membre: dict) -> str:
    return f"""\
        <li style="display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid #65466e33;border-radius:4px">
          <div aria-hidden="true" style="flex:none;width:44px;height:44px;border-radius:4px;background:#65466e;color:#b1ed4e;font-weight:700;display:flex;align-items:center;justify-content:center">{escape(initials(membre["nom"]))}</div>
          <div style="font-size:14px;line-height:1.4"><strong>{escape(membre["nom"])}</strong><br>{escape(membre["role"])}</div>
        </li>"""


GRID_STYLE = ("list-style:none;margin:0;padding:0;display:grid;"
              "grid-template-columns:repeat(auto-fill,minmax(min(100%,220px),1fr));gap:16px")


# ══════════════════════════════════════════════
#  11. COMITÉ — SECTION BUILDERS
# ══════════════════════════════════════════════

def build_anciens_section(membres: list[dict]) -> str:
    if not membres:
        return "<!-- ANCIENS_START -->\n      <!-- ANCIENS_END -->"
    items = "\n".join(render_alumnus(m) for m in membres)
    return f"""\
<!-- ANCIENS_START -->
      <details style="margin-top:40px">
        <summary style="cursor:pointer;font-weight:700;font-size:18px;padding:12px 0;border-bottom:1px solid #65466e33">Anciens membres</summary>
        <ul style="list-style:none;margin:20px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,220px),1fr));gap:12px">
{items}
        </ul>
      </details>
      <!-- ANCIENS_END -->"""


def build_projet_section(membres_comite: list[dict], membres_projet: list[dict]) -> str:
    tous = membres_comite + membres_projet
    if not tous:
        return "<!-- PROJET_START -->\n      <!-- PROJET_END -->"
    cards = "\n".join(render_card(m, show_badge=(m["type"] == "comite")) for m in tous)
    return f"""\
<!-- PROJET_START -->
      <div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 16px;margin-bottom:24px;padding-bottom:12px;border-bottom:1px solid #65466e33">
        <h2 style="margin:0;font-size:clamp(22px,3vw,30px)">L'équipe</h2>
        <span style="font-size:12px;letter-spacing:.12em;text-transform:uppercase">Membres du projet</span>
      </div>
      <ul style="{GRID_STYLE}">
{cards}
      </ul>
      <!-- PROJET_END -->"""


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
    AUTHOR_KEYS.update(author_key(a["author"]) for a in articles)

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
