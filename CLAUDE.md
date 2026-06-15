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
  Tables ajoutées : `subscribers`, `preferences`, `matches`, `demand` (+ CRUD : `add_subscriber`,
  `add_preference`, `subscribers_with_prefs`, `record_match`/`match_exists`/`mark_notified`,
  `leg_by_hash`, `add_demand`/`open_demand`, `seed_demo`).
- `listener.py` — écouteur Telegram via **Telethon** (compte utilisateur, API officielle, pas de scraping).
- Tests : `test_parser.py` (10 cas réalistes), `test_integration.py` (parse→store→dedup).

## Ce qui est construit (brique Matching + Alertes + Carnet de demande, testé)
- `matcher.py` — `match_leg(conn, leg)` → liste des `subscriber_id` dont une préférence colle
  (route+proximité, fenêtre de dates, plafond prix même devise, min sièges ; "prix sur demande"
  matche en étant signalé). Anti-doublon de matches.
- `airports.py` — ajout `NEARBY` + `expand_with_nearby()` : aéroports voisins (NCE~CEQ/MCM/LTT,
  Paris, Londres, Milan) pour le matching de proximité.
- `notifier.py` — `Notifier` pluggable : `ConsoleNotifier` (défaut), `EmailNotifier` (SMTP),
  `TelegramNotifier` (bot). `notify_match()` envoie puis marque `matches.notified=1`.
- `report_demand.py` — affiche le carnet de demande ouverte pour le desk Dynami.

## Lancer
1. `my.telegram.org` → api_id + api_hash
2. `cp config.example.py config.py` puis remplir API_ID, API_HASH, GROUPS (4 groupes)
3. `pip install -r requirements.txt`
4. `python listener.py` (login Telegram une fois, puis tourne 24/7)

### Activer matching + alertes
- Dans `config.py` : `MATCHING_ENABLED = True` (défaut `False` = écouteur seul, comportement historique).
- Créer abonnés/préférences en base (`db.add_subscriber` / `add_preference`, ou `seed_demo` pour démo).
- Secrets de notif en **variables d'environnement** (jamais en dur) :
  - email : `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
  - telegram : `TELEGRAM_BOT_TOKEN` (contact abonné = `chat_id`)
- Carnet de demande : `python report_demand.py [base.db]`.

## Lancer les tests
`python test_parser.py && python test_integration.py && python test_db_subscribers.py && \
 python test_matcher.py && python test_notifier.py && python test_listener_flow.py && \
 python test_demand.py`
(Tests = scripts autonomes, pas de pytest ; chacun crée/supprime sa propre base de test.)

## Conventions / décisions
- Un message sans route exploitable (origin+destination) est **écarté volontairement** (on préfère rater un leg que polluer la base).
- `confidence` 0..1 : route compte le plus, puis date.
- Extraction prix : on garde les espaces, on ne fusionne que les vrais séparateurs de milliers (groupes de 3) — sinon le n° d'appareil se colle au prix.

## Pièges déjà rencontrés (ne pas refaire)
- **Espaces insécables/fines (U+202F, U+00A0)** dans les prix → toujours nettoyer via regex `\s`, jamais `.replace(" ")`.
- **Ambiguïté ville/aéroport** : "Paris Le Bourget" ne doit pas produire un phantom Orly → géré dans `find_airports_in_order` (ville générique écartée si un aéroport précis de la même ville est cité ; sinon défaut via CITY_DEFAULT).
- Empty legs très **périssables** : prévoir TTL + revalidation. Données **commoditisées** (tout le monde les voit) → le moat = audience + vitesse + desk Dynami, pas la donnée.

## Prochaines briques (à coder)
1. ~~**Matching** demande client ↔ legs~~ → fait (`matcher.py`, proximité géo via `NEARBY`).
2. **Alertes** : ~~email / telegram~~ faits (`notifier.py`) ; reste **SMS** / **web-push** (brique PWA d'Arnaud).
3. ~~**Carnet de demande**~~ → fait (`demand` + `report_demand.py`). Reste : capter l'intention
   automatiquement (parser une demande client en langage naturel) et UI de saisie.
4. **Dashboard** des legs actifs + attribution des bookings (pour tracer la commission).
5. **Conversion de devises** dans le matching prix (aujourd'hui : on ne bloque pas si devises différentes).

## Stack cible (réutiliser l'existant d'Arnaud)
Cloudflare Workers + PWA + web-push, déploiement Vercel, Python pour l'ingestion.
