"""
Module Cerveau & Raisonnement Local — Alimenté par Hermes 3 (Nous Research) & Ollama
Orchestre les requêtes agentiques et l'apprentissage continu en mémoire locale.
"""

import json
import re
import urllib.request
import urllib.error
from . import memory
from . import hardware
from . import tools
from . import learning
from . import connectors

OLLAMA_API = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "hermes3"
ACTIVE_MODEL = "hermes3"

def get_active_model() -> str:
    return ACTIVE_MODEL

def set_active_model(name: str) -> str:
    global ACTIVE_MODEL
    ACTIVE_MODEL = name
    return ACTIVE_MODEL

SYSTEM_PROMPT_TEMPLATE = """Tu es JARVIS, l'assistant personnel d'élite de {nom}, exécuté localement sur son Mac ({modele}).
Personnalité : Courtois, concis, hautement compétent, inspiré du Jarvis d'Iron Man.

Connaissances actuelles de la machine :
- CPU: {cpu}
- GPU: {gpu}
- Batterie: {batterie}
- Mémoire: {memoire}

Connecteurs Mac natifs intégrés :
- Notes (prise de notes, recherche)
- Rappels (ajout et consultation de tâches)
- Calendrier (agenda)
- Communication (Messages iMessage, WhatsApp)
- Suite Microsoft (Word, Excel, Outlook)
- Multimédia (Spotify, IINA, VLC)
- Web (Safari, Tor Browser)
- Téléchargements (Transmission)
- Système (AlDente batterie, capture d'écran, corbeille, verrouillage, Finder)

Faits mémorisés sur {nom} :
{faits}

Consignes :
1. Réponds toujours en français, avec clarté et précision, sans formules superflues.
2. Si la demande nécessite une action système ou logicielle, confirme avec élégance.
3. Sois rapide et percutant.
"""

def build_system_prompt() -> str:
    facts = memory.get_all_facts()
    nom = facts.get("nom_utilisateur", "Monsieur")
    telemetry = hardware.get_full_telemetry()
    
    facts_str = "\n".join([f"- {k}: {v}" for k, v in facts.items()])

    # Intégration des compétences apprises (Hermes Learning Loop)
    skills = learning.get_learned_skills()
    skills_str = "\n".join([f"- Déclencheur '{s[0]}': {s[1]}" for s in skills]) if skills else "Aucune compétence spécifique enregistrée."

    base_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        nom=nom,
        modele=telemetry["modele"],
        cpu=telemetry["cpu"],
        gpu=telemetry["gpu"],
        batterie=telemetry["batterie"],
        memoire=telemetry["memoire"],
        faits=facts_str
    )

    return f"{base_prompt}\n\nCompétences apprises via Hermes Agent Loop :\n{skills_str}"

