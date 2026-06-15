"""Tranche 2 : moteur de matching. Lancer : python test_matcher.py"""

import os
from db import (connect, add_subscriber, add_preference, store_leg, leg_by_hash,
                match_exists)
from matcher import match_leg, preference_matches

DB = "test_match.db"
if os.path.exists(DB):
    os.remove(DB)
conn = connect(DB)


def leg(origin, destination, date=None, price=None, currency="EUR", seats=None):
    rec = {"origin": origin, "destination": destination,
           "route": f"{origin}-{destination}", "date": date, "aircraft": "TBM 930",
           "price": price, "currency": currency, "seats": seats,
           "confidence": 0.9, "raw": "x"}
    return rec


# Abonne 1 : NCE->LBG, <=8000 EUR, min 2 sieges, fenetre 15-30 juin
s1 = add_subscriber(conn, "S1", "console")
add_preference(conn, s1, home_airports=["NCE"], dest_airports=["LBG"],
               date_from="2026-06-15", date_to="2026-06-30",
               max_price=8000, currency="EUR", min_seats=2)

# Abonne 2 : depart n'importe ou -> GVA, sans contrainte de prix/date
s2 = add_subscriber(conn, "S2", "console")
add_preference(conn, s2, home_airports=None, dest_airports=["GVA"])

# --- CAS POSITIFS ---
m = match_leg(conn, leg("NCE", "LBG", "2026-06-20", 4500, "EUR", 3), record=False)
assert s1 in m, m
print("OK  match nominal NCE->LBG dans budget/fenetre/sieges")

# proximite : CEQ voisin de NCE -> doit matcher home=NCE
m = match_leg(conn, leg("CEQ", "LBG", "2026-06-20", 4500, "EUR", 3), record=False)
assert s1 in m, m
print("OK  match par proximite (CEQ voisin de NCE)")

# n'importe ou -> GVA
m = match_leg(conn, leg("MXP", "GVA", None, None, "EUR", None), record=False)
assert s2 in m and s1 not in m, m
print("OK  home vide = depart de n'importe ou")

# prix sur demande -> matche quand meme, signale price_on_request
r = preference_matches(leg("NCE", "LBG", "2026-06-20", None, "EUR", 4),
                       {"home_airports": "NCE", "dest_airports": "LBG",
                        "max_price": 8000, "currency": "EUR"})
assert r["matched"] and r["price_on_request"], r
print("OK  prix sur demande matche et est signale")

# --- CAS NEGATIFS ---
# prix trop haut
m = match_leg(conn, leg("NCE", "LBG", "2026-06-20", 12000, "EUR", 3), record=False)
assert s1 not in m, m
print("OK  rejet prix > max_price")

# date hors fenetre
m = match_leg(conn, leg("NCE", "LBG", "2026-07-15", 4500, "EUR", 3), record=False)
assert s1 not in m, m
print("OK  rejet date hors fenetre")

# pas assez de sieges
m = match_leg(conn, leg("NCE", "LBG", "2026-06-20", 4500, "EUR", 1), record=False)
assert s1 not in m, m
print("OK  rejet sieges < min_seats")

# mauvaise destination
m = match_leg(conn, leg("NCE", "MXP", "2026-06-20", 4500, "EUR", 3), record=False)
assert s1 not in m, m
print("OK  rejet destination hors dest_airports")

# devise differente -> pas de blocage sur prix (on ne convertit pas)
m = match_leg(conn, leg("NCE", "LBG", "2026-06-20", 12000, "GBP", 3), record=False)
assert s1 in m, m
print("OK  devise differente : pas de blocage prix")

# seats absent -> n'exclut pas
m = match_leg(conn, leg("NCE", "LBG", "2026-06-20", 4500, "EUR", None), record=False)
assert s1 in m, m
print("OK  sieges absents n'excluent pas")

# --- ENREGISTREMENT + ANTI-DOUBLON ---
rec = leg("NCE", "LBG", "2026-06-20", 4500, "EUR", 3)
store_leg(conn, rec, source="test")
lg = leg_by_hash(conn, rec)
m1 = match_leg(conn, lg, leg_id=lg["id"])
assert s1 in m1
assert match_exists(conn, lg["id"], s1)
# 2e appel : ne doit pas creer de doublon
m2 = match_leg(conn, lg, leg_id=lg["id"])
n = conn.execute("SELECT COUNT(*) FROM matches WHERE leg_id=? AND subscriber_id=?",
                 (lg["id"], s1)).fetchone()[0]
assert n == 1, n
print("OK  enregistrement match + anti-doublon")

conn.close()
os.remove(DB)
print("\nTRANCHE 2 : tous les tests passent.")
