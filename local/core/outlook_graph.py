#!/usr/bin/env python3
"""
JARVIS Microsoft Graph & Outlook 365 Connector
Gère l'interfaçage avec Office 365 Pro via l'API officielle Microsoft Graph.
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta

CONFIG_PATH = os.path.expanduser("~/.gemini/outlook_config.json")
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def load_config() -> dict:
    """Charge la configuration et le jeton OAuth depuis le fichier local."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg: dict) -> None:
    """Enregistre la configuration dans ~/.gemini/outlook_config.json."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_access_token() -> str:
    """Récupère le jeton d'accès actuel (ou depuis variable d'environnement)."""
    env_token = os.environ.get("OUTLOOK_ACCESS_TOKEN") or os.environ.get("MS_GRAPH_TOKEN")
    if env_token:
        return env_token.strip()
    cfg = load_config()
    return cfg.get("access_token", "").strip()

def is_configured() -> bool:
    """Indique si un jeton Microsoft Graph valide est configuré."""
    token = get_access_token()
    return bool(token and len(token) > 20)

def set_access_token(token: str, client_id: str = "", tenant_id: str = "") -> dict:
    """Enregistre un nouveau jeton d'accès Microsoft Graph."""
    cfg = load_config()
    cfg["access_token"] = token.strip()
    if client_id: cfg["client_id"] = client_id.strip()
    if tenant_id: cfg["tenant_id"] = tenant_id.strip()
    cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_config(cfg)
    return {"status": "ok", "message": "Jeton Microsoft Graph sauvegardé avec succès."}

def _graph_request(endpoint: str, method: str = "GET", data: dict = None) -> tuple:
    """Effectue une requête authentifiée vers l'API Microsoft Graph."""
    token = get_access_token()
    if not token:
        return None, "Aucun jeton Microsoft Graph configuré. Renseignez votre jeton dans les paramètres."

    url = f"{GRAPH_BASE}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}, None
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_msg)
            message = parsed.get("error", {}).get("message", err_msg)
        except Exception:
            message = err_msg
        return None, f"Erreur Microsoft Graph (HTTP {e.code}) : {message}"
    except Exception as e:
        return None, f"Erreur de connexion Microsoft Graph : {str(e)}"

def get_unread_emails(count: int = 5) -> str:
    """Récupère et résume les e-mails non lus de la boîte de réception Office 365."""
    if not is_configured():
        return (
            "💡 Le connecteur Microsoft Graph n'est pas encore authentifié.\n"
            "Pour connecter votre compte Pro Office 365, ajoutez votre jeton Graph dans les paramètres "
            "ou configurez votre compte dans Réglages Système > Comptes Internet > Exchange sur votre Mac."
        )

    endpoint = f"me/mailFolders/inbox/messages?$filter=isRead eq false&$top={count}&$select=subject,from,receivedDateTime,bodyPreview"
    res, err = _graph_request(endpoint)
    if err:
        return err

    messages = res.get("value", [])
    if not messages:
        return "Vous n'avez aucun message non lu dans votre boîte de réception Outlook pro, monsieur."

    output = [f"Vous avez {len(messages)} message{'s' if len(messages) > 1 else ''} non lu{'s' if len(messages) > 1 else ''} :"]
    for i, m in enumerate(messages, 1):
        subj = m.get("subject", "(Sans objet)")
        sender = m.get("from", {}).get("emailAddress", {}).get("name") or m.get("from", {}).get("emailAddress", {}).get("address", "Inconnu")
        preview = (m.get("bodyPreview") or "").strip()[:90]
        output.append(f"{i}. De {sender} : « {subj} »\n   {preview}...")

    return "\n\n".join(output)

def get_recent_emails(count: int = 5) -> str:
    """Récupère les derniers e-mails reçus (lus ou non)."""
    if not is_configured():
        return "Connecteur Microsoft Graph non authentifié."

    endpoint = f"me/mailFolders/inbox/messages?$top={count}&$select=subject,from,receivedDateTime,bodyPreview,isRead"
    res, err = _graph_request(endpoint)
    if err:
        return err

    messages = res.get("value", [])
    if not messages:
        return "Votre boîte de réception est vide."

    output = [f"Voici les {len(messages)} derniers e-mails de votre compte pro :"]
    for i, m in enumerate(messages, 1):
        subj = m.get("subject", "(Sans objet)")
        sender = m.get("from", {}).get("emailAddress", {}).get("name") or m.get("from", {}).get("emailAddress", {}).get("address", "Inconnu")
        status = "🔴 Non lu" if not m.get("isRead") else "✓ Lu"
        output.append(f"{i}. [{status}] {sender} : « {subj} »")

    return "\n".join(output)

def send_email(to_address: str, subject: str, body: str) -> str:
    """Envoie directement un e-mail via l'API Microsoft Graph."""
    if not is_configured():
        return "Impossible d'envoyer l'e-mail : jeton Microsoft Graph absent."

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_address
                    }
                }
            ]
        },
        "saveToSentItems": "true"
    }

    res, err = _graph_request("me/sendMail", method="POST", data=payload)
    if err:
        return err
    return f"E-mail envoyé avec succès à {to_address} avec pour objet « {subject} »."

def get_calendar_today() -> str:
    """Récupère l'agenda et les réunions de la journée depuis Outlook Calendar."""
    if not is_configured():
        return "Connecteur Microsoft Graph non authentifié pour le calendrier."

    now = datetime.now(timezone.utc)
    start_str = now.strftime("%Y-%m-%dT00:00:00Z")
    end_str = (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    endpoint = f"me/calendarview?startDateTime={start_str}&endDateTime={end_str}&$top=10&$select=subject,start,end,location,isAllDay"
    res, err = _graph_request(endpoint)
    if err:
        return err

    events = res.get("value", [])
    if not events:
        return "Aucune réunion programmée dans votre calendrier Outlook aujourd'hui, monsieur."

    output = [f"Vous avez {len(events)} événement{'s' if len(events) > 1 else ''} prévu{'s' if len(events) > 1 else ''} aujourd'hui :"]
    for i, ev in enumerate(events, 1):
        subj = ev.get("subject", "Réunion")
        start_time = ev.get("start", {}).get("dateTime", "")[:16].replace("T", " ")
        loc = ev.get("location", {}).get("displayName") or "En ligne / Teams"
        output.append(f"{i}. « {subj} » à {start_time} ({loc})")

    return "\n".join(output)
