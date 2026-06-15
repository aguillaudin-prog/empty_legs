"""Moteur de matching : un empty leg -> les abonnes dont une preference colle.

Regles (cf. CLAUDE.md / cahier des charges) :
- origin doit etre dans home_airports (home vide = depart de n'importe ou) ;
  proximite geographique prise en compte (NCE accepte CEQ/MCM/LTT...).
- dest_airports vide = toute destination, sinon destination dans dest_airports
  (proximite incluse aussi).
- si leg.date et date_from/date_to : la date doit tomber dans la fenetre.
- si max_price et leg.price (meme devise) : price <= max_price.
  Si leg.price est absent ("prix sur demande"), on matche quand meme et on
  signale price_on_request=True.
- si min_seats : leg.seats >= min_seats. Si seats absent, on n'exclut pas.

match_leg() enregistre les matches (anti-doublon via db.match_exists) et renvoie
la liste des subscriber_id concernes.
"""

from airports import expand_with_nearby
from db import subscribers_with_prefs, match_exists, record_match


def _csv_to_set(csv):
    if not csv:
        return set()
    return {c.strip().upper() for c in csv.split(",") if c.strip()}


def _leg_get(leg, key):
    """Accès uniforme : un leg peut etre un dict (parser) ou une ligne SQL (dict aussi).
    flight_date / date sont synonymes selon la provenance."""
    if key == "date":
        return leg.get("date") or leg.get("flight_date")
    return leg.get(key)


def preference_matches(leg, pref):
    """Teste une preference contre un leg.

    Renvoie un dict {matched: bool, price_on_request: bool} pour expliciter le
    cas 'prix sur demande' qui matche mais merite d'etre signale."""
    result = {"matched": False, "price_on_request": False}

    origin = (_leg_get(leg, "origin") or "").upper()
    destination = (_leg_get(leg, "destination") or "").upper()
    if not origin or not destination:
        return result  # pas de route exploitable -> jamais de match

    # --- origin dans home_airports (+ voisins) ---
    home = _csv_to_set(pref.get("home_airports"))
    if home:
        if origin not in expand_with_nearby(home):
            return result

    # --- destination dans dest_airports (+ voisins) ---
    dest = _csv_to_set(pref.get("dest_airports"))
    if dest:
        if destination not in expand_with_nearby(dest):
            return result

    # --- fenetre de dates ---
    leg_date = _leg_get(leg, "date")
    if leg_date:
        df, dt = pref.get("date_from"), pref.get("date_to")
        if df and leg_date < df:
            return result
        if dt and leg_date > dt:
            return result

    # --- seats ---
    min_seats = pref.get("min_seats")
    seats = _leg_get(leg, "seats")
    if min_seats and seats is not None and seats < min_seats:
        return result

    # --- prix (meme devise) ---
    max_price = pref.get("max_price")
    price = _leg_get(leg, "price")
    if max_price is not None:
        if price is None:
            # prix sur demande : on matche mais on signale
            result["price_on_request"] = True
        else:
            leg_cur = (_leg_get(leg, "currency") or "EUR").upper()
            pref_cur = (pref.get("currency") or "EUR").upper()
            if leg_cur == pref_cur and price > max_price:
                return result
            # devises differentes : on ne sait pas convertir -> on ne bloque pas

    result["matched"] = True
    return result


def match_leg(conn, leg, leg_id=None, record=True):
    """Renvoie la liste des subscriber_id qui matchent `leg`.

    leg : dict (sortie parser) ou ligne empty_legs (dict). leg_id : id en base
    (sinon pris dans leg['id']) pour enregistrer les matches sans doublon.
    record=False pour un test pur sans ecriture."""
    if leg_id is None:
        leg_id = leg.get("id")

    matched_ids = []
    for sub, prefs in subscribers_with_prefs(conn, only_active=True):
        # un abonne matche si AU MOINS une de ses preferences colle
        hit = any(preference_matches(leg, p)["matched"] for p in prefs)
        if not hit:
            continue
        matched_ids.append(sub["id"])
        if record and leg_id is not None and not match_exists(conn, leg_id, sub["id"]):
            record_match(conn, leg_id, sub["id"], channel=sub.get("channel"))
    return matched_ids
