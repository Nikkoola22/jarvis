/**
 * Microsoft Graph / Outlook Serverless Handler for Vercel
 * Endpoint: /api/outlook
 */

export const config = {
  maxDuration: 15,
};

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Graph-Token');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const token = req.headers['x-graph-token'] || process.env.OUTLOOK_ACCESS_TOKEN || process.env.MS_GRAPH_TOKEN;

  if (req.method === 'GET') {
    if (!token) {
      return res.status(200).json({
        configured: false,
        message: "Jeton Microsoft Graph non configuré. Renseignez votre jeton dans le panneau de configuration."
      });
    }

    try {
      const graphRes = await fetch("https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$filter=isRead eq false&$top=5&$select=subject,from,receivedDateTime,bodyPreview", {
        headers: {
          "Authorization": `Bearer ${token.trim()}`,
          "Accept": "application/json"
        }
      });

      if (!graphRes.ok) {
        const err = await graphRes.text();
        return res.status(200).json({ configured: false, error: `Erreur Graph: ${err}` });
      }

      const data = await graphRes.json();
      return res.status(200).json({
        configured: true,
        unreadCount: data.value ? data.value.length : 0,
        messages: data.value || []
      });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  if (req.method === 'POST') {
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
    const action = body.action || 'send';

    if (!token) {
      return res.status(400).json({ error: "Jeton Microsoft Graph requis pour envoyer un e-mail." });
    }

    if (action === 'send') {
      const { to, subject, message } = body;
      try {
        const sendRes = await fetch("https://graph.microsoft.com/v1.0/me/sendMail", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token.trim()}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message: {
              subject: subject || "Message de Nikkoola",
              body: { contentType: "Text", content: message || "Bonjour,\n\n" },
              toRecipients: [{ emailAddress: { address: to } }]
            },
            saveToSentItems: "true"
          })
        });

        if (!sendRes.ok) {
          const err = await sendRes.text();
          return res.status(400).json({ error: `Erreur d'envoi Graph: ${err}` });
        }

        return res.status(200).json({ success: true, message: `E-mail envoyé avec succès à ${to}.` });
      } catch (e) {
        return res.status(500).json({ error: e.message });
      }
    }
  }

  return res.status(405).json({ error: "Méthode non autorisée" });
}
