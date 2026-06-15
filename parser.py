"""Parser d'empty legs : message brut -> ligne structuree. Heuristique (offline) + hook Claude."""

import re
import unicodedata
from datetime import date, timedelta

from airports import AIRPORTS, LOOKUP, LOOKUP_KEYS_SORTED

_city_counts = {}
for _iata, _info in AIRPORTS.items():
    _c = _info["city"].lower()
    _city_counts[_c] = _city_counts.get(_c, 0) + 1
GENERIC_CITY_TOKENS = {c for c, n in _city_counts.items() if n > 1}
CITY_DEFAULT = {"paris": "LBG", "london": "LCY", "milan": "LIN"}

AIRCRAFT = {
    "tbm": "TBM", "tbm850": "TBM 850", "tbm910": "TBM 910", "tbm930": "TBM 930", "tbm940": "TBM 940",
    "pc12": "Pilatus PC-12", "pc24": "Pilatus PC-24", "pilatus": "Pilatus PC-12",
    "phenom100": "Phenom 100", "phenom300": "Phenom 300", "phenom": "Phenom 300",
    "citation": "Citation", "cj1": "Citation CJ1", "cj2": "Citation CJ2", "cj3": "Citation CJ3",
    "cj4": "Citation CJ4", "mustang": "Citation Mustang", "xls": "Citation XLS",
    "latitude": "Citation Latitude", "sovereign": "Citation Sovereign", "longitude": "Citation Longitude",
    "praetor500": "Praetor 500", "praetor600": "Praetor 600", "praetor": "Praetor 600",
    "legacy": "Legacy", "legacy500": "Legacy 500", "legacy600": "Legacy 600",
    "challenger": "Challenger", "challenger300": "Challenger 300", "challenger350": "Challenger 350",
    "challenger605": "Challenger 605", "challenger650": "Challenger 650",
    "global": "Global", "global5000": "Global 5000", "global6000": "Global 6000", "global7500": "Global 7500",
    "falcon": "Falcon", "falcon2000": "Falcon 2000", "falcon900": "Falcon 900", "falcon7x": "Falcon 7X", "falcon8x": "Falcon 8X",
    "gulfstream": "Gulfstream", "g450": "Gulfstream G450", "g550": "Gulfstream G550", "g650": "Gulfstream G650",
    "hawker": "Hawker", "learjet": "Learjet", "lear": "Learjet", "kingair": "King Air",
    "nextant": "Nextant 400XT", "premier": "Premier 1",
}
AIRCRAFT_COMPACT = {re.sub(r"[\s\-]", "", k): v for k, v in AIRCRAFT.items()}
AIRCRAFT_KEYS_SORTED = sorted(AIRCRAFT_COMPACT.keys(), key=len, reverse=True)

MONTHS = {"jan":1,"feb":2,"fev":2,"mar":3,"apr":4,"avr":4,"may":5,"mai":5,"jun":6,"juin":6,
          "jul":7,"juil":7,"aug":8,"aout":8,"sep":9,"oct":10,"nov":11,"dec":12}


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def find_airports_in_order(text):
    low = text.lower()
    used = []
    raw = []

    def overlaps(a, b):
        return any(not (b <= s or a >= e) for s, e in used)

    for key in LOOKUP_KEYS_SORTED:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", low):
            if not overlaps(m.start(), m.end()):
                iata = LOOKUP[key]
                city = AIRPORTS[iata]["city"].lower()
                raw.append((m.start(), key, iata, city, key in GENERIC_CITY_TOKENS))
                used.append((m.start(), m.end()))

    specific_cities = {city for (_, _, _, city, gen) in raw if not gen}
    resolved = []
    for pos, key, iata, city, is_generic in raw:
        if is_generic:
            if city in specific_cities:
                continue
            iata = CITY_DEFAULT.get(city, iata)
        resolved.append((pos, iata))

    resolved.sort(key=lambda x: x[0])
    cleaned = []
    for pos, iata in resolved:
        if not cleaned or cleaned[-1][1] != iata:
            cleaned.append((pos, iata))
    return cleaned


def extract_route(text):
    aps = find_airports_in_order(text)
    if len(aps) >= 2:
        return aps[0][1], aps[1][1]
    if len(aps) == 1:
        return aps[0][1], None
    return None, None


def extract_aircraft(text):
    compact = re.sub(r"[\s\-]", "", _strip_accents(text.lower()))
    for key in AIRCRAFT_KEYS_SORTED:
        if key in compact:
            return AIRCRAFT_COMPACT[key]
    return None


