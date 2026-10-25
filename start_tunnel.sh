#!/usr/bin/env bash
# JARVIS Remote Bridge Launcher for iPhone & Web Access
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo ""
echo "=========================================================="
echo "🤖 DÉMARRAGE DU PONT JARVIS POUR IPHONE & VERCEL"
echo "=========================================================="

# 1. Vérifier si server.py tourne déjà, sinon le lancer
if ! curl -s http://localhost:8888/api/telemetry >/dev/null 2>&1; then
    echo "⚡ Lancement de server.py en arrière-plan..."
    python3 server.py &
    SERVER_PID=$!
    sleep 1.5
else
    echo "✅ server.py tourne déjà sur le port 8888."
fi

# Nettoyage si on quitte
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    echo ""
    echo "👋 Pont JARVIS arrêté."
    exit 0
}
trap cleanup INT TERM

echo ""
echo "🌐 Création du tunnel HTTPS public..."
echo "----------------------------------------------------------"

# 2. Utiliser cloudflared s'il existe, sinon le tunnel SSH instantané
if command -v cloudflared >/dev/null 2>&1; then
    echo "🚀 Tunnel Cloudflare en cours..."
    cloudflared tunnel --url http://localhost:8888
else
    echo "🔑 Connexion au tunnel HTTPS instantané (Pinggy SSH)..."
    echo "👉 Copiez l'URL https://xxxx.a.pinggy.link qui apparaîtra ci-dessous"
    echo "👉 Collez-la dans les réglages ⚙️ sur votre iPhone"
    echo "----------------------------------------------------------"
    ssh -o StrictHostKeyChecking=no -p 443 -R0:localhost:8888 a.pinggy.io
fi
