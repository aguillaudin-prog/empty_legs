"""Tranche 4 : flux temps reel store -> match -> notify, branche comme dans listener.py.

listener.py importe Telethon + config.py (absents en test) ; on valide donc ici
la meme sequence de fonctions, dans les deux modes (matching on/off).
Lancer : python test_listener_flow.py
"""

import io
import os
from db import (connect, add_subscriber, add_preference, store_leg, leg_by_hash,
                get_subscriber)
from matcher import match_leg
from notifier import ConsoleNotifier, notify_match

DB = "test_flow.db"
if os.path.exists(DB):
    os.remove(DB)
conn = connect(DB)

s1 = add_subscriber(conn, "Desk Dynami", "console", channel="console")
add_preference(conn, s1, home_airports=["NCE"], dest_airports=["LBG"], max_price=8000)

rec = {"origin": "NCE", "destination": "LBG", "route": "NCE-LBG",
       "date": "2026-06-20", "aircraft": "TBM 930", "seats": 3,
       "price": 4500, "currency": "EUR", "confidence": 0.9, "raw": "x"}


def flow_with_matching(rec):
    """Reproduit la branche MATCHING_ENABLED=True du listener."""
    buf = io.StringIO()
    notifier = ConsoleNotifier(stream=buf)
    if not store_leg(conn, rec, source="telegram:test"):
        return buf, []
    leg = leg_by_hash(conn, rec)
    notified = []
    for sub_id in match_leg(conn, leg, leg_id=leg["id"]):
        row = conn.execute(
            "SELECT id FROM matches WHERE leg_id=? AND subscriber_id=? AND notified=0",
            (leg["id"], sub_id)).fetchone()
        if not row:
            continue
        sub = get_subscriber(conn, sub_id)
        notify_match(conn, sub, leg, match_id=row[0], notifier=notifier)
        notified.append(sub_id)
    return buf, notified


# --- mode matching ON : l'abonne est notifie ---
buf, notified = flow_with_matching(rec)
assert s1 in notified, notified
assert "Desk Dynami" in buf.getvalue() and "NCE-LBG" in buf.getvalue()
print("OK  matching ON : leg stocke -> abonne notifie")

# --- relance sur le meme leg (doublon store) : aucune nouvelle notif ---
buf2, notified2 = flow_with_matching(rec)
assert notified2 == [], notified2  # store_leg renvoie False (doublon)
print("OK  doublon de leg : pas de re-notification")

# --- mode ecouteur seul (matching OFF) : on stocke sans notifier ---
rec2 = {**rec, "date": "2026-06-21"}  # leg different
ok = store_leg(conn, rec2, source="telegram:test")  # branche OFF = juste store
assert ok is True
# aucune table matches touchee pour ce leg
leg2 = leg_by_hash(conn, rec2)
n = conn.execute("SELECT COUNT(*) FROM matches WHERE leg_id=?", (leg2["id"],)).fetchone()[0]
assert n == 0
print("OK  matching OFF : leg stocke, aucune notification")

conn.close()
os.remove(DB)
print("\nTRANCHE 4 : tous les tests passent.")