def _norm_cur(tok):
    tok = (tok or "").lower()
    if "£" in tok or "gbp" in tok:
        return "GBP"
    if "$" in tok or "usd" in tok:
        return "USD"
    return "EUR"


def extract_price(text):
    """(montant, devise). Garde les espaces : ne fusionne que les vrais milliers (groupes de 3)."""
    # 1) notation 'k' : 12k, 5.5k€, €12k  (k non suivi d'une lettre -> evite 12kg)
    m = re.search(r"(€|£|\$|eur|gbp|usd)?\s?(\d+(?:\.\d+)?)\s?k(?![a-z])\s?(€|£|\$|eur|gbp|usd)?", text, re.I)
    if m:
        return round(float(m.group(2)) * 1000), _norm_cur((m.group(1) or "") + (m.group(3) or ""))
    # 2) montant colle a une devise. NUM = groupes de milliers (4 500 / 4.500) OU bloc simple
    NUM = r"(\d{1,3}(?:[   .]\d{3})+|\d{3,7})"
    m = re.search(NUM + r"\s?(€|£|\$|eur|gbp|usd|euros?)", text, re.I)
    if m:
        return int(re.sub(r"[   .,]", "", m.group(1))), _norm_cur(m.group(2))
    m = re.search(r"(€|£|\$|eur|gbp|usd|euros?)\s?" + NUM, text, re.I)
    if m:
        return int(re.sub(r"[   .,]", "", m.group(2))), _norm_cur(m.group(1))
    return None, None


def extract_seats(text):
    m = re.search(r"(\d{1,2})\s*(?:pax|seats?|pers(?:onnes?)?|places?|si[eè]ges?|psgr?s?)", text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:pax|seats?|places?|si[eè]ges?)\s*[:=]?\s*(\d{1,2})", text, re.I)
    if m:
        return int(m.group(1))
    return None


def extract_date(text, today=None):
    today = today or date.today()
    low = _strip_accents(text.lower())
    if re.search(r"\b(today|aujourd'?hui|asap|now|immediat)\b", low):
        return today.isoformat()
    if re.search(r"\b(tomorrow|demain)\b", low):
        return (today + timedelta(days=1)).isoformat()
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b", low)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = m.group(3)
        if 1 <= d <= 31 and 1 <= mo <= 12:
            year = today.year
            if y:
                year = int(y) if len(y) == 4 else 2000 + int(y)
            return _safe_date(year, mo, d, today)
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s+([a-z]{3,5})\b", low)
    if m:
        d = int(m.group(1))
        mo = MONTHS.get(m.group(2)[:4]) or MONTHS.get(m.group(2)[:3])
        if mo and 1 <= d <= 31:
            return _safe_date(today.year, mo, d, today)
    return None


def _safe_date(year, month, day, today):
    try:
        dt = date(year, month, day)
    except ValueError:
        return None
    if dt < today - timedelta(days=7):
        try:
            dt = date(year + 1, month, day)
        except ValueError:
            pass
    return dt.isoformat()


def parse_message(text, today=None):
    text = _norm(text or "")
    origin, destination = extract_route(text)
    aircraft = extract_aircraft(text)
    price, currency = extract_price(text)
    seats = extract_seats(text)
    dt = extract_date(text, today)
    score = (0.35 if origin else 0) + (0.35 if destination else 0) + (0.15 if dt else 0) \
            + (0.08 if aircraft else 0) + (0.07 if price else 0)
    return {
        "origin": origin, "destination": destination,
        "route": (origin + "-" + destination) if origin and destination else None,
        "date": dt, "aircraft": aircraft, "seats": seats,
        "price": price, "currency": currency,
        "confidence": round(score, 2), "raw": text,
    }


def parse_with_claude(text, client=None, model="claude-haiku-4-5-20251001"):
    """Version haute qualite via l'API Claude (optionnelle). pip install anthropic + ANTHROPIC_API_KEY."""
    import json
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    prompt = (
        "Tu extrais les infos d'un message d'empty leg (jet prive) en JSON STRICT. "
        "Champs: origin (IATA), destination (IATA), date (YYYY-MM-DD), aircraft, "
        "seats (int), price (number), currency (EUR/GBP/USD), operator. "
        "Mets null si absent. Reponds UNIQUEMENT le JSON.\n\nMessage:\n" + text
    )
    resp = client.messages.create(model=model, max_tokens=400,
                                  messages=[{"role": "user", "content": prompt}])
    txt = resp.content[0].text.strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.MULTILINE).strip()
    data = json.loads(txt)
    data["raw"] = text
    data["confidence"] = 0.95
    return data
