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

CREATE TABLE IF NOT EXISTS subscribers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT,
    contact TEXT,
    channel TEXT DEFAULT 'console',   -- 'email' | 'telegram' | 'console'
    active  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS preferences (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id INTEGER NOT NULL,
    home_airports TEXT,               -- CSV de codes IATA (vide = n'importe où)
    dest_airports TEXT,               -- CSV nullable (vide = toute destination)
    date_from     TEXT,               -- YYYY-MM-DD nullable
    date_to       TEXT,               -- YYYY-MM-DD nullable
    max_price     REAL,               -- nullable
    currency      TEXT DEFAULT 'EUR',
    min_seats     INTEGER,            -- nullable
    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
);
CREATE INDEX IF NOT EXISTS idx_pref_sub ON preferences(subscriber_id);

CREATE TABLE IF NOT EXISTS matches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    leg_id        INTEGER NOT NULL,
    subscriber_id INTEGER NOT NULL,
    matched_at    TEXT,
    notified      INTEGER DEFAULT 0,
    channel       TEXT,
    UNIQUE (leg_id, subscriber_id),
    FOREIGN KEY (leg_id) REFERENCES empty_legs(id),
    FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
);

CREATE TABLE IF NOT EXISTS demand (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id INTEGER,             -- nullable (demande captee sans abonne)
    origin        TEXT,
    dest          TEXT,
    date_from     TEXT,
    date_to       TEXT,
    max_price     REAL,
    note          TEXT,
    status        TEXT DEFAULT 'open', -- 'open' | 'sourced' | 'closed'
    created_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_demand_status ON demand(status);
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


def leg_by_hash(conn, rec):
    """Renvoie la ligne empty_legs (dict) correspondant a rec, ou None.

    Utile apres store_leg (qui ne renvoie qu'un booleen) pour recuperer l'id
    necessaire au matching/notification."""
    cur = conn.execute("SELECT * FROM empty_legs WHERE dedup_hash = ?", (_dedup_hash(rec),))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [c[0] for c in cur.description]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# Abonnes & preferences (matching / alertes)
# ---------------------------------------------------------------------------

def add_subscriber(conn, name, contact, channel="console", active=True):
    """Cree un abonne. Renvoie son id."""
    cur = conn.execute(
        "INSERT INTO subscribers (name, contact, channel, active) VALUES (?,?,?,?)",
        (name, contact, channel, 1 if active else 0))
    conn.commit()
    return cur.lastrowid


def add_preference(conn, subscriber_id, home_airports=None, dest_airports=None,
                   date_from=None, date_to=None, max_price=None, currency="EUR",
                   min_seats=None):
    """Cree une preference pour un abonne. home_airports/dest_airports = liste ou CSV."""
    cur = conn.execute(
        """INSERT INTO preferences
           (subscriber_id, home_airports, dest_airports, date_from, date_to,
            max_price, currency, min_seats)
           VALUES (?,?,?,?,?,?,?,?)""",
        (subscriber_id, _to_csv(home_airports), _to_csv(dest_airports),
         date_from, date_to, max_price, currency, min_seats))
    conn.commit()
    return cur.lastrowid


def get_subscriber(conn, subscriber_id):
    """Renvoie l'abonne (dict) ou None."""
    cur = conn.execute("SELECT * FROM subscribers WHERE id = ?", (subscriber_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [c[0] for c in cur.description]
    return dict(zip(cols, row))


def subscribers_with_prefs(conn, only_active=True):
    """Renvoie [(subscriber_dict, [preference_dict, ...]), ...]."""
    q = "SELECT * FROM subscribers"
    if only_active:
        q += " WHERE active = 1"
    cur = conn.execute(q)
    scols = [c[0] for c in cur.description]
    subs = [dict(zip(scols, r)) for r in cur.fetchall()]
    out = []
    for s in subs:
        pcur = conn.execute("SELECT * FROM preferences WHERE subscriber_id = ?", (s["id"],))
        pcols = [c[0] for c in pcur.description]
        prefs = [dict(zip(pcols, r)) for r in pcur.fetchall()]
        out.append((s, prefs))
    return out


def match_exists(conn, leg_id, subscriber_id):
    """True si un match (leg_id, subscriber_id) est deja enregistre."""
    cur = conn.execute(
        "SELECT 1 FROM matches WHERE leg_id = ? AND subscriber_id = ?",
        (leg_id, subscriber_id))
    return cur.fetchone() is not None


def record_match(conn, leg_id, subscriber_id, channel=None, notified=False):
    """Enregistre un match. Renvoie son id, ou None si doublon (leg_id, subscriber_id)."""
    try:
        cur = conn.execute(
            """INSERT INTO matches (leg_id, subscriber_id, matched_at, notified, channel)
               VALUES (?,?,?,?,?)""",
            (leg_id, subscriber_id, datetime.now().isoformat(timespec="seconds"),
             1 if notified else 0, channel))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def mark_notified(conn, match_id):
    """Marque un match comme notifie."""
    conn.execute("UPDATE matches SET notified = 1 WHERE id = ?", (match_id,))
    conn.commit()


def _to_csv(value):
    """Liste/tuple -> CSV normalise (codes en majuscules). Chaine/None laisses tels quels."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return ",".join(str(v).strip().upper() for v in value if str(v).strip())
    return value


# ---------------------------------------------------------------------------
# Carnet de demande (intention client a sourcer par le desk Dynami)
# ---------------------------------------------------------------------------

def add_demand(conn, origin, dest, subscriber_id=None, date_from=None, date_to=None,
               max_price=None, note=None, status="open"):
    """Enregistre une intention client (meme sans leg correspondant). Renvoie son id."""
    cur = conn.execute(
        """INSERT INTO demand
           (subscriber_id, origin, dest, date_from, date_to, max_price, note, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (subscriber_id, (origin or "").upper() or None, (dest or "").upper() or None,
         date_from, date_to, max_price, note, status,
         datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    return cur.lastrowid


def set_demand_status(conn, demand_id, status):
    """Passe une demande a 'open' | 'sourced' | 'closed'."""
    conn.execute("UPDATE demand SET status = ? WHERE id = ?", (status, demand_id))
    conn.commit()


def open_demand(conn):
    """Liste la demande ouverte pour le desk Dynami (route, fenetre, budget),
    abonne joint si renseigne. Plus ancienne d'abord (a sourcer en priorite)."""
    cur = conn.execute(
        """SELECT d.id, d.origin, d.dest, d.date_from, d.date_to, d.max_price,
                  d.note, d.created_at, s.name, s.contact, s.channel
           FROM demand d
           LEFT JOIN subscribers s ON s.id = d.subscriber_id
           WHERE d.status = 'open'
           ORDER BY d.created_at ASC""")
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def seed_demo(conn):
    """Cree quelques abonnes + preferences de demonstration. Renvoie les ids crees."""
    ids = []
    sid = add_subscriber(conn, "Desk Dynami", "console", channel="console")
    add_preference(conn, sid, home_airports=["NCE", "CEQ"], dest_airports=["LBG", "GVA"],
                   max_price=8000, currency="EUR", min_seats=2)
    ids.append(sid)

    sid = add_subscriber(conn, "Client St-Tropez", "client@example.com", channel="email")
    add_preference(conn, sid, home_airports=["LTT", "NCE"], dest_airports=None,
                   date_from="2026-06-15", date_to="2026-06-30", max_price=15000)
    ids.append(sid)
    return ids
