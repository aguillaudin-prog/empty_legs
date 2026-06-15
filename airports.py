"""
Référentiel d'aéroports orienté aviation d'affaires (focus Europe / Riviera).
Sert à reconnaître les codes IATA, ICAO, et noms de villes dans les messages.
Ajoute-en librement : plus la liste est riche, mieux le parser matche les routes.
"""

# Chaque entrée : code IATA canonique -> infos + alias (villes, ICAO, surnoms)
AIRPORTS = {
    # --- Côte d'Azur / Sud-Est ---
    "NCE": {"name": "Nice Côte d'Azur", "icao": "LFMN", "city": "Nice", "aliases": ["nice", "cote d'azur", "côte d'azur"]},
    "CEQ": {"name": "Cannes Mandelieu", "icao": "LFMD", "city": "Cannes", "aliases": ["cannes", "mandelieu"]},
    "LTT": {"name": "Saint-Tropez La Môle", "icao": "LFTZ", "city": "Saint-Tropez", "aliases": ["saint-tropez", "st tropez", "st-tropez", "la mole", "la môle"]},
    "MRS": {"name": "Marseille Provence", "icao": "LFML", "city": "Marseille", "aliases": ["marseille"]},
    "TLN": {"name": "Toulon-Hyères", "icao": "LFTH", "city": "Toulon", "aliases": ["toulon", "hyeres", "hyères"]},
    "CMF": {"name": "Chambéry", "icao": "LFLB", "city": "Chambéry", "aliases": ["chambery", "chambéry"]},
    "MCM": {"name": "Monaco (héliport)", "icao": "LNMC", "city": "Monaco", "aliases": ["monaco", "monte carlo", "monte-carlo"]},

    # --- Paris ---
    "LBG": {"name": "Paris Le Bourget", "icao": "LFPB", "city": "Paris", "aliases": ["le bourget", "bourget", "paris"]},
    "CDG": {"name": "Paris Charles de Gaulle", "icao": "LFPG", "city": "Paris", "aliases": ["roissy", "charles de gaulle", "cdg"]},
    "ORY": {"name": "Paris Orly", "icao": "LFPO", "city": "Paris", "aliases": ["orly"]},

    # --- Suisse ---
    "GVA": {"name": "Genève", "icao": "LSGG", "city": "Genève", "aliases": ["geneva", "geneve", "genève"]},
    "ZRH": {"name": "Zurich", "icao": "LSZH", "city": "Zurich", "aliases": ["zurich", "zürich"]},
    "SIR": {"name": "Sion", "icao": "LSGS", "city": "Sion", "aliases": ["sion"]},

    # --- Royaume-Uni ---
    "LCY": {"name": "London City", "icao": "EGLC", "city": "London", "aliases": ["london city", "londres"]},
    "LTN": {"name": "Luton", "icao": "EGGW", "city": "London", "aliases": ["luton"]},
    "FAB": {"name": "Farnborough", "icao": "EGLF", "city": "Farnborough", "aliases": ["farnborough"]},
    "STN": {"name": "Stansted", "icao": "EGSS", "city": "London", "aliases": ["stansted"]},
    "BQH": {"name": "Biggin Hill", "icao": "EGKB", "city": "London", "aliases": ["biggin hill", "biggin"]},

    # --- Italie ---
    "LIN": {"name": "Milan Linate", "icao": "LIML", "city": "Milan", "aliases": ["linate", "milan", "milano"]},
    "MXP": {"name": "Milan Malpensa", "icao": "LIMC", "city": "Milan", "aliases": ["malpensa"]},
    "OLB": {"name": "Olbia", "icao": "LIEO", "city": "Olbia", "aliases": ["olbia", "costa smeralda"]},
    "ROM": {"name": "Rome Ciampino", "icao": "LIRA", "city": "Rome", "aliases": ["ciampino", "rome", "roma"]},

    # --- Espagne / Baléares ---
    "IBZ": {"name": "Ibiza", "icao": "LEIB", "city": "Ibiza", "aliases": ["ibiza", "eivissa"]},
    "PMI": {"name": "Palma de Majorque", "icao": "LEPA", "city": "Palma", "aliases": ["palma", "majorque", "mallorca"]},
    "MAD": {"name": "Madrid", "icao": "LEMD", "city": "Madrid", "aliases": ["madrid"]},
    "BCN": {"name": "Barcelone", "icao": "LEBL", "city": "Barcelone", "aliases": ["barcelona", "barcelone"]},

    # --- Corse ---
    "AJA": {"name": "Ajaccio", "icao": "LFKJ", "city": "Ajaccio", "aliases": ["ajaccio"]},
    "FSC": {"name": "Figari", "icao": "LFKF", "city": "Figari", "aliases": ["figari"]},
    "CLY": {"name": "Calvi", "icao": "LFKC", "city": "Calvi", "aliases": ["calvi"]},
}


def _build_lookup():
    """Construit un index { token_normalisé : code_IATA } pour la reconnaissance."""
    lookup = {}
    for iata, info in AIRPORTS.items():
        lookup[iata.lower()] = iata
        lookup[info["icao"].lower()] = iata
        lookup[info["city"].lower()] = iata
        for alias in info.get("aliases", []):
            lookup[alias.lower()] = iata
    return lookup


LOOKUP = _build_lookup()

# Tokens triés du plus long au plus court pour matcher d'abord les alias multi-mots
LOOKUP_KEYS_SORTED = sorted(LOOKUP.keys(), key=len, reverse=True)


def resolve_airport(token: str):
    """Renvoie le code IATA canonique pour un token, ou None."""
    return LOOKUP.get(token.lower().strip())


def airport_label(iata: str) -> str:
    info = AIRPORTS.get(iata)
    return f"{iata} ({info['name']})" if info else iata
