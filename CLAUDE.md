# Empty Legs Radar — brief de reprise

## But du projet
Capter automatiquement les **empty legs** (jets privés) postés dans des groupes
**Telegram**, les structurer, les stocker, puis (prochaines briques) matcher la
demande client et alerter — pour alimenter le desk de courtage **Dynami** (courtier
aérien). Modèle : commission de courtage (3-7%) sur les vols transformés.
Wedge géographique : **Côte d'Azur** (Nice/Cannes/St-Tropez/Monaco ↔ Paris/Genève/Londres).

## Ce qui est déjà construit (MVP, testé)
- `parser.py` — cœur : message brut → {origin, destination, route, date, aircraft, seats, price, currency, confidence}.
  Heuristique offline (gratuit) + `parse_with_claude()` optionnel (meilleure qualité).
- `airports.py` — référentiel aéroports (IATA/ICAO/ville/alias), focus Riviera/Europe. À ENRICHIR.
- `db.py` — SQLite : `store_leg()` avec déduplication (hash) + expiration (TTL 72h), `active_legs()`.
- `listener.py` — écouteur Telegram via **Telethon** (compte utilisateur, API officielle, pas de scraping).
- Tests : `test_parser.py` (10 cas réalistes, tous verts), `test_integration.py` (parse→store→dedup).

## Lancer
1. `my.telegram.org` → api_id + api_hash
2. `cp config.example.py config.py` puis remplir API_ID, API_HASH, GROUPS (4 groupes)
3. `pip install -r requirements.txt`
4. `python listener.py` (login Telegram une fois, puis tourne 24/7)

## Conventions / décisions
- Un message sans route exploitable (origin+destination) est **écarté volontairement** (on préfère rater un leg que polluer la base).
- `confidence` 0..1 : route compte le plus, puis date.
- Extraction prix : on garde les espaces, on ne fusionne que les vrais séparateurs de milliers (groupes de 3) — sinon le n° d'appareil se colle au prix.

## Pièges déjà rencontrés (ne pas refaire)
- **Espaces insécables/fines (U+202F, U+00A0)** dans les prix → toujours nettoyer via regex `\s`, jamais `.replace(" ")`.
- **Ambiguïté ville/aéroport** : "Paris Le Bourget" ne doit pas produire un phantom Orly → géré dans `find_airports_in_order` (ville générique écartée si un aéroport précis de la même ville est cité ; sinon défaut via CITY_DEFAULT).
- Empty legs très **périssables** : prévoir TTL + revalidation. Données **commoditisées** (tout le monde les voit) → le moat = audience + vitesse + desk Dynami, pas la donnée.

## Prochaines briques (à coder)
1. **Matching** demande client ↔ legs (géo floue autour d'un aéroport, fenêtres de dates, plafond prix).
2. **Alertes** : email / SMS / **web-push** (réutiliser la brique PWA d'Arnaud).
3. **Carnet de demande** : capter l'intention client ("Nice→Paris vendredi <6k€") et la pousser au desk Dynami pour sourcer proactivement.
4. **Dashboard** des legs actifs + attribution des bookings (pour tracer la commission).

## Stack cible (réutiliser l'existant d'Arnaud)
Cloudflare Workers + PWA + web-push, déploiement Vercel, Python pour l'ingestion.
