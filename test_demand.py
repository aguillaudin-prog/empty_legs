"""Tranche 5 : carnet de demande. Lancer : python test_demand.py"""

import os
from db import (connect, add_subscriber, add_demand, set_demand_status,
                open_demand)
from report_demand import render

DB = "test_demand.db"
if os.path.exists(DB):
    os.remove(DB)
conn = connect(DB)

# demande rattachee a un abonne
s1 = add_subscriber(conn, "Client St-Tropez", "client@example.com", channel="email")
d1 = add_demand(conn, "nce", "lbg", subscriber_id=s1, date_from="2026-06-20",
                date_to="2026-06-25", max_price=6000, note="vendredi de preference")
# demande directe (sans abonne)
d2 = add_demand(conn, "gva", "lcy", max_price=12000)
# demande deja sourcee -> ne doit pas apparaitre dans le carnet ouvert
d3 = add_demand(conn, "cdg", "ibz", status="sourced")

rows = open_demand(conn)
assert len(rows) == 2, rows
# normalisation majuscules
assert rows[0]["origin"] == "NCE" and rows[0]["dest"] == "LBG"
# jointure abonne
assert rows[0]["name"] == "Client St-Tropez"
# demande directe : pas d'abonne
assert rows[1]["name"] is None
print("OK  add_demand + open_demand (jointure abonne, filtre status)")

# tri : plus ancienne d'abord
assert [r["id"] for r in rows] == [d1, d2]
print("OK  tri par anciennete (a sourcer en priorite)")

# changement de statut -> sort du carnet ouvert
set_demand_status(conn, d1, "closed")
rows = open_demand(conn)
assert [r["id"] for r in rows] == [d2], rows
print("OK  set_demand_status retire la demande du carnet ouvert")

# rendu lisible
out = render(conn)
assert "CARNET DE DEMANDE OUVERTE" in out
assert "GVA -> LCY" in out
print("OK  report_demand.render")

# carnet vide
set_demand_status(conn, d2, "closed")
assert "(aucune demande ouverte)" in render(conn)
print("OK  carnet vide")

conn.close()
os.remove(DB)
print("\nTRANCHE 5 : tous les tests passent.")
