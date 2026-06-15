"""Tranche 3 : notifier (ConsoleNotifier). Lancer : python test_notifier.py"""

import io
import os
from db import (connect, add_subscriber, add_preference, store_leg, leg_by_hash,
                record_match)
from matcher import match_leg
from notifier import (ConsoleNotifier, format_leg_message, format_subject,
                      notifier_for, notify_match, EmailNotifier, TelegramNotifier,
                      CTA)

DB = "test_notif.db"
if os.path.exists(DB):
    os.remove(DB)
conn = connect(DB)

leg = {"origin": "NCE", "destination": "LBG", "route": "NCE-LBG",
       "date": "2026-06-20", "aircraft": "TBM 930", "seats": 3,
       "price": 4500, "currency": "EUR"}

# --- format du message ---
body = format_leg_message(leg)
assert "NCE-LBG" in body
assert "2026-06-20" in body
assert "TBM 930" in body
assert "3 sieges" in body
assert "4500 EUR" in body
assert CTA in body
print("OK  format message complet + CTA Dynami")

# prix sur demande
body2 = format_leg_message(leg, price_on_request=True)
assert "prix sur demande" in body2
body3 = format_leg_message({**leg, "price": None})
assert "prix sur demande" in body3
print("OK  format 'prix sur demande'")

assert format_subject(leg) == "[Empty Leg] NCE-LBG 2026-06-20"
print("OK  sujet email")

# --- ConsoleNotifier capture ---
buf = io.StringIO()
notifier = ConsoleNotifier(stream=buf)
sub = {"id": 1, "name": "Alice", "contact": "console", "channel": "console"}
assert notifier.notify(sub, leg) is True
out = buf.getvalue()
assert "Alice" in out and "NCE-LBG" in out
assert len(notifier.sent) == 1
print("OK  ConsoleNotifier ecrit et garde une trace")

# --- fabrique par canal ---
assert isinstance(notifier_for("console"), ConsoleNotifier)
assert isinstance(notifier_for("email"), EmailNotifier)
assert isinstance(notifier_for("telegram"), TelegramNotifier)
assert isinstance(notifier_for(None), ConsoleNotifier)
print("OK  fabrique notifier_for")

# --- notify_match marque le match notified=1 ---
s1 = add_subscriber(conn, "Alice", "console", channel="console")
add_preference(conn, s1, home_airports=["NCE"], dest_airports=["LBG"], max_price=8000)
store_leg(conn, leg, source="test")
lg = leg_by_hash(conn, leg)
ids = match_leg(conn, lg, leg_id=lg["id"])
assert s1 in ids
mid = conn.execute("SELECT id FROM matches WHERE leg_id=? AND subscriber_id=?",
                   (lg["id"], s1)).fetchone()[0]

cn = ConsoleNotifier(stream=io.StringIO())
ok = notify_match(conn, {"id": s1, "name": "Alice", "channel": "console"}, lg,
                  match_id=mid, notifier=cn)
assert ok
notified = conn.execute("SELECT notified FROM matches WHERE id=?", (mid,)).fetchone()[0]
assert notified == 1
print("OK  notify_match marque matches.notified=1")

conn.close()
os.remove(DB)
print("\nTRANCHE 3 : tous les tests passent.")
