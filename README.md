# Radar Empty Legs — capteur Telegram (MVP)

Capte automatiquement les empty legs postés dans tes groupes **Telegram**, les
transforme en données structurées (route, date, appareil, sièges, prix, devise)
et les range en base avec déduplication + expiration. Conçu pour tourner **tout seul**.

## Ce qu'il fait
- Se connecte à Telegram avec **ton compte** (API officielle, via Telethon — pas de scraping, pas de risque de ban).
- Écoute tes 4 groupes empty legs en continu.
- Parse chaque message (heuristique gratuite, ou Claude pour la qualité max).
- Stocke proprement (dédup, expiration 72 h par défaut) dans un simple fichier SQLite.

## Installation (≈ 10 min)
1. **Crée tes identifiants Telegram** : va sur https://my.telegram.org → *API development tools* → note `api_id` et `api_hash`.
2. **Configure** : `cp config.example.py config.py` puis remplis `API_ID`, `API_HASH`, et la liste `GROUPS` (les @username ou ids de tes 4 groupes).
3. **Installe** : `pip install -r requirements.txt`
4. **Lance** : `python listener.py`
   - 1er lancement : saisis ton numéro + le code reçu sur Telegram (**une seule fois**).
   - Ensuite : ça tourne en continu, les empty legs s'affichent et se rangent en base.

## Tester sans Telegram (tout de suite)
- `python test_parser.py` → teste l'extraction sur 10 messages réalistes.
- `python test_integration.py` → teste parse + stockage + déduplication.
Remplace les exemples par **tes vrais messages** pour calibrer.

## Piloter le radar sans coder
Un seul outil, `manage.py`, gère tout depuis le terminal :
```bash
python manage.py legs          # empty legs actifs en base
python manage.py demande       # carnet de demande ouverte (pour le desk Dynami)
python manage.py abonnes       # abonnés + leurs préférences
python manage.py demo          # jeu de données de démonstration

python manage.py ajouter-abonne --nom "Client St-Tropez" --contact client@example.com --canal email
python manage.py ajouter-pref  --abonne 1 --depart NCE,CEQ --arrivee LBG,GVA --prix-max 8000 --sieges-min 2
python manage.py ajouter-demande --depart NCE --arrivee LBG --prix-max 6000 --note "vendredi"
```
`python manage.py -h` liste toutes les commandes.

## Vérifier que tout marche
```bash
python run_tests.py            # lance les 7 suites et affiche un bilan PASS/FAIL
```

## Fichiers
| Fichier | Rôle |
|---|---|
| `parser.py` | Le cœur : message brut → ligne structurée |
| `airports.py` | Référentiel aéroports + aéroports voisins (matching de proximité) |
| `db.py` | Stockage SQLite + dédup + expiration ; abonnés, préférences, matches, demande |
| `listener.py` | L'écouteur Telegram (Telethon) — robuste : un message fautif n'arrête pas l'agent |
| `matcher.py` | Associe un empty leg aux abonnés dont une préférence colle |
| `notifier.py` | Envoi des alertes (console / email / Telegram) |
| `report_demand.py` | Affiche le carnet de demande ouverte |
| `manage.py` | Outil en ligne de commande pour tout piloter sans coder |
| `config.example.py` | Modèle de configuration |

## Qualité d'extraction : heuristique vs Claude
Par défaut, le parser est **heuristique** (gratuit, hors-ligne, instantané). Sur des
messages très tordus, passe `USE_CLAUDE = True` dans `config.py` (nécessite `anthropic`
et une clé `ANTHROPIC_API_KEY`) : Claude extrait alors les champs avec une bien
meilleure tolérance au désordre.

## Activer le matching + les alertes
Par défaut l'agent se contente d'écouter et de ranger (mode historique). Pour qu'il
**alerte automatiquement** les abonnés dès qu'un empty leg correspond à leurs critères :
1. dans `config.py`, mets `MATCHING_ENABLED = True` ;
2. crée des abonnés et leurs préférences avec `manage.py` (voir plus haut) ;
3. secrets de notification en **variables d'environnement** (jamais dans le code) :
   - email : `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` ;
   - Telegram : `TELEGRAM_BOT_TOKEN` (le `contact` de l'abonné = son `chat_id`).

Sans rien configurer, le canal `console` affiche les alertes dans le terminal — pratique pour tester.

## Prochaines briques (non incluses)
- **SMS** / **web-push** (brique PWA).
- Capter l'intention client en **langage naturel** pour remplir le carnet automatiquement.
- **Conversion de devises** dans le filtre de prix.
- Petit **dashboard** web des legs actifs + suivi des commissions.

## Note honnête
Le référentiel `airports.py` est volontairement limité (focus Riviera/Europe). Plus tu
l'enrichis, plus le taux de reconnaissance des routes monte. Les messages sans route
exploitable ou trop ambigus sont écartés *exprès* (mieux vaut rater un leg que polluer la base).
