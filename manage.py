"""Outil en ligne de commande pour piloter le radar SANS ecrire de Python.

Exemples :
    python manage.py legs                       # vols (empty legs) actifs en base
    python manage.py demande                     # carnet de demande ouverte (desk Dynami)
    python manage.py abonnes                     # liste des abonnes + leurs preferences

    # creer un abonne (canal : console | email | telegram)
    python manage.py ajouter-abonne --nom "Client St-Tropez" \
        --contact client@example.com --canal email

    # lui ajouter une preference (codes IATA separes par des virgules)
    python manage.py ajouter-pref --abonne 1 --depart NCE,CEQ --arrivee LBG,GVA \
        --prix-max 8000 --sieges-min 2 --du 2026-06-15 --au 2026-06-30

    # enregistrer une demande client (intention a sourcer)
    python manage.py ajouter-demande --depart NCE --arrivee LBG \
        --prix-max 6000 --note "vendredi de preference" --abonne 1

    python manage.py demo                        # jeu de donnees de demonstration

Toutes les commandes acceptent --base pour viser une autre base SQLite
(par defaut : empty_legs.db).
"""

import argparse

from db import (connect, add_subscriber, add_preference, subscribers_with_prefs,
                add_demand, active_legs, seed_demo)
from report_demand import render as render_demand


def _csv(value):
    """'nce, ceq' -> ['NCE', 'CEQ'] ; vide/None -> None."""
    if not value:
        return None
    return [v.strip().upper() for v in value.split(",") if v.strip()]


def cmd_legs(conn, args):
    rows = active_legs(conn)
    if not rows:
        print("(aucun empty leg actif)")
        return
    print(f"{len(rows)} empty leg(s) actif(s) :")
    for route, dt, ac, seats, price, cur, src, recu in rows:
        prix = f"{int(price)} {cur}" if price is not None else "prix sur demande"
        print(f"  {route:<10} {dt or 'date n.c.':<12} {ac or 'appareil n.c.':<16} "
              f"{(str(seats) + ' sieges') if seats is not None else 'sieges n.c.':<12} {prix}")


def cmd_demande(conn, args):
    print(render_demand(conn))


def cmd_abonnes(conn, args):
    data = subscribers_with_prefs(conn, only_active=False)
    if not data:
        print("(aucun abonne)")
        return
    for sub, prefs in data:
        etat = "actif" if sub["active"] else "inactif"
        print(f"#{sub['id']} {sub['name']} [{sub['channel']}] {sub['contact']} ({etat})")
        if not prefs:
            print("    (aucune preference)")
        for p in prefs:
            depart = p["home_airports"] or "n'importe ou"
            arrivee = p["dest_airports"] or "toute destination"
            budget = f"<= {int(p['max_price'])} {p['currency']}" if p["max_price"] is not None else "budget libre"
            fenetre = f"{p['date_from'] or '...'} -> {p['date_to'] or '...'}"
            sieges = f", >= {p['min_seats']} sieges" if p["min_seats"] else ""
            print(f"    pref #{p['id']}: {depart} -> {arrivee} | {fenetre} | {budget}{sieges}")


def cmd_ajouter_abonne(conn, args):
    sid = add_subscriber(conn, args.nom, args.contact, channel=args.canal)
    print(f"Abonne cree : #{sid} {args.nom} [{args.canal}]")


def cmd_ajouter_pref(conn, args):
    pid = add_preference(conn, args.abonne, home_airports=_csv(args.depart),
                         dest_airports=_csv(args.arrivee), date_from=args.du,
                         date_to=args.au, max_price=args.prix_max,
                         currency=args.devise, min_seats=args.sieges_min)
    print(f"Preference creee : #{pid} pour l'abonne #{args.abonne}")


def cmd_ajouter_demande(conn, args):
    did = add_demand(conn, args.depart, args.arrivee, subscriber_id=args.abonne,
                     date_from=args.du, date_to=args.au, max_price=args.prix_max,
                     note=args.note)
    print(f"Demande enregistree : #{did} {args.depart} -> {args.arrivee}")


def cmd_demo(conn, args):
    ids = seed_demo(conn)
    print(f"Jeu de demonstration cree : {len(ids)} abonne(s) (#{', #'.join(map(str, ids))}).")


def build_parser():
    p = argparse.ArgumentParser(description="Piloter le radar empty legs sans coder.")
    p.add_argument("--base", default="empty_legs.db", help="fichier SQLite (defaut: empty_legs.db)")
    sub = p.add_subparsers(dest="commande", required=True)

    sub.add_parser("legs", help="lister les empty legs actifs").set_defaults(func=cmd_legs)
    sub.add_parser("demande", help="afficher le carnet de demande ouverte").set_defaults(func=cmd_demande)
    sub.add_parser("abonnes", help="lister les abonnes et leurs preferences").set_defaults(func=cmd_abonnes)
    sub.add_parser("demo", help="creer un jeu de donnees de demonstration").set_defaults(func=cmd_demo)

    a = sub.add_parser("ajouter-abonne", help="creer un abonne")
    a.add_argument("--nom", required=True)
    a.add_argument("--contact", required=True, help="email, chat_id Telegram, ou 'console'")
    a.add_argument("--canal", default="console", choices=["console", "email", "telegram"])
    a.set_defaults(func=cmd_ajouter_abonne)

    pr = sub.add_parser("ajouter-pref", help="ajouter une preference a un abonne")
    pr.add_argument("--abonne", type=int, required=True, help="id de l'abonne")
    pr.add_argument("--depart", help="codes IATA separes par virgules (vide = n'importe ou)")
    pr.add_argument("--arrivee", help="codes IATA separes par virgules (vide = toute destination)")
    pr.add_argument("--du", help="date debut YYYY-MM-DD")
    pr.add_argument("--au", help="date fin YYYY-MM-DD")
    pr.add_argument("--prix-max", type=float, dest="prix_max")
    pr.add_argument("--devise", default="EUR")
    pr.add_argument("--sieges-min", type=int, dest="sieges_min")
    pr.set_defaults(func=cmd_ajouter_pref)

    d = sub.add_parser("ajouter-demande", help="enregistrer une demande client")
    d.add_argument("--depart", required=True)
    d.add_argument("--arrivee", required=True)
    d.add_argument("--du", help="date debut YYYY-MM-DD")
    d.add_argument("--au", help="date fin YYYY-MM-DD")
    d.add_argument("--prix-max", type=float, dest="prix_max")
    d.add_argument("--note")
    d.add_argument("--abonne", type=int, help="id de l'abonne a l'origine (optionnel)")
    d.set_defaults(func=cmd_ajouter_demande)

    return p


def main():
    args = build_parser().parse_args()
    conn = connect(args.base)
    args.func(conn, args)
    conn.close()


if __name__ == "__main__":
    main()
