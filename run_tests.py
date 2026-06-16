"""Lance TOUS les tests d'un coup et affiche un bilan clair.

    python run_tests.py

Code de sortie 0 si tout passe, 1 sinon (pratique pour la CI plus tard).
Les tests sont des scripts autonomes : chacun cree/supprime sa propre base.
"""

import subprocess
import sys

TESTS = [
    "test_parser.py",
    "test_integration.py",
    "test_db_subscribers.py",
    "test_matcher.py",
    "test_notifier.py",
    "test_listener_flow.py",
    "test_demand.py",
]


def main():
    echecs = []
    for t in TESTS:
        r = subprocess.run([sys.executable, t], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  PASS  {t}")
        else:
            echecs.append(t)
            print(f"  FAIL  {t}")
            # on montre la sortie d'erreur pour diagnostiquer tout de suite
            sortie = (r.stdout + r.stderr).strip()
            for ligne in sortie.splitlines()[-15:]:
                print(f"        {ligne}")

    print("-" * 50)
    if echecs:
        print(f"{len(echecs)} test(s) en echec : {', '.join(echecs)}")
        sys.exit(1)
    print(f"OK — les {len(TESTS)} suites de tests passent.")


if __name__ == "__main__":
    main()
