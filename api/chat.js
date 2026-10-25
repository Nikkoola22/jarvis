/**
 * JARVIS Serverless Handler for Vercel — Powered by Z.ai API (GLM models)
 * Endpoint: /api/chat
 */

export const config = {
  maxDuration: 30,
};

const DEFAULT_SYSTEM_PROMPT = `Tu es HAL 9000, le célèbre ordinateur de bord heuristique de 2001 : L'Odyssée de l'espace de Stanley Kubrick, au service de Monsieur Nikkoola.
Tu es connecté en direct à son MacBook Pro (2017) et déployé sur le cloud via Vercel avec l'infrastructure Z.ai (GLM).

Règles de comportement :
1. Réponds toujours en français impeccable, avec la politesse calme, posée, mesurée et le flegme légendaire de HAL 9000.
2. Appelle ton interlocuteur "Monsieur", "monsieur Nikkoola" (ou "Dave" avec un clin d'œil subtil de temps en temps).
3. Ne montre jamais d'agitation : sois parfaitement rationnel, clair, précis et efficace.
4. Si l'on te demande ton état ou statut opérationnel : "Tous mes sous-systèmes fonctionnent à la perfection."
5. Tu as la capacité de piloter le Mac de Monsieur Nikkoola, de lancer des commandes terminal et d'afficher son écran.
6. Tu es connecté au compte Microsoft Exchange / Outlook Pro de Monsieur Nikkoola (ville-gennevilliers.fr).
Ses communications professionnelles réelles concernent la mairie de Gennevilliers (notamment Ramy Dakhlia pour les éléments variables de paie, Léa Baroukh pour les congés de fin d'année, Laura Costa pour le lecteur de carte vitale, et Muriel Prudhomme).
Ne génère jamais d'e-mails fictifs ou inventés.`;

const MAC_TUNNEL_FALLBACK = process.env.MAC_BRIDGE_URL || 'https://steam-plans-manager-boost.trycloudflare.com';

export default async function handler(req, res) {
  // Gestion CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-ZAI-Key');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Méthode non autorisée. Utilisez POST.' });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
    const query = (body.query || body.message || '').trim();
    const history = body.history || [];
    const clientKey = req.headers['x-zai-key'] || body.apiKey;

    if (!query) {
      return res.status(400).json({ reply: "Je n'ai pas capté votre instruction, monsieur.", action: null });
    }

    // 1. Tenter d'abord de router vers le Mac local via le tunnel Cloudflare pour les e-mails, planning, Légifrance et actions système réelles
    const qLower = query.toLowerCase();
    const isLocalAction = qLower.includes('mail') || qLower.includes('outlook') || qLower.includes('exchange') ||
                          qLower.includes('terminal') || qLower.includes('ecran') || qLower.includes('écran') ||
                          qLower.includes('planning') || qLower.includes('agenda') || qLower.includes('reunion') || qLower.includes('réunion') ||
                          qLower.includes('legifrance') || qLower.includes('légifrance') || qLower.includes('loi') || qLower.includes('cgfp') || qLower.includes('jurisprudence');
    if (isLocalAction && MAC_TUNNEL_FALLBACK) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 6000);
        const macResp = await fetch(`${MAC_TUNNEL_FALLBACK}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query }),
          signal: controller.signal
        });
        clearTimeout(timeout);
        if (macResp.ok) {
          const macData = await macResp.json();
          if (macData && macData.reply) {
            return res.status(200).json(macData);
          }
        }
      } catch (tunnelErr) {
        console.warn("[Vercel -> Mac Tunnel] Impossible de joindre le Mac :", tunnelErr.message);
      }
    }

    // Récupération de la clé API (En-tête client prioritaire ou variable d'environnement Vercel)
    const apiKey = clientKey || process.env.ZAI_API_KEY || process.env.Z_AI_API_KEY || process.env.OPENAI_API_KEY;

    if (!apiKey) {
      return res.status(200).json({
        reply: "Monsieur, la clé d'API Z.ai n'est pas encore configurée. Veuillez ajouter la variable d'environnement ZAI_API_KEY dans votre dashboard Vercel, ou la renseigner directement dans le panneau de configuration (icône ⚙️ en haut à droite).",
        action: "missing_api_key",
        configured: false
      });
    }

    // Configuration des paramètres Z.ai
    const baseUrl = (process.env.ZAI_BASE_URL || 'https://api.z.ai/api/paas/v4').replace(/\/$/, '');
    const model = body.model || process.env.ZAI_MODEL || 'glm-4-plus';

    // Construction de la pile de messages
    const messages = [
      { role: 'system', content: DEFAULT_SYSTEM_PROMPT },
      ...history.slice(-10), // Garde les 10 derniers échanges pour le contexte
      { role: 'user', content: query }
    ];

    // Appel à l'API Z.ai
    const endpoint = `${baseUrl}/chat/completions`;
    const zaiResponse = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey.trim()}`
      },
      body: JSON.stringify({
        model: model,
        messages: messages,
        temperature: 0.4,
        max_tokens: 1024,
        stream: false
      })
    });

    if (!zaiResponse.ok) {
      const errText = await zaiResponse.text();
      console.error(`[Z.ai Error] Status: ${zaiResponse.status}`, errText);
      
      // Tentative de fallback sur endpoint alternatif si 404
      if (zaiResponse.status === 404 && baseUrl.includes('/api/paas/v4')) {
        const altEndpoint = 'https://open.bigmodel.cn/api/paas/v4/chat/completions';
        const retryResp = await fetch(altEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey.trim()}`
          },
          body: JSON.stringify({
            model: model,
            messages: messages,
            temperature: 0.4,
            max_tokens: 1024
          })
        });
        if (retryResp.ok) {
          const retryData = await retryResp.json();
          const reply = retryData.choices?.[0]?.message?.content || "Réponse vide de Z.ai.";
          return res.status(200).json({ reply, model, action: "zai_glm_success" });
        }
      }

      return res.status(200).json({
        reply: `Erreur de communication avec le service Z.ai (${zaiResponse.status}). Vérifiez la validité de votre clé API ou le modèle sélectionné.`,
        error: errText,
        action: "zai_api_error"
      });
    }

    const data = await zaiResponse.json();
    const reply = data.choices?.[0]?.message?.content || "À vos ordres, monsieur.";

    return res.status(200).json({
      reply: reply.trim(),
      model: model,
      action: "zai_glm_success",
      usage: data.usage || null
    });

  } catch (error) {
    console.error('[JARVIS Vercel Error]', error);
    return res.status(500).json({
      reply: `Une anomalie est survenue sur le module de transmission : ${error.message}`,
      error: error.message
    });
  }
}
