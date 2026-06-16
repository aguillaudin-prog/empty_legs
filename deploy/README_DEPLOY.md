# Déployer l'écouteur sur un petit serveur (VPS) — guide pas-à-pas

Objectif : faire tourner `listener.py` **en continu (24/7)** sur une machine qui
reste allumée. Compte ~20-30 min la première fois. Tu n'as à faire ça **qu'une fois**.

> Pourquoi un VPS et pas la session web ? Le login Telegram se fait une fois avec
> ton téléphone + un code (interactif), et l'agent doit ensuite tourner sans
> interruption. Un petit serveur toujours allumé est l'endroit naturel pour ça.

---

## 1. Créer le serveur (≈ 5 min)
- Prends un petit VPS chez n'importe quel hébergeur (Hetzner, DigitalOcean, OVH, Scaleway…).
- Choix suffisant : **1 vCPU / 1 Go RAM**, **Ubuntu 24.04 LTS** (~4-6 €/mois).
- À la création, note l'**adresse IP** et le **mot de passe root** (ou ajoute ta clé SSH).

## 2. Se connecter au serveur
Depuis n'importe quel terminal (ou la console web de l'hébergeur) :
```bash
ssh root@TON_IP
```

## 3. Installer les outils + créer un utilisateur dédié
```bash
apt update && apt install -y python3 python3-venv git
adduser --disabled-password --gecos "" emptylegs
```

## 4. Récupérer le code
Le dépôt est privé : crée un **Personal Access Token** GitHub (Settings → Developer
settings → Tokens, scope `repo`) et utilise-le dans l'URL de clone.
```bash
cd /opt
git clone -b claude/fervent-cori-1bmo8r https://TON_TOKEN@github.com/aguillaudin-prog/empty_legs.git
chown -R emptylegs:emptylegs /opt/empty_legs
```

## 5. Installer les dépendances (dans un environnement isolé)
```bash
cd /opt/empty_legs
sudo -u emptylegs python3 -m venv .venv
sudo -u emptylegs .venv/bin/pip install -r requirements.txt
```

## 6. Configurer
```bash
sudo -u emptylegs cp config.example.py config.py
sudo -u emptylegs nano config.py     # remplis API_ID, API_HASH, GROUPS
```
(Ctrl+O pour enregistrer, Ctrl+X pour quitter nano.)

## 7. Login Telegram — UNE SEULE FOIS (interactif)
```bash
sudo -u emptylegs .venv/bin/python listener.py
```
- Saisis ton **numéro** (+33…), puis le **code** reçu sur Telegram (et ton mot de passe 2FA si tu en as un).
- Quand tu vois `Connecté en tant que …`, c'est bon : un fichier `.session` est créé.
- Fais **Ctrl+C** pour arrêter : on va maintenant le faire tourner proprement en tâche de fond.

## 8. Le faire tourner 24/7 (service systemd)
```bash
cp /opt/empty_legs/deploy/empty-legs.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now empty-legs
```
C'est tout : l'agent tourne, redémarre tout seul s'il plante, et repart même après un reboot du serveur.

## Commandes utiles ensuite
```bash
systemctl status empty-legs        # voir s'il tourne
tail -f /var/log/empty_legs.log    # voir les empty legs captés en direct
systemctl restart empty-legs       # après avoir modifié config.py
```

## Mettre à jour le code plus tard
```bash
cd /opt/empty_legs && sudo -u emptylegs git pull
systemctl restart empty-legs
```

---

### Activer les alertes (optionnel)
1. Dans `config.py` : `MATCHING_ENABLED = True`.
2. Crée abonnés/préférences : `sudo -u emptylegs .venv/bin/python manage.py ajouter-abonne ...`
3. Mets les secrets de notif dans le service : édite `/etc/systemd/system/empty-legs.service`,
   décommente les lignes `Environment=...`, puis `systemctl daemon-reload && systemctl restart empty-legs`.
