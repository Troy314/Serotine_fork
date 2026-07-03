# Sérotine — Un souffle de science

Site statique du webzine scientifique associatif **Sérotine**, porté par [AurorAlpes](https://www.auroralpes.fr/).  
Déployé sur GitHub Pages à l'adresse **[serotine.fr](https://serotine.fr)**.

---

## Structure du projet

```
serotine_rebrand/
├── index.html              # Page d'accueil
├── comite.html             # Comité de rédaction (généré par update_comite.py)
├── mentions-legales.html   # Mentions légales
├── 404.html                # Page d'erreur (générée par generate_site.py)
├── serotine.css            # Feuille de style partagée (source unique)
├── components.js           # Navigation et footer injectés sur toutes les pages
├── generate_site.py        # Générateur de pages articles depuis articles.csv
├── update_comite.py        # Générateur de la page comité depuis membres.csv
├── articles.csv            # Données des articles (source de vérité)
├── membres.csv             # Données des membres du comité (source de vérité)
├── articles/               # Pages HTML des articles (générées — ne pas modifier à la main)
└── media/                  # Images, SVGs, favicon
```

**Palette** : Bleu acier `#435c6e` · Bleu clair `#6a8fa5` · Bleu nuit `#2d4255` · Ambre `#edaf55`  
**Typographie** : Verdana — gras pour les titres, normal pour le corps

---

## Ajouter un article à un numéro existant

1. Ajouter une ligne dans `articles.csv` :

   ```
   id,title,author,theme,type,issue,issueLabel,href,season,image
   mon_article,Titre de l'article,Prénom Nom,astrophysique,article,5,#5 · Mai 2026,https://heyzine.com/...,2,../media/articles/serotine5_4.webp
   ```

   - `id` : identifiant unique, lettres/chiffres/tirets uniquement
   - `theme` : `astrophysique` · `biologie` · `physique` · `psychologie` · `sociologie`
   - `type` : `article` · `jeu` · `poesie`
   - `image` : chemin depuis `articles/`, donc `../media/articles/serotineN_M.webp` (1920×1080 px recommandé)
   - `issueLabel` : format `#N · Mois AAAA`

2. Régénérer le site :

   ```bash
   python generate_site.py articles.csv
   ```

---

## Publier un nouveau numéro

1. Ajouter les articles du numéro dans `articles.csv` (voir ci-dessus).

2. Ajouter les métadonnées du nouveau numéro dans `ISSUE_META` dans `generate_site.py` :

   ```python
   ISSUE_META = {
       6: ("media/Serotine6.jpg", "https://heyzine.com/flip-book/XXXXXXXX.html", "Octobre 2026"),
       5: ("media/Serotine5.jpg", "https://heyzine.com/flip-book/c5bd9067c1.html", "Mai 2026"),
       # …
   }
   ```

3. Déposer la couverture du numéro dans `media/` (`Serotine6.jpg`).

4. Régénérer :

   ```bash
   python generate_site.py articles.csv
   ```

   Le script met à jour automatiquement :
   - le bloc `const ARTICLES` dans `index.html`
   - la section **Archives** dans `index.html` (grille des numéros)
   - le **hero CTA** (`<!-- HERO_CTA -->`) pour pointer vers le dernier numéro
   - les pages HTML dans `articles/` (nav + footer via `components.js`)
   - le `sitemap.xml` et la page `404.html`

---

## Mettre à jour la page Comité

La page `comite.html` est générée depuis `membres.csv` :

```bash
python update_comite.py membres.csv
```

**Colonnes de `membres.csv`** : `Nom, Rôle, Biographie, URL, Type, Image, Speciality`  
**Valeurs de `Type`** : `comite` · `membre_projet` · `ancien_membre`

> ⚠ Ne pas modifier manuellement les sections entre `<!-- PROJET_START -->` / `<!-- PROJET_END -->` et `<!-- ANCIENS_START -->` / `<!-- ANCIENS_END -->` dans `comite.html` — elles seront écrasées par le script.

---

## Navigation et footer partagés

`components.js` injecte la navigation et le footer sur **toutes les pages** (index, comité, articles générés) via des placeholders HTML :

```html
<nav id="nav-placeholder"></nav>
…
<footer id="footer-placeholder"></footer>
<script src="components.js"></script>   <!-- ou ../components.js depuis articles/ -->
```

Pour modifier les liens de navigation ou le contenu du footer, éditer uniquement `components.js`.

---

## Structure de la page d'accueil (`index.html`)

| Section | ID | Description |
|---|---|---|
| Hero | — | Titre + réseaux sociaux + newsletter (gauche) · image `display.webp` + titres du dernier numéro + CTA (droite) |
| Découvrir les articles | `#explorer` | Grille filtrée par numéro (onglets), thème et type ; premier article mis en avant |
| Nous soutenir | `#about` | Texte + widget HelloAsso |
| Tous les numéros | `#archives` | Grille de couvertures avec lien Heyzine |
| Podcast | `#podcast` | Liens Apple Podcast, Spotify, Deezer, RSS |

---

## Développement local

Aucune dépendance de build — HTML/CSS/JS pur. Lancer un serveur local :

```bash
python -m http.server 8000
# puis ouvrir http://localhost:8000
```

---

## Déploiement

Le site est déployé automatiquement via **GitHub Pages** sur la branche `master`.  
Le fichier `CNAME` pointe le domaine personnalisé vers `serotine.fr`.

Pour déployer : pousser les modifications sur `master`.

---

## Favicon

- `media/favicon.svg` — utilisé sur toutes les pages (seul fichier favicon du dépôt)
