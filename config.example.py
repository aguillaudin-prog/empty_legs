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

# Matching + alertes : True = a chaque empty leg stocke, on cherche les abonnes
# dont une preference colle et on les notifie (cf. matcher.py / notifier.py).
# False = mode "ecouteur seul" historique (on se contente de ranger en base).
MATCHING_ENABLED = False

# Secrets de notification : a definir en VARIABLES D'ENVIRONNEMENT, jamais ici.
#   Email (canal 'email')   : SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
#   Telegram (canal 'telegram') : TELEGRAM_BOT_TOKEN
# Les abonnes/preferences se gerent en base (db.py : add_subscriber/add_preference,
# ou seed_demo pour un jeu de demonstration).
