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
from db import connect, store_leg
from parser import parse_message, parse_with_claude

conn = connect(getattr(config, "DB_PATH", "empty_legs.db"))
client = TelegramClient(getattr(config, "SESSION", "empty_legs"), config.API_ID, config.API_HASH)


def _extract(text):
    if getattr(config, "USE_CLAUDE", False):
        try:
            return parse_with_claude(text)
        except Exception as e:
            print(f"[claude KO -> heuristique] {e}")
    return parse_message(text)


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
    # sinon : doublon, message sans route, ou bruit -> ignore en silence


async def main():
    await client.start()
    me = await client.get_me()
    print(f"Connecte en tant que {me.first_name}. Ecoute de {len(config.GROUPS)} groupe(s)... (Ctrl+C pour arreter)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
