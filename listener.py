"""
Ecouteur Telegram : se connecte avec TON compte (API officielle, via Telethon),
lit les messages des groupes empty legs, les parse et les range en base.

Lancement :
    1) cree config.py depuis config.example.py (api_id, api_hash, groupes)
    2) pip install -r requirements.txt
    3) python listener.py
       -> au 1er lancement : saisis ton numero + le code recu sur Telegram (une seule fois)
       -> ensuite ca tourne tout seul, 24/7

Optionnel : pour une extraction haute qualite, mets USE_CLAUDE = True dans config.py
(necessite anthropic + ANTHROPIC_API_KEY).
"""

import asyncio
from telethon import TelegramClient, events

import config
from db import connect, store_leg, leg_by_hash, get_subscriber
from parser import parse_message, parse_with_claude

conn = connect(getattr(config, "DB_PATH", "empty_legs.db"))
client = TelegramClient(getattr(config, "SESSION", "empty_legs"), config.API_ID, config.API_HASH)

MATCHING_ENABLED = getattr(config, "MATCHING_ENABLED", False)
if MATCHING_ENABLED:
    # imports paresseux : le mode "ecouteur seul" ne depend pas de ces modules
    from matcher import match_leg
    from notifier import notify_match


def _extract(text):
    if getattr(config, "USE_CLAUDE", False):
        try:
            return parse_with_claude(text)
        except Exception as e:
            print(f"[claude KO -> heuristique] {e}")
    return parse_message(text)


def _match_and_notify(rec):
    """Cherche les abonnes concernes par le leg fraichement stocke et les notifie.
    Tolerant aux pannes : une erreur de notif ne doit pas tuer l'ecouteur."""
    leg = leg_by_hash(conn, rec)
    if not leg:
        return
    for sub_id in match_leg(conn, leg, leg_id=leg["id"]):
        row = conn.execute(
            "SELECT id FROM matches WHERE leg_id=? AND subscriber_id=? AND notified=0",
            (leg["id"], sub_id)).fetchone()
        if not row:
            continue  # deja notifie
        sub = get_subscriber(conn, sub_id)
        try:
            notify_match(conn, sub, leg, match_id=row[0])
            print(f"   ↳ alerte envoyee a {sub['name']} ({sub['channel']})")
        except Exception as e:
            print(f"   ↳ [notif KO] {sub.get('name')}: {e}")


@client.on(events.NewMessage(chats=config.GROUPS))
async def handler(event):
    text = event.message.message or ""
    if not text.strip():
        return
    rec = _extract(text)
    src = f"telegram:{getattr(event.chat, 'title', event.chat_id)}"
    if store_leg(conn, rec, source=src):
        print(f"✅ EMPTY LEG  {rec['route']}  {rec.get('date')}  "
              f"{rec.get('aircraft')}  {rec.get('seats')}pax  "
              f"{rec.get('price')}{rec.get('currency') or ''}  (conf {rec['confidence']})")
        if MATCHING_ENABLED:
            _match_and_notify(rec)
    # sinon : doublon, message sans route, ou bruit -> ignore en silence


async def main():
    await client.start()
    me = await client.get_me()
    print(f"Connecte en tant que {me.first_name}. Ecoute de {len(config.GROUPS)} groupe(s)... (Ctrl+C pour arreter)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
