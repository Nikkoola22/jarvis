#!/usr/bin/env python3
"""
JARVIS Local Web Server & API Bridge
Expose l'interface holographique sur http://localhost:8888 avec accès micro et pont Ollama.
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import subprocess
import re
from urllib.parse import urlparse

# Assurer le chargement des modules du dossier jarvis
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import brain
from core import hardware
from core import memory
from core import voice

PORT = 8888
HTML_PATH = os.path.join(BASE_DIR, "web", "jarvis_hud.html")

class JarvisHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(HTML_PATH, "rb") as f:
                self.wfile.write(f.read())
            return

        if parsed.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = hardware.get_full_telemetry()
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if parsed.path == "/api/screen":
            img_path = "/tmp/jarvis_screen.jpg"
            raw_path = "/tmp/jarvis_screen.png"
            import subprocess
            subprocess.run(["screencapture", "-x", raw_path])
            subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1280", raw_path, "--out", img_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(img_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                with open(img_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(500)
                self.end_headers()
            return

        if parsed.path == "/api/outlook":
            from core import outlook_graph, connectors
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = {
                "configured": outlook_graph.is_configured(),
                "outlook_installed": True,
                "summary": connectors.check_outlook_emails(count=3)
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html", "/api/telemetry", "/api/screen", "/api/outlook"]:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                query = payload.get("query", "").strip()

                if not query:
                    reply, action = "Je n'ai pas saisi votre demande, monsieur.", None
                else:
                    reply, action = brain.ask(query)

                    # Optionnel : prononcer également avec la voix macOS locale
                    threading.Thread(target=voice.speak, args=(reply,), daemon=True).start()

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply, "action": action}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if parsed.path == "/api/terminal":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            cwd = os.path.expanduser("~")
            try:
                payload = json.loads(body)
                raw_cmd = payload.get("command", "").strip()
                req_cwd = payload.get("cwd", "").strip()
                if req_cwd and os.path.isdir(os.path.expanduser(req_cwd)):
                    cwd = os.path.expanduser(req_cwd)

                if not raw_cmd:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Commande vide"}).encode("utf-8"))
                    return

                # Normalisation des guillemets iOS / smart quotes
                cmd = raw_cmd.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

                # Préparation de l'environnement d'exécution avec PATH complet
                sub_env = os.environ.copy()
                user_home = os.path.expanduser("~")
                local_bin = os.path.join(user_home, ".local", "bin")
                gemini_bin = os.path.join(user_home, ".gemini", "antigravity-cli", "bin")
                extra_paths = [local_bin, gemini_bin, "/opt/homebrew/bin", "/usr/local/bin"]
                sub_env["PATH"] = ":".join(extra_paths) + ":" + sub_env.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")

                # Guardrails pour commandes interactives TUI
                if cmd == "agy":
                    out = (
                        "💡 Antigravity CLI ('agy' seul) lance une interface TUI plein écran qui requiert un terminal physique.\n"
                        "Pour interroger Antigravity depuis votre iPhone ou le Web, utilisez le mode direct avec l'option -p :\n\n"
                        "  👉 agy -p \"votre consigne ou prompt\"\n"
                        "  👉 agy models\n"
                        "  👉 agy changelog\n"
                        "  👉 agy agent\n"
                    )
                    code = 0
                elif cmd in ["nano", "vi", "vim"]:
                    out = f"💡 '{cmd}' est un éditeur plein écran interactif. Pour afficher un fichier, utilisez 'cat <fichier>' ou 'head -n 20 <fichier>'.\n"
                    code = 0
                elif cmd == "top":
                    res = subprocess.run(
                        "top -l 1 | head -n 15",
                        shell=True,
                        executable="/bin/zsh",
                        capture_output=True,
                        text=True,
                        timeout=15,
                        cwd=cwd,
                        env=sub_env
                    )
                    out = res.stdout + res.stderr
                    code = res.returncode
                # Gestion spéciale de la navigation 'cd'
                elif cmd == "cd" or cmd.startswith("cd "):
                    target = cmd[3:].strip() if cmd.startswith("cd ") else "~"
                    target_dir = os.path.expanduser(target)
                    if not os.path.isabs(target_dir):
                        target_dir = os.path.normpath(os.path.join(cwd, target))
                    if os.path.isdir(target_dir):
                        cwd = target_dir
                        out = ""
                        code = 0
                    else:
                        out = f"cd: {target}: Aucun fichier ou dossier de ce nom\n"
                        code = 1
                else:
                    # Traitement automatique pour agy -p non quoté
                    # Si l'utilisateur tape: agy -p quel temps fait-il ?
                    m = re.match(r"^(agy\s+(?:-p|--print|--prompt))\s+(.+)$", cmd)
                    if m:
                        prefix = m.group(1)
                        prompt_arg = m.group(2).strip()
                        if not ((prompt_arg.startswith('"') and prompt_arg.endswith('"')) or
                                (prompt_arg.startswith("'") and prompt_arg.endswith("'"))):
                            escaped = prompt_arg.replace('"', '\\"')
                            cmd = f'{prefix} "{escaped}"'

                    # unsetopt nomatch pour empêcher l'erreur zsh sur les caractères de motif glob (?, *)
                    exec_cmd = f"unsetopt nomatch; {cmd}"
                    cmd_timeout = 80 if "agy" in cmd else 30

                    res = subprocess.run(
                        exec_cmd,
                        shell=True,
                        executable="/bin/zsh",
                        capture_output=True,
                        text=True,
                        timeout=cmd_timeout,
                        cwd=cwd,
                        env=sub_env
                    )
                    out = res.stdout + res.stderr
                    code = res.returncode

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "output": out,
                    "returncode": code,
                    "cwd": cwd
                }).encode("utf-8"))
            except subprocess.TimeoutExpired:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "output": "⏱️ Timeout : la commande a dépassé le délai imparti.\n",
                    "returncode": 124,
                    "cwd": cwd
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if parsed.path == "/api/outlook":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            from core import outlook_graph, connectors
            try:
                payload = json.loads(body) if body else {}
                action = payload.get("action", "check")
                if action == "save_token":
                    token = payload.get("token", "").strip()
                    res = outlook_graph.set_access_token(token)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(res).encode("utf-8"))
                    return
                elif action == "send":
                    res = connectors.compose_outlook_email(
                        to=payload.get("to", ""),
                        subject=payload.get("subject", ""),
                        body=payload.get("body", "")
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"reply": res}).encode("utf-8"))
                    return
                elif action == "calendar":
                    res = connectors.get_outlook_calendar()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"reply": res}).encode("utf-8"))
                    return
                else:
                    res = connectors.check_outlook_emails()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"reply": res}).encode("utf-8"))
                    return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP logs for quiet terminal
        return

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), JarvisHandler) as httpd:
        print(f"\n⚡ JARVIS Server actif sur http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
