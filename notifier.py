"""Notification des abonnes quand un empty leg matche.

Trois implementations pluggables derriere une interface commune Notifier :
- ConsoleNotifier : affiche dans le terminal (defaut, zero config, pour tester).
- EmailNotifier   : SMTP, parametres lus dans des variables d'environnement.
- TelegramNotifier: envoi via un bot, token lu dans une variable d'environnement.

Les secrets (SMTP, token bot) ne sont JAMAIS en dur : uniquement via os.environ.
"""

import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

CTA = "👉 Demander a Dynami pour bloquer ce vol."


def _leg_get(leg, key):
    if key == "date":
        return leg.get("date") or leg.get("flight_date")
    return leg.get(key)


def format_leg_message(leg, price_on_request=False):
    """Message clair et lisible : route, date, appareil, sieges, prix + CTA Dynami."""
    route = _leg_get(leg, "route") or \
        f"{_leg_get(leg, 'origin')}-{_leg_get(leg, 'destination')}"
    date = _leg_get(leg, "date") or "date a confirmer"
    aircraft = _leg_get(leg, "aircraft") or "appareil n.c."
    seats = _leg_get(leg, "seats")
    seats_txt = f"{seats} sieges" if seats is not None else "sieges n.c."

    price = _leg_get(leg, "price")
    if price is None or price_on_request:
        price_txt = "prix sur demande"
    else:
        cur = _leg_get(leg, "currency") or "EUR"
        price_txt = f"{int(price) if float(price).is_integer() else price} {cur}"

    lines = [
        f"✈️  Empty leg : {route}",
        f"📅  {date}",
        f"🛩️  {aircraft} — {seats_txt}",
        f"💶  {price_txt}",
        "",
        CTA,
    ]
    return "\n".join(lines)


def format_subject(leg):
    route = _leg_get(leg, "route") or \
        f"{_leg_get(leg, 'origin')}-{_leg_get(leg, 'destination')}"
    date = _leg_get(leg, "date") or ""
    return f"[Empty Leg] {route} {date}".strip()


class Notifier:
    """Interface. Implementer notify(subscriber, leg, price_on_request=False) -> bool."""

    def notify(self, subscriber, leg, price_on_request=False):
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """Affiche la notification dans le terminal. Garde une trace dans self.sent (tests)."""

    def __init__(self, stream=None):
        self.stream = stream
        self.sent = []

    def notify(self, subscriber, leg, price_on_request=False):
        body = format_leg_message(leg, price_on_request)
        name = subscriber.get("name") if isinstance(subscriber, dict) else subscriber
        msg = f"--- Notification -> {name} ---\n{body}\n"
        self.sent.append({"subscriber": subscriber, "leg": leg, "body": body})
        if self.stream is not None:
            self.stream.write(msg + "\n")
        else:
            print(msg)
        return True


class EmailNotifier(Notifier):
    """Envoi SMTP. Config via variables d'environnement :
       SMTP_HOST, SMTP_PORT (defaut 587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM."""

    def __init__(self):
        self.host = os.environ.get("SMTP_HOST")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER")
        self.password = os.environ.get("SMTP_PASSWORD")
        self.sender = os.environ.get("SMTP_FROM", self.user)

    def notify(self, subscriber, leg, price_on_request=False):
        if not self.host:
            raise RuntimeError("SMTP_HOST non configure (variables d'environnement).")
        to = subscriber.get("contact") if isinstance(subscriber, dict) else subscriber
        if not to:
            raise RuntimeError("Abonne sans contact email.")
        em = EmailMessage()
        em["Subject"] = format_subject(leg)
        em["From"] = self.sender
        em["To"] = to
        em.set_content(format_leg_message(leg, price_on_request))
        with smtplib.SMTP(self.host, self.port) as s:
            s.starttls()
            if self.user:
                s.login(self.user, self.password)
            s.send_message(em)
        return True


class TelegramNotifier(Notifier):
    """Envoi via l'API Bot Telegram. Token via env TELEGRAM_BOT_TOKEN.
       Le contact de l'abonne est le chat_id (numerique) du destinataire."""

    API = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token=None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")

    def notify(self, subscriber, leg, price_on_request=False):
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN non configure.")
        chat_id = subscriber.get("contact") if isinstance(subscriber, dict) else subscriber
        if not chat_id:
            raise RuntimeError("Abonne sans chat_id Telegram.")
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": format_leg_message(leg, price_on_request),
        }).encode()
        url = self.API.format(token=self.token)
        with urllib.request.urlopen(urllib.request.Request(url, data=data)) as resp:
            return resp.status == 200


# Fabrique : map canal -> notifier (le canal est stocke sur l'abonne).
def notifier_for(channel):
    """Renvoie une instance de Notifier selon le canal de l'abonne."""
    if channel == "email":
        return EmailNotifier()
    if channel == "telegram":
        return TelegramNotifier()
    return ConsoleNotifier()


def notify_match(conn, subscriber, leg, match_id=None, notifier=None,
                 price_on_request=False):
    """Notifie un abonne pour un leg et marque le match comme notifie en base.

    notifier : instance forcee (sinon choisie selon subscriber['channel']).
    Renvoie True si l'envoi a reussi."""
    channel = subscriber.get("channel", "console") if isinstance(subscriber, dict) else "console"
    notifier = notifier or notifier_for(channel)
    ok = notifier.notify(subscriber, leg, price_on_request)
    if ok and match_id is not None:
        from db import mark_notified
        mark_notified(conn, match_id)
    return ok
