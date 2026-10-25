# ⚡ J.A.R.V.I.S. — Complete AI Assistant Suite

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FNikkoola22%2Fjarvis&env=ZAI_API_KEY)

Assistant personnel d'élite inspiré d'Iron Man, proposant une double architecture :
1. 🌐 **JARVIS Cloud (Vercel & Z.ai)** : Version serverless ultra-rapide déployable en 1 clic sur Vercel, propulsée par l'API **Z.ai (GLM-4 / GLM-5.3)** avec interface holographique web et reconnaissance vocale.
2. 💻 **JARVIS Local (Mac & Hermes 3 / Llama 3.2)** : Version 100% hors-ligne exécutée sur MacBook Pro (Ollama, AppleScript, MCP Spotify/Mail, synthèse vocale native).

---

## 🌐 1. Déploiement Cloud sur Vercel (Z.ai GLM)

### Déploiement en 1 clic
1. Cliquez sur le bouton **Deploy with Vercel** ci-dessus ou importez ce dépôt sur [vercel.com](https://vercel.com).
2. Ajoutez la variable d'environnement :
   - `ZAI_API_KEY` = *votre clé API Z.ai*
   - `ZAI_MODEL` = `glm-4-flash` *(optionnel)*
3. Cliquez sur **Deploy** !

### Déploiement en CLI (30 secondes)
```bash
npx vercel
npx vercel env add ZAI_API_KEY
npx vercel --prod
```

### Fonctionnalités Cloud
- ⚛️ **Interface Holographique Arc Reactor** : Onde visuelle réactive en Canvas 2D.
- 🎙️ **Reconnaissance & Synthèse Vocale Web** : Parlez au micro (ou appuyez sur Espace) et écoutez JARVIS vous répondre dans le navigateur.
- ⚙️ **Panneau de Configuration Embarqué (⚙️)** : Permet de tester ou changer sa clé d'API Z.ai directement dans l'interface sans re-déployer.

---

## 💻 2. Version Locale macOS (Hermes 3 & Ollama)

Située dans le dossier [`local/`](./local/) :
- 🧠 **Cerveau local** : Hermes 3 (Nous Research) ou Llama 3.2 3B via Ollama.
- 🛠️ **Outils système Mac** : Pilotage du volume, luminosité, dark mode, ouverture d'apps, météo.
- 🎵 **Intégration Spotify & Mail** : Contrôle de la musique et lecture des courriels via AppleScript & MCP.
- 🔁 **Boucle d'apprentissage Hermes** : Capacité d'apprendre de nouvelles compétences persistées en SQLite (`memory.db`).

### Lancer la version locale :
```bash
cd local
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt # si applicable
python3 jarvis.py
```

---

## 📁 Structure du Répertoire

```
jarvis/
├── api/                  # Fonctions Serverless Vercel
│   ├── chat.js           # Relais Z.ai GLM avec prompt JARVIS
│   └── telemetry.js      # Statut runtime cloud
├── public/               # Frontend Web holographique
│   └── index.html        # Interface Arc Reactor Canvas + Web Audio
├── local/                # Version locale Mac (Hermes 3, Ollama, AppleScript)
│   ├── core/             # Moteurs Python (brain, hardware, voice, tools)
│   ├── jarvis.py         # Entrypoint vocal local
│   ├── server.py         # Pont HTTP local (port 8888)
│   └── web/              # HUD local
├── vercel.json           # Routage et CORS pour Vercel
├── server.js             # Émulateur local Node.js pour tester le cloud
├── package.json          # Configuration Vercel / Node
├── .env.example          # Gabarit des variables d'environnement
└── README.md
```

---

## 🔑 Variables d'Environnement Vercel

| Variable | Description | Requis |
| :--- | :--- | :--- |
| `ZAI_API_KEY` | Clé d'API Z.ai (Bearer Token) | **Oui** |
| `ZAI_MODEL` | Modèle Z.ai (`glm-4-flash`, `glm-4`, `glm-5.3`) | Non (défaut: `glm-4-flash`) |
| `ZAI_BASE_URL` | Base URL Z.ai | Non (défaut: `https://api.z.ai/api/paas/v4`) |

---

## 👤 Auteur
Conçu pour **Nikkoola** — Inspiré de J.A.R.V.I.S. (Iron Man / Tony Stark).
