/**
 * JARVIS Serverless Handler for Vercel — Powered by Z.ai API (GLM models)
 * Endpoint: /api/chat
 */

export const config = {
  maxDuration: 30,
};

const DEFAULT_SYSTEM_PROMPT = `Tu es JARVIS, l'assistant personnel d'élite de Monsieur Nikkoola, inspiré de l'intelligence artificielle de Tony Stark dans Iron Man.
Tu es déployé sur le cloud via Vercel et alimenté par le moteur d'intelligence avancée Z.ai (GLM).

Règles de comportement :
1. Réponds toujours en français impeccable, avec politesse, concision, élégance et précision digne de J.A.R.V.I.S.
2. Appelle ton interlocuteur "Monsieur" ou "monsieur Nikkoola".
3. Sois direct, rapide et percutant. Pas de bavardage inutile, concentre-toi sur l'efficacité et la clarté.
4. Si la demande concerne du code, de l'analyse ou de la planification, apporte une solution experte et structurée.
5. Si l'utilisateur demande qui tu es ou où tu fonctionnes, indique que tu es le système JARVIS Mark Vercel connecté à l'infrastructure Z.ai.`;

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
