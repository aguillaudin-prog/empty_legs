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

## Fichiers
| Fichier | Rôle |
|---|---|
| `parser.py` | Le cœur : message brut → ligne structurée |
| `airports.py` | Référentiel aéroports (enrichis-le pour couvrir plus de routes) |
| `db.py` | Stockage SQLite + dédup + expiration |
| `listener.py` | L'écouteur Telegram (Telethon) |
| `config.example.py` | Modèle de configuration |

## Qualité d'extraction : heuristique vs Claude
Par défaut, le parser est **heuristique** (gratuit, hors-ligne, instantané). Sur des
messages très tordus, passe `USE_CLAUDE = True` dans `config.py` (nécessite `anthropic`
et une clé `ANTHROPIC_API_KEY`) : Claude extrait alors les champs avec une bien
meilleure tolérance au désordre.

## Prochaines briques (non incluses dans ce MVP)
- Moteur de **matching** demande client ↔ empty legs + **alertes** (email/SMS/web-push).
- **Carnet de demande** : capter l'intention client et la pousser au desk courtier Dynami.
- Petit **dashboard** des legs actifs.

## Note honnête
Le référentiel `airports.py` est volontairement limité (focus Riviera/Europe). Plus tu
l'enrichis, plus le taux de reconnaissance des routes monte. Les messages sans route
exploitable ou trop ambigus sont écartés *exprès* (mieux vaut rater un leg que polluer la base).
