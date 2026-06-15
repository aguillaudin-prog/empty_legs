"""Stockage SQLite des empty legs : dedup + expiration. Zero serveur, un simple fichier."""

import hashlib
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "empty_legs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS empty_legs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_hash  TEXT UNIQUE,
    origin      TEXT, destination TEXT, route TEXT,
    flight_date TEXT, aircraft TEXT, seats INTEGER,
    price REAL, currency TEXT, operator TEXT,
    confidence REAL, source TEXT, raw TEXT,
    received_at TEXT, expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_route ON empty_legs(route);
CREATE INDEX IF NOT EXISTS idx_date  ON empty_legs(flight_date);
"""


def _dedup_hash(rec):
    key = f"{rec.get('origin')}|{rec.get('destination')}|{rec.get('date')}|{rec.get('aircraft')}|{rec.get('price')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def store_leg(conn, rec, source=None, ttl_hours=72):
    """Insere un empty leg. True si nouveau, False si doublon/bruit (sans route exploitable)."""
    if not rec.get("origin") or not rec.get("destination"):
        return False
    now = datetime.now()
    expires = now + timedelta(hours=ttl_hours)
    try:
        conn.execute(
            """INSERT INTO empty_legs
               (dedup_hash, origin, destination, route, flight_date, aircraft, seats,
                price, currency, operator, confidence, source, raw, received_at, expires_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (_dedup_hash(rec), rec.get("origin"), rec.get("destination"), rec.get("route"),
             rec.get("date"), rec.get("aircraft"), rec.get("seats"), rec.get("price"),
             rec.get("currency"), rec.get("operator"), rec.get("confidence"), source,
             rec.get("raw"), now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def active_legs(conn):
    """Empty legs non perimes, plus recents d'abord."""
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "SELECT route, flight_date, aircraft, seats, price, currency, source, received_at "
        "FROM empty_legs WHERE expires_at > ? ORDER BY received_at DESC", (now,))
    return cur.fetchall()
