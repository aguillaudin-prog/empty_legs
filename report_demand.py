"""Carnet de demande pour le desk courtier Dynami.

Affiche la demande client OUVERTE (intention captee, avec ou sans leg
correspondant) pour que Dynami source proactivement : route, fenetre de dates,
budget, et l'abonne a l'origine de la demande.

Lancer :
    python report_demand.py            # lit empty_legs.db
    python report_demand.py ma.db      # lit une autre base
"""

import sys

from db import connect, open_demand


def _fmt_window(d):
    df, dt = d.get("date_from"), d.get("date_to")
    if df and dt:
        return f"{df} -> {dt}"
    if df:
        return f"des {df}"
    if dt:
        return f"avant {dt}"
    return "dates ouvertes"


def _fmt_budget(d):
    mp = d.get("max_price")
    return f"<= {int(mp)} EUR" if mp is not None else "budget n.c."


def render(conn):
    rows = open_demand(conn)
    lines = []
    lines.append("=" * 70)
    lines.append("CARNET DE DEMANDE OUVERTE — desk Dynami")
    lines.append("=" * 70)
    if not rows:
        lines.append("(aucune demande ouverte)")
        return "\n".join(lines)
    for d in rows:
        route = f"{d.get('origin') or '???'} -> {d.get('dest') or '???'}"
        who = d.get("name") or "demande directe"
        lines.append(f"#{d['id']:<3} {route:<18} {_fmt_window(d):<24} {_fmt_budget(d)}")
        meta = f"      client: {who}"
        if d.get("note"):
            meta += f"  |  note: {d['note']}"
        lines.append(meta)
    lines.append("-" * 70)
    lines.append(f"{len(rows)} demande(s) ouverte(s) a sourcer.")
    return "\n".join(lines)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "empty_legs.db"
    conn = connect(path)
    print(render(conn))
    conn.close()


if __name__ == "__main__":
    main()
