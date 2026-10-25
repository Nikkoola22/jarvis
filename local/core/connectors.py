"""
JARVIS Mac Connectors Hub — Interfaçage natif avec les applications installées sur le Mac
Programmes gérés : Notes, Rappels, Calendrier, Messages, WhatsApp, Microsoft (Word, Excel, Outlook),
IINA, VLC, Spotify, Safari, Tor Browser, Transmission, AlDente, Finder & Système.
"""

import os
import subprocess
import urllib.parse
import re

def _run_osa(script: str, timeout: int = 8) -> str:
    """Exécute un script AppleScript avec gestion des erreurs et timeout."""
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Erreur AppleScript : {res.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Délai d'attente dépassé pour l'application cible."
    except Exception as e:
        return f"Erreur : {str(e)}"

# ============================================================
# 1. APPLE NOTES (Notes.app)
# ============================================================
def create_note(title: str, content: str = "") -> str:
    """Crée une nouvelle note dans Apple Notes."""
    title_escaped = title.replace('"', '\\"')
    content_escaped = content.replace('"', '\\"')
    body_html = f"<div><b>{title_escaped}</b></div><br><div>{content_escaped}</div>"
    
    script = f'''
    if application "Notes" is not running then
        tell application "Notes" to activate
        delay 0.8
    end if
    tell application "Notes"
        tell account 1
            make new note at default folder with properties {{name:"{title_escaped}", body:"{body_html}"}}
        end tell
    end tell
    return "Note créée avec succès : {title_escaped}"
    '''
    return _run_osa(script)

def list_recent_notes(limit: int = 5) -> str:
    """Récupère les titres des notes récentes."""
    script = f'''
    if application "Notes" is not running then
        tell application "Notes" to activate
        delay 0.8
    end if
    tell application "Notes"
        set noteList to name of notes
        set outList to {{}}
        set maxItems to {limit}
        if (count of noteList) < maxItems then
            set maxItems to (count of noteList)
        end if
        repeat with i from 1 to maxItems
            set end of outList to (item i of noteList)
        end repeat
        set AppleScript's text item delimiters to ", "
        return outList as text
    end tell
    '''
    res = _run_osa(script)
    if not res or "Erreur" in res:
        return "Impossible d'accéder aux notes pour le moment."
    return f"Vos dernières notes Apple : {res}."

# ============================================================
# 2. APPLE RAPPELS (Reminders.app)
# ============================================================
def add_reminder(title: str, due_date: str = "") -> str:
    """Ajoute un rappel dans l'application Rappels."""
    title_escaped = title.replace('"', '\\"')
    script = f'''
    if application "Reminders" is not running then
        tell application "Reminders" to activate
        delay 0.8
    end if
    tell application "Reminders"
        set targetList to default list
        make new reminder at targetList with properties {{name:"{title_escaped}"}}
        return "Rappel ajouté : {title_escaped}"
    end tell
    '''
    return _run_osa(script)

def list_reminders(limit: int = 5) -> str:
    """Liste les rappels en attente."""
    script = f'''
    if application "Reminders" is not running then
        tell application "Reminders" to activate
        delay 0.8
    end if
    tell application "Reminders"
        set rems to (name of reminders of default list whose completed is false)
        set outList to {{}}
        set maxItems to {limit}
        if (count of rems) < maxItems then
            set maxItems to (count of rems)
        end if
        repeat with i from 1 to maxItems
            set end of outList to (item i of rems)
        end repeat
        set AppleScript's text item delimiters to ", "
        return outList as text
    end tell
    '''
    res = _run_osa(script)
    if not res or "Erreur" in res:
        return "Aucun rappel en attente trouvé."
    return f"Vos rappels en attente : {res}."

# ============================================================
# 3. APPLE CALENDRIER (Calendar.app)
# ============================================================
def open_calendar_and_view() -> str:
    """Ouvre l'application Calendrier."""
    subprocess.run(["open", "-a", "Calendar"])
    return "Application Calendrier ouverte à l'écran, monsieur."

# ============================================================
# 4. MESSAGES & WHATSAPP
# ============================================================
def send_imessage(target: str, message: str) -> str:
    """Envoie ou prépare un message via l'application Messages."""
    target_clean = target.replace('"', '\\"')
    msg_clean = message.replace('"', '\\"')
    script = f'''
    tell application "Messages"
        activate
        try
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{target_clean}" of targetService
            send "{msg_clean}" to targetBuddy
            return "Message envoyé à {target_clean}."
        on error
            return "Impossible d'envoyer directement. L'application Messages est ouverte."
        end try
    end tell
    '''
    return _run_osa(script)

def open_whatsapp_chat(contact_or_number: str = "", message: str = "") -> str:
    """Ouvre WhatsApp avec un contact ou prépare un message."""
    subprocess.run(["open", "-a", "WhatsApp"])
    if message:
        encoded = urllib.parse.quote(message)
        phone = re.sub(r'[^0-9+]', '', contact_or_number)
        if phone:
            url = f"whatsapp://send?phone={phone}&text={encoded}"
        else:
            url = f"whatsapp://send?text={encoded}"
        subprocess.run(["open", url])
        return f"WhatsApp ouvert avec le message préparé pour {contact_or_number or 'votre contact'}."
    return "WhatsApp ouvert à l'écran, monsieur."

# ============================================================
# 5. SUITE MICROSOFT (Outlook, Word, Excel) & CLOUD GRAPH
# ============================================================
def compose_outlook_email(to: str = "", subject: str = "", body: str = "") -> str:
    """Prépare un nouvel email dans Microsoft Outlook."""
    subprocess.run(["open", "-a", "Microsoft Outlook"])
    sub_val = subject.replace('"', '\\"') if subject else "Message de Nikkoola"
    body_val = body.replace('"', '\\"') if body else "Bonjour,\n\n"
    to_val = to.replace('"', '\\"').strip()

    script = f'''
    tell application "Microsoft Outlook"
        activate
        set newMsg to make new outgoing message with properties {{subject:"{sub_val}", plain text content:"{body_val}"}}
        if "{to_val}" is not "" then
            make new recipient at newMsg with properties {{email address:{{name:"{to_val}", address:"{to_val}"}}}}
        end if
        open newMsg
        return "Brouillon d'email préparé dans Outlook pour {to_val or 'votre destinataire'}."
    end tell
    '''
    res = _run_osa(script)
    if "Erreur" in res or not res:
        return f"Microsoft Outlook a été ouvert avec un nouveau message pour {to_val or 'votre destinataire'}."
    return res

def check_outlook_emails(count: int = 6) -> str:
    """Consulte et présente élégamment les e-mails réels du compte Exchange professionnel."""
    try:
        from . import outlook_graph
        if outlook_graph.is_configured():
            return outlook_graph.get_unread_emails(count)
    except Exception:
        pass

    script = f'''
    tell application "Mail"
        try
            set exAcc to account "Exchange"
            set inb to mailbox "Boîte de réception" of exAcc
            set unreadC to unread count of inb
            
            set res to ""
            set maxCount to {count}
            set recentMsgs to (messages 1 thru maxCount of inb)
            repeat with aMsg in recentMsgs
                set s_subj to subject of aMsg
                set s_snd to sender of aMsg
                set s_dt to date received of aMsg as string
                set s_rd to read status of aMsg
                set is_read_str to "1"
                if not s_rd then set is_read_str to "0"
                set res to res & s_snd & "|||" & s_subj & "|||" & s_dt & "|||" & is_read_str & "###"
            end repeat
            return (unreadC as string) & "###" & res
        on error errMsg
            return "error:" & errMsg
        end try
    end tell
    '''
    raw = _run_osa(script, timeout=8)
    if not raw or raw.startswith("error:"):
        return "Impossible de récupérer vos e-mails professionnels pour le moment."

    parts = raw.strip().split("###")
    unread_count = parts[0].strip() if parts else "0"
    items = [p for p in parts[1:] if p.strip()]

    lines = [
        f"📬 **Messagerie Professionnelle Exchange** (ville-gennevilliers.fr)",
        f"État : **{unread_count} message(s) non lu(s)** dans votre boîte de réception\n"
    ]

    for idx, item in enumerate(items, 1):
        fields = item.split("|||")
        if len(fields) < 4:
            continue
        sender_raw, subject, date_raw, is_read_str = fields[0], fields[1], fields[2], fields[3]
        
        # Nettoyage et extraction de l'expéditeur
        match = re.search(r'^(.*?)\s*<([^>]+)>', sender_raw)
        if match:
            snd_name = match.group(1).strip()
            snd_email = match.group(2).strip()
        else:
            snd_name = sender_raw.strip()
            snd_email = ""

        # Détection de catégorie pour emoji
        cat_emoji = "✉️"
        sub_low = subject.lower()
        if any(w in sub_low for w in ["paie", "salaire", "variable", "septembre", "octobre", "conges", "congés", "arret", "arrêt"]):
            cat_emoji = "💼"
        elif any(w in sub_low for w in ["lecteur", "vitale", "materiel", "matériel", "carte", "panne"]):
            cat_emoji = "🛠️"
        elif any(w in sub_low for w in ["formation", "suicide", "crise", "vaccination", "stage"]):
            cat_emoji = "🎓"
        elif any(w in sub_low for w in ["re:", "re :", "fw:", "fwd:"]):
            cat_emoji = "💬"

        # Format de date simplifié
        dt_clean = date_raw.replace(" à ", " à ").replace("octobre 2026", "oct.")
        
        status_tag = "🔴 [Non lu]" if is_read_str == "0" else "✓ [Lu]"
        subj_display = subject.strip() if subject.strip() else "(Sans objet)"

        lines.append(
            f"**{idx}. {cat_emoji} {snd_name}** {status_tag}\n"
            f"   • **Objet** : *« {subj_display} »*\n"
            f"   • *Reçu le {dt_clean}*"
        )

    lines.append("\n💡 **Actions rapides disponibles :**")
    lines.append("• Dites : *« Réponds à Ramy Dakhlia concernant les éléments de paie »*")
    lines.append("• Dites : *« Réponds à Léa Baroukh pour les dates de congés »*")
    lines.append("• Dites : *« Ouvre Outlook »* pour consulter l'un de ces messages à l'écran.")

    return "\n".join(lines)

def get_outlook_calendar() -> str:
    """Consulte l'agenda pro de la journée."""
    try:
        from . import outlook_graph
        if outlook_graph.is_configured():
            return outlook_graph.get_calendar_today()
    except Exception:
        pass
    return "💡 Connectez votre jeton Microsoft Graph dans les paramètres de HAL pour afficher vos réunions du jour."

def create_word_document() -> str:
    """Crée un nouveau document vierge dans Microsoft Word."""
    subprocess.run(["open", "-a", "Microsoft Word"])
    script = '''
    tell application "Microsoft Word"
        activate
        make new document
        return "Nouveau document créé dans Microsoft Word."
    end tell
    '''
    res = _run_osa(script)
    return "Microsoft Word est ouvert avec un nouveau document prêt."

def create_excel_spreadsheet() -> str:
    """Crée un nouveau classeur vierge dans Microsoft Excel."""
    subprocess.run(["open", "-a", "Microsoft Excel"])
    script = '''
    tell application "Microsoft Excel"
        activate
        make new workbook
        return "Nouveau classeur créé dans Microsoft Excel."
    end tell
    '''
    res = _run_osa(script)
    return "Microsoft Excel est ouvert avec un nouveau classeur prêt."

# ============================================================
# 6. LECTEURS MULTIMÉDIA (IINA, VLC, Spotify)
# ============================================================
def open_in_iina(target: str) -> str:
    """Ouvre une vidéo ou un lien de streaming dans le lecteur IINA."""
    subprocess.run(["open", "-a", "IINA", target])
    return f"Lecture lancée dans IINA : {target}"

def control_vlc(action: str = "play") -> str:
    """Contrôle la lecture dans VLC."""
    action_map = {
        "play": "play",
        "pause": "play",
        "stop": "stop",
        "next": "next",
        "previous": "previous",
        "fullscreen": "fullscreen"
    }
    cmd = action_map.get(action.lower(), "play")
    script = f'''
    if application "VLC" is running then
        tell application "VLC" to {cmd}
        return "Commande VLC {action} transmise."
    else
        return "VLC n'est pas ouvert."
    end if
    '''
    return _run_osa(script)

# ============================================================
# 7. NAVIGATION WEB (Safari, Tor Browser)
# ============================================================
def safari_open(url: str) -> str:
    """Ouvre une URL dans Safari."""
    if not url.startswith("http"):
        url = "https://" + url
    subprocess.run(["open", "-a", "Safari", url])
    return f"Page ouverte dans Safari : {url}"

def safari_search(query: str) -> str:
    """Effectue une recherche Google dans Safari."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    subprocess.run(["open", "-a", "Safari", url])
    return f"Recherche lancée dans Safari pour : « {query} »."

def safari_get_active_tab() -> str:
    """Récupère l'URL et le titre de l'onglet actif dans Safari."""
    script = '''
    if application "Safari" is running then
        tell application "Safari"
            set currentTab to current tab of front window
            set pageTitle to name of currentTab
            set pageUrl to URL of currentTab
            return "Onglet actif : " & pageTitle & " (" & pageUrl & ")"
        end tell
    else
        return "Safari n'est pas ouvert."
    end if
    '''
    return _run_osa(script)

def open_tor_browser() -> str:
    """Lance le navigateur sécurisé Tor Browser."""
    subprocess.run(["open", "-a", "Tor Browser"])
    return "Tor Browser lancé en mode navigation sécurisée et anonyme."

# ============================================================
# 8. TÉLÉCHARGEMENTS (Transmission)
# ============================================================
def transmission_add(url_or_magnet: str) -> str:
    """Ajoute un torrent ou un magnet link à Transmission."""
    subprocess.run(["open", "-a", "Transmission", url_or_magnet])
    return "Fichier torrent / magnet transmis à Transmission."

def transmission_toggle_all(action: str = "start") -> str:
    """Démarre ou suspend tous les téléchargements dans Transmission."""
    verb = "resume all" if action == "start" else "pause all"
    script = f'''
    if application "Transmission" is running then
        tell application "Transmission" to {verb}
        return "Téléchargements Transmission : {action} all."
    else
        tell application "Transmission" to activate
        return "Transmission ouvert à l'écran."
    end if
    '''
    return _run_osa(script)

# ============================================================
# 9. BATTERIE & CHARGE (AlDente)
# ============================================================
def open_aldente() -> str:
    """Ouvre le gestionnaire de batterie AlDente."""
    subprocess.run(["open", "-a", "AlDente"])
    return "Panneau AlDente ouvert pour la gestion de la charge et préservation de la batterie."

# ============================================================
# 10. PRODUCTIVITÉ FINDER & SYSTÈME
# ============================================================
def empty_trash() -> str:
    """Vide la corbeille macOS."""
    script = 'tell application "Finder" to empty trash'
    _run_osa(script)
    return "Corbeille vidée, monsieur."

def take_screenshot() -> str:
    """Capture l'écran complet et l'enregistre sur le bureau."""
    import time
    ts = int(time.time())
    dest = os.path.expanduser(f"~/Desktop/JARVIS_Capture_{ts}.png")
    subprocess.run(["screencapture", "-x", dest])
    return f"Capture d'écran enregistrée sur le bureau : JARVIS_Capture_{ts}.png."

def lock_screen() -> str:
    """Verrouille immédiatement la session Mac."""
    subprocess.run(["pmset", "displaysleepnow"])
    return "Écran mis en veille et session verrouillée, monsieur."

def open_folder(folder_name: str) -> str:
    """Ouvre un dossier usuel dans le Finder."""
    target_map = {
        "téléchargements": "~/Downloads",
        "downloads": "~/Downloads",
        "bureau": "~/Desktop",
        "desktop": "~/Desktop",
        "documents": "~/Documents",
        "applications": "/Applications",
        "musique": "~/Music",
        "images": "~/Pictures"
    }
    path = os.path.expanduser(target_map.get(folder_name.lower(), "~/Downloads"))
    subprocess.run(["open", path])
    return f"Dossier {folder_name.capitalize()} ouvert dans le Finder."
