import os
from parser import parse_message
from db import connect, store_leg, active_legs

if os.path.exists("test.db"):
    os.remove("test.db")
conn = connect("test.db")

msgs = [
    "TBM930 NCE-LBG 14/06 3pax 4500€",
    "TBM930 NCE-LBG 14/06 3pax 4500€",        # doublon exact -> doit etre rejete
    "Challenger 350 GVA-NCE 16 June 7pax 12k€",
    "Promo voiture -50% cliquez ici",          # bruit -> rejete
]
new, dup = 0, 0
for m in msgs:
    rec = parse_message(m)
    ok = store_leg(conn, rec, source="telegram:test")
    new += ok
    dup += (not ok)
print(f"stockes={new}  rejetes(doublon/bruit)={dup}")
print("--- empty legs actifs en base ---")
for row in active_legs(conn):
    print(" ", row[:6])
os.remove("test.db")
