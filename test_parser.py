"""
Test du parser sur des messages d'empty legs réalistes (FR/EN, format crasseux de groupe).
Lance : python3 test_parser.py
Remplace ensuite SAMPLES par tes vrais messages pour calibrer.
"""

from parser import parse_message

SAMPLES = [
    "TBM930 NCE-LBG 14/06 3pax 4500€ dispo",
    "Empty leg Challenger 350 Geneva > Nice 16 June 7 pax 12k€ contact ops",
    "EL dispo demain LBG-GVA Phenom 300 4500 eur 6 seats",
    "⚡ One way Citation XLS Cannes➡London City 20/06 8pax £9500",
    "Ferry flight Pilatus PC12 Olbia/Nice 18.06 4 places 3 900€",
    "Dispo: Falcon 7X PARIS LE BOURGET to IBIZA 22 juin 12 pax, prix sur demande",
    "global 6000 LFMN LSGG tomorrow 13 pax 15000€",
    "Nouvelle promo voiture occasion -50% cliquez ici",  # bruit : doit être ignoré
    "St Tropez - Geneve 15/07 King Air 350 6 pax 5.5k€",
    "Legacy 600 MXP-NCE 14 juin // 9 seats // 8000 EUR // operator JetX",
]


def main():
    print("=" * 78)
    print("TEST PARSER EMPTY LEGS")
    print("=" * 78)
    kept, ignored = 0, 0
    for i, msg in enumerate(SAMPLES, 1):
        r = parse_message(msg)
        usable = bool(r["origin"] and r["destination"])
        tag = "✅ EXPLOITABLE" if usable else "⛔ ignoré (pas de route)"
        if usable:
            kept += 1
        else:
            ignored += 1
        print(f"\n[{i}] {msg}")
        print(f"    -> {tag}  (confiance {r['confidence']})")
        if usable:
            print(f"       route={r['route']}  date={r['date']}  appareil={r['aircraft']}  "
                  f"sièges={r['seats']}  prix={r['price']} {r['currency'] or ''}")
    print("\n" + "-" * 78)
    print(f"Bilan : {kept} empty legs exploitables, {ignored} messages écartés.")


if __name__ == "__main__":
    main()