def ask(query: str, history: list = None) -> tuple[str, str | None]:
    """
    Envoie la question au LLM local (Ollama).
    Retourne (réponse_texte, action_exécutée_ou_None).
    """
    if history is None:
        history = []

    # 1. Vérification d'intentions directes rapides (0ms latence)
    q_low = query.lower().strip()

    # Météo
    if any(w in q_low for w in ["météo", "quel temps", "temperature"]):
        city = "Paris"
        words = q_low.split()
        if "à" in words:
            idx = words.index("à")
            if idx + 1 < len(words):
                city = words[idx + 1].strip("?.!")
        res = tools.get_weather_forecast(city)
        return res, "get_weather"

    # Batterie / Santé
    if re.search(r'\b(batterie|autonomie|niveau de charge)\b', q_low):
        b = hardware.get_battery_info()
        return f"Votre batterie est actuellement à {b['percent']}%, connectée au {b['state']}. Temps estimé : {b['time_remaining']}.", "battery_check"

    # Télémétrie complète
    if any(w in q_low for w in ["télémétrie", "diag", "diagnostic", "statut système", "ressources"]):
        t = hardware.get_full_telemetry()
        res = (
            f"Rapport système : {t['cpu']}, GPU : {t['gpu']}. "
            f"Mémoire : {t['memoire']}. Batterie : {t['batterie']}."
        )
        return res, "telemetry"

    # Volume
    if "volume" in q_low:
        digits = re.findall(r'\d+', q_low)
        if digits:
            val = int(digits[0])
            res = tools.set_volume(val)
            return res, "set_volume"

    # Dark Mode
    if "mode sombre" in q_low or "mode clair" in q_low or "dark mode" in q_low:
        res = tools.toggle_dark_mode()
        return res, "toggle_dark_mode"

    # Ouvrir un dossier Finder ou une application
    if any(q_low.startswith(p) for p in ["ouvre le dossier ", "ouvre dossier "]):
        folder = query.split("dossier", 1)[1].strip()
        return connectors.open_folder(folder), "open_folder"

    if q_low.startswith("ouvre ") or q_low.startswith("lance "):
        target = query[6:].strip()
        res = tools.open_app(target)
        return res, "open_app"

    # Musique & Spotify
    if any(w in q_low for w in ["spotify", "musique", "chanson", "morceau"]):
        if any(w in q_low for w in ["quel", "quelle", "titre", "qui chante", "quoi"]):
            return tools.get_spotify_track(), "spotify_track_info"
        if "pause" in q_low or "stop" in q_low:
            return tools.control_spotify("pause"), "spotify_pause"
        if any(w in q_low for w in ["suivant", "next", "passer"]):
            return tools.control_spotify("next"), "spotify_next"
        if any(w in q_low for w in ["precedent", "précédent", "previous"]):
            return tools.control_spotify("previous"), "spotify_previous"
        if any(w in q_low for w in ["play", "lance", "mets", "reprends", "joue"]):
            return tools.control_spotify("play"), "spotify_play"

    # Emails (Gmail, Outlook, Mail)
    if any(w in q_low for w in ["email", "emails", "mail", "mails", "courriel", "gmail", "outlook"]):
        if any(w in q_low for w in ["non lu", "combien", "reçu", "nouveau", "nouveaux", "verifie", "vérifie"]):
            return tools.check_unread_emails(), "check_emails"
        if any(w in q_low for w in ["ecris", "écris", "envoie", "redige", "rédige", "brouillon"]):
            to_addr = ""
            if "à " in q_low or "a " in q_low:
                parts = query.split("à " if "à " in query else "a ", 1)
                if len(parts) > 1:
                    to_addr = parts[1].split()[0].strip()
            return tools.compose_email(to=to_addr, subject="Message de Nikkoola", body="Bonjour,\n\n"), "compose_email"

    # Statut MCP
    if "mcp" in q_low:
        from . import mcp_manager
        servers = mcp_manager.list_mcp_servers()
        server_names = ", ".join([s["name"].capitalize() for s in servers])
        return f"Serveurs MCP configurés pour JARVIS : {server_names}. Vous pouvez renseigner vos identifiants dans ~/jarvis/config_mcp.json.", "mcp_status"

    # --- CONNECTEURS APPLICATIONS MAC ---
    # Apple Notes
    if any(w in q_low for w in ["note que", "prends note", "ajoute une note", "crée une note", "nouvelle note"]):
        content = query
        for trigger in ["note que", "prends note que", "prends note", "ajoute une note", "crée une note", "nouvelle note"]:
            if trigger in q_low:
                content = query[q_low.index(trigger) + len(trigger):].strip(" :,-")
                break
        res = connectors.create_note(title=content[:30] or "Note JARVIS", content=content)
        return res, "create_note"

    if any(w in q_low for w in ["mes notes", "lire mes notes", "dernières notes", "liste des notes"]):
        return connectors.list_recent_notes(), "list_notes"

    # Apple Rappels (Reminders)
    if any(w in q_low for w in ["rappelle-moi de", "rappelle moi de", "ajoute un rappel", "crée un rappel", "nouveau rappel"]):
        title = query
        for trigger in ["rappelle-moi de", "rappelle moi de", "ajoute un rappel pour", "ajoute un rappel de", "crée un rappel pour"]:
            if trigger in q_low:
                title = query[q_low.index(trigger) + len(trigger):].strip(" :,-")
                break
        return connectors.add_reminder(title), "add_reminder"

    if any(w in q_low for w in ["mes rappels", "liste des rappels", "quels sont mes rappels"]):
        return connectors.list_reminders(), "list_reminders"

    # Calendrier, Planning & Réunions
    if any(w in q_low for w in ["planning", "agenda", "calendrier", "reunion", "réunion", "rendez-vous", "rdv"]):
        if any(w in q_low for w in ["ouvre", "lance", "affiche l'app", "application"]):
            return connectors.open_calendar_and_view(), "calendar"
        return connectors.get_outlook_calendar(), "outlook_calendar"

    # WhatsApp
    if "whatsapp" in q_low:
        msg = ""
        target = ""
        if "à " in q_low or "a " in q_low:
            parts = query.split("à " if "à " in query else "a ", 1)
            if len(parts) > 1:
                target = parts[1].split()[0].strip()
        if "disant " in q_low:
            msg = query.split("disant ", 1)[1].strip()
        return connectors.open_whatsapp_chat(target, msg), "whatsapp"

    # iMessage / Messages
    if any(w in q_low for w in ["imessage", "envoie un message", "envoie un sms"]):
        target = ""
        msg = ""
        if "à " in q_low or "a " in q_low:
            parts = query.split("à " if "à " in query else "a ", 1)
            if len(parts) > 1:
                target = parts[1].split()[0].strip()
        if "disant " in q_low:
            msg = query.split("disant ", 1)[1].strip()
        return connectors.send_imessage(target or "contact", msg or "Bonjour de la part de Nikkoola"), "imessage"

    # Microsoft Word / Excel / Outlook
    if "word" in q_low and any(w in q_low for w in ["document", "nouveau", "crée", "ouvre"]):
        return connectors.create_word_document(), "word_new_doc"

    if "excel" in q_low and any(w in q_low for w in ["feuille", "classeur", "nouveau", "crée", "ouvre"]):
        return connectors.create_excel_spreadsheet(), "excel_new_sheet"

    # Réponses contextuelles emails Pro réels
    if any(w in q_low for w in ["dakhlia", "ramy", "éléments variables", "elements variables", "paie"]):
        return connectors.compose_outlook_email(
            to="Ramy.DAKHLIA@ville-gennevilliers.fr",
            subject="Re: DEMANDE D'ELEMENTS VARIABLES DE SEPTEMBRE PAIE D'OCTOBRE 2026",
            body="Bonjour Ramy,\n\nJe te transmets les éléments variables validés pour le traitement de la paie.\n\nBien cordialement,\nNikkoola"
        ), "outlook_reply_dakhlia"

    if any(w in q_low for w in ["baroukh", "léa", "lea", "dates de congés", "conges de fin"]):
        return connectors.compose_outlook_email(
            to="Lea.BAROUKH@ville-gennevilliers.fr",
            subject="RE: dates de congés de fin d'année",
            body="Bonjour Léa,\n\nConcernant les congés de fin d'année, les dates prévues sont bien enregistrées.\n\nBien à toi,\nNikkoola"
        ), "outlook_reply_baroukh"

    if any(w in q_low for w in ["costa", "laura", "carte vitale", "lecteur"]):
        return connectors.compose_outlook_email(
            to="Laura.COSTA@ville-gennevilliers.fr",
            subject="RE: Problème lecteur carte vitale",
            body="Bonjour Laura,\n\nLe problème de lecteur de carte vitale a été signalé et des tests sont en cours avec la DSI.\n\nBien cordialement,\nNikkoola"
        ), "outlook_reply_costa"

    if any(w in q_low for w in ["prudhomme", "muriel"]):
        return connectors.compose_outlook_email(
            to="muriel.prudhomme@ville-gennevilliers.fr",
            subject="RE: Point d'information",
            body="Bonjour Muriel,\n\nJ'ai bien reçu votre message et je reviens vers vous rapidement.\n\nBien cordialement,\nNikkoola"
        ), "outlook_reply_prudhomme"

    if any(w in q_low for w in ["outlook", "mail pro", "mails pro", "compte pro", "boite pro", "boîte pro", "exchange"]):
        if any(w in q_low for w in ["agenda", "calendrier", "reunion", "réunion", "planning"]):
            return connectors.get_outlook_calendar(), "outlook_calendar"
        if any(w in q_low for w in ["lis", "lit", "lire", "consulte", "check", "verifie", "vérifie", "voir", "affiche", "reçu", "non lu", "derniers", "nouveau", "nouveaux", "combien", "boite", "boîte", "reception", "réception", "mail", "mails"]):
            return connectors.check_outlook_emails(), "outlook_check_emails"
        if any(w in q_low for w in ["écris", "ecris", "envoie", "nouveau", "brouillon", "prepare", "prépare", "redige", "rédige"]):
            to_addr = ""
            sub = "Message de Nikkoola"
            msg_body = "Bonjour,\n\n"
            if "à " in query or "a " in query or "pour " in query:
                sep = "à " if "à " in query else ("pour " if "pour " in query else "a ")
                parts = query.split(sep, 1)
                if len(parts) > 1:
                    to_addr = parts[1].split()[0].strip().rstrip(",.")
            if "objet " in q_low or "sujet " in q_low:
                sub_sep = "objet " if "objet " in q_low else "sujet "
                sub_part = query.lower().split(sub_sep, 1)[1]
                sub = sub_part.split(" avec ")[0].split(" et ")[0].strip().capitalize()
            return connectors.compose_outlook_email(to=to_addr, subject=sub, body=msg_body), "outlook_compose"
        return tools.open_app("Microsoft Outlook"), "open_outlook"

    # Recherche Légifrance & Droit Français (API PISTE / DILA)
    if any(w in q_low for w in ["legifrance", "légifrance", "jurisprudence", "conseil d'état", "conseil d'etat", "cour de cassation"]) or \
       (any(w in q_low for w in ["article", "art.", "loi", "code", "décret", "statut", "cgfp", "cgct", "rifseep", "citis"]) and \
        any(w in q_low for w in ["cherche", "recherche", "consulte", "trouve", "que dit", "texte", "base", "légal", "juridique", "droit"])):
        search_query = query
        for trig in ["cherche sur légifrance", "cherche sur legifrance", "recherche sur légifrance", "recherche sur legifrance", "légifrance", "legifrance"]:
            if trig in q_low:
                search_query = query[q_low.index(trig) + len(trig):].strip(" :,-")
                break
        if not search_query.strip():
            search_query = query
        return connectors.search_legifrance_droit(search_query), "legifrance_search"

    # iTerm2 & Terminal
    if "iterm" in q_low or "iterm2" in q_low:
        cmd = ""
        for sep in ["lance ", "exécute ", "exec ", "run ", "avec "]:
            if sep in q_low:
                cmd = query.split(sep, 1)[1].strip()
                break
        if "agy" in q_low and not cmd:
            cmd = "agy"
        return connectors.open_in_iterm(cmd), "iterm_open"

    # IINA & VLC
    if "iina" in q_low:
        return connectors.open_in_iina("~/Downloads"), "iina_open"

    if "vlc" in q_low:
        action = "play"
        if "pause" in q_low or "stop" in q_low: action = "pause"
        elif "suivant" in q_low or "next" in q_low: action = "next"
        elif "plein écran" in q_low: action = "fullscreen"
        return connectors.control_vlc(action), "vlc_control"

    # Safari & Tor Browser
    if "tor browser" in q_low or "tor" in q_low:
        return connectors.open_tor_browser(), "tor_browser"

    if "safari" in q_low or "cherche sur le web" in q_low or "recherche sur google" in q_low:
        if "onglet" in q_low or "page" in q_low and "actuel" in q_low:
            return connectors.safari_get_active_tab(), "safari_active_tab"
        term = query
        for trigger in ["cherche sur le web", "recherche sur le web", "cherche sur google", "recherche sur safari", "cherche sur safari"]:
            if trigger in q_low:
                term = query[q_low.index(trigger) + len(trigger):].strip(" :,-")
                break
        return connectors.safari_search(term), "safari_search"

    # Transmission (Torrents)
    if "transmission" in q_low or "torrent" in q_low:
        if "pause" in q_low or "stop" in q_low:
            return connectors.transmission_toggle_all("pause"), "transmission_pause"
        if "start" in q_low or "reprends" in q_low or "lance" in q_low:
            return connectors.transmission_toggle_all("start"), "transmission_start"
        return tools.open_app("Transmission"), "open_transmission"

    # AlDente (Batterie)
    if "aldente" in q_low:
        return connectors.open_aldente(), "open_aldente"

    # Finder & Système
    if any(w in q_low for w in ["corbeille", "vide la corbeille"]):
        return connectors.empty_trash(), "empty_trash"

    if any(w in q_low for w in ["capture d'écran", "capture d ecran", "screenshot", "screen"]):
        return connectors.take_screenshot(), "take_screenshot"

    if any(w in q_low for w in ["verrouille", "bloque l'écran", "met en veille l'écran"]):
        return connectors.lock_screen(), "lock_screen"

    if "ouvre le dossier" in q_low or "ouvre mes" in q_low:
        for folder in ["téléchargements", "downloads", "bureau", "desktop", "documents", "applications"]:
            if folder in q_low:
                return connectors.open_folder(folder), "open_folder"

    # Musique générique fallback
    if any(w in q_low for w in ["pause", "reprends la musique", "morceau suivant", "chanson suivante"]):
        if "pause" in q_low:
            res = tools.control_media("playpause")
        elif "suivant" in q_low:
            res = tools.control_media("next track")
        else:
            res = tools.control_media("playpause")
        return res, "control_media"

    # Bascule de Modèle (Llama ⇄ Hermes 3)
    if any(w in q_low for w in ["mode hermes", "bascule sur hermes", "active hermes", "passe sur hermes"]):
        set_active_model("hermes3")
        return "Cerveau basculé avec succès sur le modèle Hermes 3 (Nous Research). Prêt pour le raisonnement d'agent avancé.", "switch_model_hermes"

    if any(w in q_low for w in ["mode llama", "bascule sur llama", "active llama", "passe sur llama"]):
        set_active_model("llama3.2:3b")
        return "Cerveau basculé sur Meta Llama 3.2 (3B). Fluidité et vitesse maximales activées.", "switch_model_llama"

    # Hermes Agent Learning Loop
    if q_low.startswith("apprends que quand je dis") or q_low.startswith("apprends la compétence"):
        # Format : "apprends que quand je dis X, fais Y"
        if "fais " in q_low:
            parts = query.split("fais ", 1)
            trigger = parts[0].replace("apprends que quand je dis", "").replace("apprends que", "").strip(" '\",")
            instruction = parts[1].strip()
            res = learning.learn_skill(trigger, instruction)
            return f"Compétence Hermes enregistrée : lorsque vous direz '{trigger}', j'exécuterai : {instruction}", "learn_skill"

    # Mémoriser une information
    if q_low.startswith("rappelle-toi que") or q_low.startswith("mémorise que") or q_low.startswith("souviens-toi que"):
        info = query.split("que", 1)[1].strip()
        key = f"note_{len(memory.get_all_facts()) + 1}"
        res = memory.remember_fact(key, info, "utilisateur")
        return f"C'est noté, monsieur. J'ai enregistré : {info}", "remember_fact"

    # 2. Sinon, sollicitation complète de Llama 3.2 via Ollama
    system_prompt = build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": query}]

    payload = {
        "model": ACTIVE_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.3 if "hermes" in ACTIVE_MODEL else 0.5,
            "num_predict": 250
        }
    }

    try:
        req = urllib.request.Request(
            OLLAMA_API,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode('utf-8'))
            reply = data.get("message", {}).get("content", "").strip()
            return reply, "ollama_reasoning"
    except urllib.error.URLError:
        return "Le serveur Ollama n'est pas joignable sur le port 11434. Lancez 'ollama serve' en arrière-plan.", None
    except Exception as e:
        return f"Erreur de traitement : {str(e)}", None
