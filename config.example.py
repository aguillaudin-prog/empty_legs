# Copie ce fichier en config.py et remplis-le.
# api_id / api_hash : cree-les sur https://my.telegram.org -> "API development tools"

API_ID = 123456                 # <-- ton api_id (entier)
API_HASH = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # <-- ton api_hash

# Nom de session local (un fichier .session sera cree, garde-le prive)
SESSION = "empty_legs"

# Les 4 groupes a ecouter. Mets le @username public, ou le lien d'invitation,
# ou l'identifiant numerique du chat. Exemples :
GROUPS = [
    "@emptylegs_group_1",
    "@emptylegs_group_2",
    # -1001234567890,        # un groupe prive par son id (recupere via un /id bot ou les logs)
]

DB_PATH = "empty_legs.db"

# Extraction : False = heuristique gratuite et hors-ligne ; True = API Claude (meilleure qualite)
USE_CLAUDE = False
