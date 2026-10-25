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

        self.send_response(404)
        self.end_headers()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html", "/api/telemetry", "/api/screen"]:
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
