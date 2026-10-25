/**
 * HAL 9000 — Serverless Légifrance Search (DILA / PISTE)
 * Endpoint: /api/legifrance
 */

const CLIENT_ID = process.env.LEGIFRANCE_CLIENT_ID || 'c21e08ec-26bf-4699-868b-e7e86264cb79';
const CLIENT_SECRET = process.env.LEGIFRANCE_CLIENT_SECRET || 'a1cd3e71-e63f-4ec7-b74c-a28f5c4042c6';
const API_KEY = process.env.LEGIFRANCE_API_KEY || '6f3304e9-0093-46c4-8a20-f0dc98c73a01';

let cachedToken = null;
let tokenExpiresAt = 0;

async function getToken() {
  if (cachedToken && Date.now() < tokenExpiresAt) {
    return cachedToken;
  }
  const params = new URLSearchParams();
  params.append('grant_type', 'client_credentials');
  params.append('client_id', CLIENT_ID);
  params.append('client_secret', CLIENT_SECRET);
  params.append('scope', 'openid');

  const res = await fetch('https://oauth.piste.gouv.fr/api/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString()
  });
  if (!res.ok) throw new Error(`OAuth error: ${res.status}`);
  const data = await res.json();
  cachedToken = data.access_token;
  tokenExpiresAt = Date.now() + ((data.expires_in || 3600) - 60) * 1000;
  return cachedToken;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    const query = req.method === 'POST' ? (req.body?.query || req.body?.q) : req.query?.q;
    if (!query) {
      return res.status(400).json({ error: 'Query parameter required' });
    }

    const token = await getToken();
    const isJuri = /jurisprudence|conseil d'état|cassation|arrêt|caa|jugement/i.test(query);
    const fond = isJuri ? 'CETAT' : 'CODE_DATE';

    const searchPayload = {
      fond,
      recherche: {
        champs: [{
          typeChamp: 'ALL',
          criteres: [{ valeur: query, typeRecherche: 'UN_DES_MOTS', operateur: 'ET' }],
          operateur: 'ET'
        }],
        filtres: [],
        pageNumber: 1,
        pageSize: 4,
        operateur: 'ET',
        sort: 'PERTINENCE',
        typePagination: 'DEFAUT'
      }
    };

    const apiRes = await fetch('https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'KeyId': API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(searchPayload)
    });

    if (!apiRes.ok) {
      return res.status(200).json({ success: false, error: `PISTE status ${apiRes.status}` });
    }

    const data = await apiRes.json();
    const results = (data.results || []).map(r => {
      const titles = r.titles || [{}];
      const title = (titles[0]?.title || r.title || '').replace(/<[^>]+>/g, '').trim();
      const id = titles[0]?.id || r.id || '';
      let link = 'https://www.legifrance.gouv.fr';
      if (id.startsWith('LEGIARTI')) link = `https://www.legifrance.gouv.fr/codes/article_lc/${id}`;
      else if (id.startsWith('CETATEXT')) link = `https://www.legifrance.gouv.fr/ceta/id/${id}`;
      else if (id.startsWith('JURITEXT')) link = `https://www.legifrance.gouv.fr/juri/id/${id}`;
      else if (id.includes('LEGITEXT')) link = `https://www.legifrance.gouv.fr/codes/texte_lc/${id.split('_')[0]}`;
      return { title, id, link, num: r.num };
    });

    return res.status(200).json({ success: true, fond, results });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
