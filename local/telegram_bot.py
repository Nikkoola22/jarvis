#!/usr/bin/env python3
"""
HAL 9000 / JARVIS — Passerelle Telegram Bot Native
Permet de piloter HAL 9000, lire ses vrais e-mails Exchange,
consulter la télémétrie du Mac et recevoir des captures d'écran directement dans Telegram.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import subprocess

# Chargement du dossier jarvis
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import brain
from core import connectors
from core import hardware

CONFIG_PATH = os.path.expanduser("~/.gemini/telegram_config.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_bot_token() -> str:
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env_token:
        return env_token.strip()
    return load_config().get("token", "").strip()

def telegram_api_call(method: str, params: dict = None, timeout: int = 35) -> dict:
    token = get_bot_token()
    if not token:
        return {"ok": False, "description": "Token Telegram manquant"}

    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(params).encode("utf-8") if params else None
    req = urllib.request.Request(url, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
    return telegram_api_call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    })

def send_photo(chat_id: int, photo_path: str, caption: str = "") -> dict:
    token = get_bot_token()
    if not token or not os.path.exists(photo_path):
        return {"ok": False}

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    boundary = "----WebKitFormBoundaryHAL9000"
    
    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{chat_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f"{caption}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="screen.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + photo_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

def handle_incoming_message(msg: dict):
    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    user_name = msg.get("from", {}).get("first_name", "Monsieur")

    if not text or not chat_id:
        return

    # Sauvegarde automatique du chat_id du propriétaire si premier contact
    cfg = load_config()
    owner_id = cfg.get("owner_chat_id")
    if not owner_id:
        cfg["owner_chat_id"] = chat_id
        save_config(cfg)
        owner_id = chat_id

    # Sécurité : Si un ID propriétaire est défini, refuser les messages d'inconnus
    if owner_id and chat_id != owner_id:
        send_message(chat_id, "⛔ Accès refusé. Cet ordinateur HAL 9000 est réservé à Monsieur Nikkoola.")
        return

    text_lower = text.lower()

    # 1. Commande de démarrage / aide
    if text == "/start" or text == "/help":
        welcome = (
            f"🔴 *HAL 9000 connecté et opérationnel.* Bonjour {user_name}.\n\n"
            "Tous mes sous-systèmes fonctionnent à la perfection sur votre MacBook Pro.\n\n"
            "📌 *Commandes rapides :*\n"
            "• `/agenda` : Consulter votre planning et vos prochaines réunions\n"
            "• `/mails` : Consulter vos e-mails pro Exchange en direct\n"
            "• `/loi <terme>` : Rechercher sur l'API officielle Légifrance (CGFP, codes, arrêts)\n"
            "• `/ecran` : Recevoir une capture d'écran live du Mac\n"
            "• `/status` : Télémesure complète (CPU, Batterie, RAM)\n"
            "• `/repondre <nom> <texte>` : Rédiger un e-mail dans Outlook\n\n"
            "Vous pouvez également me poser n'importe quelle question ou me donner des consignes en langage naturel."
        )
        send_message(chat_id, welcome)
        return

    # 2. Consultation Planning & Réunions Exchange
    if text == "/agenda" or text == "/planning" or any(w in text_lower for w in ["planning", "agenda", "calendrier", "reunion", "réunion"]):
        send_message(chat_id, "📅 *Consultation de votre planning Exchange en cours...*")
        res = connectors.get_outlook_calendar()
        send_message(chat_id, res)
        return

    # 3. Consultation Légifrance & Droit Français (API PISTE)
    if text.startswith("/loi") or text.startswith("/legifrance"):
        parts = text.split(" ", 1)
        q = parts[1].strip() if len(parts) > 1 else "Code général de la fonction publique"
        send_message(chat_id, f"⚖️ *Interrogation de l'API officielle Légifrance (DILA) pour : « {q} »...*")
        res = connectors.search_legifrance_droit(q)
        send_message(chat_id, res)
        return

    # 4. Consultation des E-mails Professionnels Exchange
    if text == "/mails" or (any(w in text_lower for w in ["mail", "mails", "exchange"]) or ("outlook" in text_lower and not any(w in text_lower for w in ["planning", "agenda", "calendrier", "reunion", "réunion"]))):
        send_message(chat_id, "⏳ *Consultation de votre boîte professionnelle Exchange en cours...*")
        res = connectors.check_outlook_emails(count=6)
        send_message(chat_id, res)
        return

    # 3. Capture d'écran en direct du MacBook Pro
    if text == "/ecran" or any(w in text_lower for w in ["ecran", "écran", "screenshot", "capture"]):
        send_message(chat_id, "📸 *Capture de l'écran du Mac en cours...*")
        raw_path = "/tmp/tg_screen_raw.png"
        jpg_path = "/tmp/tg_screen.jpg"
        try:
            subprocess.run(["screencapture", "-x", raw_path], check=True)
            subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1440", raw_path, "--out", jpg_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(jpg_path):
                send_photo(chat_id, jpg_path, caption="🖥️ Écran de votre MacBook Pro en direct.")
                return
        except Exception as e:
            send_message(chat_id, f"❌ Erreur lors de la capture d'écran : {str(e)}")
            return

    # 4. Télémétrie Mac
    if text == "/status" or text == "/telemetry":
        t = hardware.get_full_telemetry()
        rep = (
            f"📊 *Télémétrie MacBook Pro :*\n\n"
            f"• *Modèle* : `{t.get('modele', 'MacBook Pro')}`\n"
            f"• *CPU* : `{t.get('cpu', 'Inconnu')}`\n"
            f"• *Batterie* : `{t.get('batterie', 'Inconnu')}`\n"
            f"• *Mémoire* : `{t.get('memoire', 'Inconnu')}`\n"
            f"• *Disque* : `{t.get('disque', 'Inconnu')}`\n"
        )
        send_message(chat_id, rep)
        return

    # 5. Traitement général par le Cerveau HAL 9000
    try:
        reply, action = brain.ask(text)
        send_message(chat_id, f"« {reply} »")
    except Exception as e:
        send_message(chat_id, f"Erreur de traitement : {str(e)}")

def run_polling():
    token = get_bot_token()
    if not token:
        print("\n❌ Aucun token Telegram trouvé.")
        print("Configurez votre token avec : python3 telegram_bot.py --setup")
        sys.exit(1)

    print("\n" + "="*50)
    print("🔴 HAL 9000 — Passerelle Telegram Bot ACTIVE")
    print(f"Token : {token[:8]}...{token[-4:]}")
    print("En attente de messages Telegram... (Appuyez sur Ctrl+C pour arrêter)")
    print("="*50 + "\n")

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            updates = telegram_api_call("getUpdates", params, timeout=35)
            if updates.get("ok"):
                for item in updates.get("result", []):
                    offset = item.get("update_id", 0) + 1
                    msg = item.get("message")
                    if msg:
                        handle_incoming_message(msg)
            else:
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nArrêt de la passerelle Telegram.")
            break
        except Exception as e:
            time.sleep(3)

def setup_cli():
    print("\n--- Configuration du Bot Telegram pour HAL 9000 ---")
    print("1. Ouvrez Telegram et cherchez @BotFather")
    print("2. Envoyez la commande /newbot et suivez les instructions")
    print("3. Collez ici le token HTTP API fourni par BotFather :\n")
    tok = input("Token Telegram Bot : ").strip()
    if tok and ":" in tok:
        cfg = load_config()
        cfg["token"] = tok
        save_config(cfg)
        print("✅ Token enregistré avec succès dans ~/.gemini/telegram_config.json")
        print("Lancement du bot...")
        run_polling()
    else:
        print("❌ Format de token invalide.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--setup", "setup", "-s"]:
        setup_cli()
    else:
        run_polling()
