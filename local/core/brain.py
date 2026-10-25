"""
Module Cerveau & Raisonnement Local — Alimenté par Hermes 3 (Nous Research) & Ollama
Orchestre les requêtes agentiques et l'apprentissage continu en mémoire locale.
"""

import json
import urllib.request
import urllib.error
from . import memory
from . import hardware
from . import tools
from . import learning

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

Faits mémorisés sur {nom} :
{faits}

Consignes :
1. Réponds toujours en français, avec clarté et précision, sans formules superflues.
2. Si la demande nécessite une action système (ex: volume, météo, ouvrir une app, dark mode, lancer une commande), indique clairement l'action.
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
    if any(w in q_low for w in ["batterie", "charge", "autonomie"]):
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
        import re
        digits = re.findall(r'\d+', q_low)
        if digits:
            val = int(digits[0])
            res = tools.set_volume(val)
            return res, "set_volume"

    # Dark Mode
    if "mode sombre" in q_low or "mode clair" in q_low or "dark mode" in q_low:
        res = tools.toggle_dark_mode()
        return res, "toggle_dark_mode"

    # Ouvrir une application
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
