"""
Module Outils & Automatisation Mac — Inspiré d'Open Interpreter
Donne à JARVIS la capacité d'interagir directement avec macOS.
"""

import os
import subprocess
import urllib.request
import urllib.parse
import json
import re

def notify(title: str, message: str) -> str:
    """Affiche une notification macOS native."""
    script = f'display notification "{message}" with title "{title}" subtitle "JARVIS"'
    subprocess.run(["osascript", "-e", script])
    return f"Notification envoyée : {title} - {message}"

def set_volume(level: int) -> str:
    """Règle le volume système de 0 à 100."""
    lvl = max(0, min(100, int(level)))
    subprocess.run(["osascript", "-e", f"set volume output volume {lvl}"])
    return f"Volume réglé à {lvl}%."

def toggle_dark_mode() -> str:
    """Bascule entre le mode sombre et le mode clair."""
    script = 'tell app "System Events" to tell appearance preferences to set dark mode to not dark mode'
    subprocess.run(["osascript", "-e", script])
    return "Mode d'affichage basculé."

def open_app(name: str) -> str:
    """Lance une application."""
    res = subprocess.run(["open", "-a", name], capture_output=True, text=True)
    if res.returncode == 0:
        return f"{name} a été ouvert."
    return f"Impossible d'ouvrir l'application {name}."

def quit_app(name: str) -> str:
    """Ferme proprement une application via AppleScript."""
    script = f'tell application "{name}" to quit'
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode == 0:
        return f"{name} a été fermé."
    return f"Impossible de fermer {name}."

def get_spotify_track() -> str:
    """Récupère le titre et l'artiste du morceau en cours sur Spotify."""
    script = """
    if application "Spotify" is running then
        try
            tell application "Spotify"
                set trackName to name of current track
                set artistName to artist of current track
                set playerState to player state as string
                return "Piste en cours : " & trackName & " par " & artistName & " (statut: " & playerState & ")"
            end tell
        on error
            return "Spotify est ouvert mais aucune piste n'est en cours de lecture."
        end try
    else
        return "L'application Spotify n'est pas ouverte actuellement."
    end if
    """
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    out = res.stdout.strip()
    return out or "L'application Spotify n'est pas lancée."

def control_spotify(action: str) -> str:
    """Contrôle précis de Spotify (play, pause, next, previous)."""
    action_map = {
        "play": "play",
        "pause": "pause",
        "suivant": "next track",
        "next": "next track",
        "precedent": "previous track",
        "previous": "previous track",
        "toggle": "playpause"
    }
    cmd = action_map.get(action.lower(), "playpause")
    script = f"""
    if application "Spotify" is not running then
        tell application "Spotify" to activate
        delay 0.5
    end if
    tell application "Spotify" to {cmd}
    """
    subprocess.run(["osascript", "-e", script])
    return f"Spotify : commande {action} exécutée."

def compose_email(to: str = "", subject: str = "", body: str = "") -> str:
    """Prépare un nouveau message dans le client mail par défaut (Gmail/Outlook/Apple Mail)."""
    script = f"""
    tell application "Mail"
        activate
        set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
        if "{to}" is not "" then
            tell newMessage to make new to recipient with properties {{address:"{to}"}}
        end if
    end tell
    """
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode == 0:
        return f"Brouillon d'email préparé pour {to or 'destinataire'}."
    # Fallback mailto: URL
    mailto = f"mailto:{urllib.parse.quote(to)}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
    subprocess.run(["open", mailto])
    return f"Client email ouvert avec le brouillon pour {to or 'destinataire'}."

def check_unread_emails() -> str:
    """Vérifie le nombre de courriels non lus dans la boîte de réception."""
    script = """
    tell application "Mail"
        if it is running then
            return unread count of inbox as string
        else
            return "non_lance"
        end if
    end tell
    """
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    val = res.stdout.strip()
    if val == "non_lance":
        return "L'application Mail n'est pas ouverte. Dites 'ouvre Mail' pour synchroniser vos comptes Gmail/Outlook."
    try:
        count = int(val)
        return f"Vous avez {count} message{'s' if count > 1 else ''} non lu{'s' if count > 1 else ''} dans votre boîte de réception."
    except Exception:
        return "Boîte de réception consultée."

def control_media(action: str) -> str:
    """Contrôle la lecture multimédia (Spotify ou Musique)."""
    action = action.lower()
    script = f"""
    if application "Spotify" is running then
        tell application "Spotify" to {action}
    else if application "Music" is running then
        tell application "Music" to {action}
    else
        return "Aucune application de musique active"
    end if
    """
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return res.stdout.strip() or f"Action {action} exécutée."

def get_weather_forecast(city: str = "Paris") -> str:
    """Météo en direct via wttr.in."""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            current = data['current_condition'][0]
            temp = current['temp_C']
            desc = current.get('lang_fr', [{}])[0].get('value') or current['weatherDesc'][0]['value']
            humidity = current['humidity']
            wind = current['windspeedKmph']
            return f"À {city}, il fait actuellement {temp}°C ({desc}), humidité: {humidity}%, vent: {wind} km/h."
    except Exception:
        return f"Impossible de joindre le service météo pour {city} actuellement."

def run_safe_shell(command: str) -> str:
    """Exécute une commande terminal sûre (Inspiré d'Open Interpreter)."""
    # Protection élémentaire contre commandes destructrices
    dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:"]
    if any(d in command for d in dangerous):
        return "COMMANDE REFUSÉE : Détection d'un modèle potentiellement destructeur."

    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.path.expanduser("~")
        )
        out = (res.stdout + res.stderr).strip()
        if len(out) > 1500:
            out = out[:1500] + "\n... [Sortie tronquée]"
        return out or "(Commande exécutée sans sortie)"
    except subprocess.TimeoutExpired:
        return "Erreur : La commande a dépassé le délai imparti (15s)."
    except Exception as e:
        return f"Erreur d'exécution : {str(e)}"
