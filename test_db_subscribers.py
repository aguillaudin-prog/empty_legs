"""Tranche 1 : abonnes, preferences, matches. Lancer : python test_db_subscribers.py"""

import os
from db import (connect, add_subscriber, add_preference, get_subscriber,
                subscribers_with_prefs, record_match, match_exists, mark_notified,
                seed_demo, store_leg, leg_by_hash)

DB = "test_subs.db"
if os.path.exists(DB):
    os.remove(DB)
conn = connect(DB)

# --- CRUD abonne + preference ---
sid = add_subscriber(conn, "Alice", "alice@example.com", channel="email")
pid = add_preference(conn, sid, home_airports=["nce", "ceq"], dest_airports=["LBG"],
                     max_price=9000, min_seats=2)
sub = get_subscriber(conn, sid)
assert sub["name"] == "Alice"
assert sub["channel"] == "email"
assert sub["active"] == 1

subs = subscribers_with_prefs(conn)
assert len(subs) == 1
s, prefs = subs[0]
assert len(prefs) == 1
# liste -> CSV normalise en majuscules
assert prefs[0]["home_airports"] == "NCE,CEQ"
assert prefs[0]["dest_airports"] == "LBG"
assert prefs[0]["max_price"] == 9000
assert prefs[0]["currency"] == "EUR"
print("OK  CRUD abonne + preference")

# --- abonne inactif filtre ---
sid2 = add_subscriber(conn, "Bob", "console", channel="console", active=False)
assert len(subscribers_with_prefs(conn, only_active=True)) == 1
assert len(subscribers_with_prefs(conn, only_active=False)) == 2
print("OK  filtrage actifs/inactifs")

# --- matches + anti-doublon ---
rec = {"origin": "NCE", "destination": "LBG", "route": "NCE-LBG",
       "date": "2026-06-20", "aircraft": "TBM 930", "price": 4500,
       "currency": "EUR", "seats": 3, "confidence": 0.9, "raw": "x"}
assert store_leg(conn, rec, source="test") is True
leg = leg_by_hash(conn, rec)
assert leg is not None and leg["route"] == "NCE-LBG"

mid = record_match(conn, leg["id"], sid, channel="email")
assert mid is not None
assert match_exists(conn, leg["id"], sid) is True
# doublon -> None
assert record_match(conn, leg["id"], sid, channel="email") is None
print("OK  match + anti-doublon")

# --- mark_notified ---
mark_notified(conn, mid)
row = conn.execute("SELECT notified FROM matches WHERE id = ?", (mid,)).fetchone()
assert row[0] == 1
print("OK  mark_notified")

# --- seed_demo ---
conn2 = connect(":memory:")
ids = seed_demo(conn2)
assert len(ids) == 2
assert len(subscribers_with_prefs(conn2)) == 2
print("OK  seed_demo")

conn.close()
os.remove(DB)
print("\nTRANCHE 1 : tous les tests passent.")
