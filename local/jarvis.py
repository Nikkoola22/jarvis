#!/usr/bin/env python3
"""
JARVIS Local Assistant — macOS Edition
Architecture inspirée de OpenJarvis (Stanford), Open Interpreter et sosoj92/jarvis-assistant-vocal.
Intègre Llama 3.2 (3B) local via Ollama, mémoire persistante SQLite et contrôle système complet.
"""

import argparse
import os
import sys
import subprocess

from core import brain
from core import hardware
from core import memory
from core import voice
from core import tools

def print_banner():
    print("""
\033[1;36m
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
   ██║███████║██████╔╝██║   ██║██║███████╗
██╗██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚████║██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
\033[0m
\033[1;32m[SYSTÈME EN LIGNE // MACBOOK PRO 15" 2017 // LLAMA 3.2 3B]\033[0m
Commandes utiles : 'télémétrie', 'batterie', 'météo', 'mode sombre', 'volume 40', 'ouvre Safari'.
Tapez 'quitter' pour sortir ou 'hud' pour ouvrir le tableau de bord visuel.
----------------------------------------------------------------------
""")

def main():
    parser = argparse.ArgumentParser(description="JARVIS Local AI Assistant")
    parser.add_argument("query", nargs="*", help="Question ou commande one-shot directe")
    parser.add_argument("--mute", action="store_true", help="Désactive la synthèse vocale")
    parser.add_argument("--hud", action="store_true", help="Ouvre l'interface web visuelle HUD")
    args = parser.parse_args()

    if args.mute:
        voice.set_mute(True)

    if args.hud:
        hud_path = os.path.expanduser("~/jarvis/web/index.html")
        print(f"Ouverture du HUD visuel : {hud_path}")
        subprocess.run(["open", hud_path])
        return

    # Si une requête directe en ligne de commande est fournie
    if args.query:
        query_text = " ".join(args.query)
        res, action = brain.ask(query_text)
        print(f"\n\033[1;36mJARVIS:\033[0m {res}\n")
        voice.speak(res)
        return

    # Mode interactif interactif complet
    print_banner()
    voice.play_chime("activate")
    
    facts = memory.get_all_facts()
    user_name = facts.get("nom_utilisateur", "monsieur")
    intro_message = f"Bonjour {user_name}. Tous les sous-systèmes sont prêts à vos ordres."
    print(f"\033[1;36mJARVIS:\033[0m {intro_message}\n")
    voice.speak(intro_message)

    history = []

    while True:
        try:
            user_input = input("\033[1;32m👤 Vous > \033[0m").strip()
            if not user_input:
                continue

            low = user_input.lower()
            if low in ["quitter", "exit", "quit", "stop", "au revoir"]:
                bye = "Mise en veille des systèmes. À votre service, monsieur."
                print(f"\n\033[1;36mJARVIS:\033[0m {bye}\n")
                voice.speak(bye)
                break

            if low == "hud":
                hud_path = os.path.expanduser("~/jarvis/web/index.html")
                subprocess.run(["open", hud_path])
                print("HUD visuel ouvert dans le navigateur.")
                continue

            if low in ["silence", "mute"]:
                voice.set_mute(True)
                print("Synthèse vocale coupée.")
                continue

            if low in ["voix", "unmute"]:
                voice.set_mute(False)
                print("Synthèse vocale activée.")
                voice.speak("La synthèse vocale est de nouveau active.")
                continue

            # Traitement de la requête
            res, action = brain.ask(user_input, history)

            # Mise à jour de l'historique
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": res})
            if len(history) > 12:
                history = history[-12:]

            # Log mémoire
            memory.log_interaction("user", user_input)
            memory.log_interaction("assistant", res)

            # Affichage et vocalisation
            print(f"\n\033[1;36mJARVIS:\033[0m {res}\n")
            if action:
                print(f"\033[90m[Action exécutée : {action}]\033[0m\n")
            
            voice.speak(res)

        except (KeyboardInterrupt, EOFError):
            print("\nArrêt.")
            break

if __name__ == "__main__":
    main()
