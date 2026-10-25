/**
 * Local Development Server for JARVIS Vercel
 * Permet de tester en local exactement comme sur Vercel sans installer de dépendances.
 * Commande : node server.js
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PORT = process.env.PORT || 3000;

// Chargement basique de .env si existant
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
      const [k, ...v] = trimmed.split('=');
      process.env[k.trim()] = v.join('=').trim().replace(/^["']|["']$/g, '');
    }
  }
}

import chatHandler from './api/chat.js';
import telemetryHandler from './api/telemetry.js';

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  // Emulation des fonctions Serverless Vercel
  if (url.pathname === '/api/chat') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      req.body = body ? JSON.parse(body) : {};
      
      // Shim res.status().json()
      res.status = (code) => {
        res.statusCode = code;
        return {
          json: (data) => {
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify(data));
          },
          end: () => res.end()
        };
      };

      await chatHandler(req, res);
    });
    return;
  }

  if (url.pathname === '/api/telemetry') {
    res.status = (code) => ({
      json: (data) => {
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(data));
      }
    });
    return telemetryHandler(req, res);
  }

  // Fichiers statiques (public/)
  let filePath = path.join(__dirname, 'public', url.pathname === '/' ? 'index.html' : url.pathname);
  if (!fs.existsSync(filePath)) {
    filePath = path.join(__dirname, 'public', 'index.html');
  }

  try {
    const content = fs.readFileSync(filePath);
    const ext = path.extname(filePath);
    const contentType = ext === '.html' ? 'text/html' : (ext === '.css' ? 'text/css' : (ext === '.js' ? 'text/javascript' : 'application/octet-stream'));
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  } catch (e) {
    res.writeHead(404);
    res.end('File not found');
  }
});

server.listen(PORT, () => {
  console.log(`\n⚡ JARVIS Cloud (Z.ai / Vercel Emulator) actif sur http://localhost:${PORT}`);
  console.log(`🔑 Clé ZAI_API_KEY détectée : ${process.env.ZAI_API_KEY ? 'OUI' : 'NON (Configurable via interface ou .env)'}`);
  console.log(`🚀 Pour déployer sur Vercel : npx vercel\n`);
});
