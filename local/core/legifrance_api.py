"""
HAL 9000 — Module de Recherche Légifrance Officiel (API PISTE / DILA)
Permet d'interroger en temps réel le droit français consolidé :
- Codes de lois (CGFP, CGCT, Code civil, Code du travail, etc.)
- Jurisprudence administrative (Conseil d'État, CAA, TA)
- Textes et décrets consolidés

Identifiants issus du projet Gruuuprimes (DILA / PISTE).
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import re

# Identifiants PISTE / Légifrance officiels
DEFAULT_CLIENT_ID = os.environ.get("LEGIFRANCE_CLIENT_ID", "c21e08ec-26bf-4699-868b-e7e86264cb79")
DEFAULT_CLIENT_SECRET = os.environ.get("LEGIFRANCE_CLIENT_SECRET", "a1cd3e71-e63f-4ec7-b74c-a28f5c4042c6")
DEFAULT_API_KEY = os.environ.get("LEGIFRANCE_API_KEY", "6f3304e9-0093-46c4-8a20-f0dc98c73a01")

TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
API_BASE = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"

# Cache mémoire pour le token OAuth2
_piste_token = None
_piste_token_expires = 0

STOPWORDS = {
    "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en", "et", "eux",
    "il", "ils", "je", "la", "le", "les", "leur", "lui", "ma", "mais", "me", "mes", "moi",
    "mon", "ne", "nos", "notre", "nous", "on", "ou", "par", "pas", "pour", "que", "qui",
    "sa", "se", "ses", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une",
    "vos", "votre", "vous", "c", "d", "j", "l", "m", "n", "s", "t", "y", "est", "sont",
    "recherche", "cherche", "trouve", "donne", "quel", "quelle", "quels", "quelles"
}

CODE_NAMES = {
    "CGFP": "Code général de la fonction publique",
    "CGCT": "Code général des collectivités territoriales",
    "CIVIL": "Code civil",
    "TRAVAIL": "Code du travail",
    "PENAL": "Code pénal",
    "COMMANDE_PUBLIQUE": "Code de la commande publique",
    "CRPA": "Code des relations entre le public et l'administration",
    "SANTE": "Code de la santé publique",
    "URBANISME": "Code de l'urbanisme"
}

def get_piste_token() -> str:
    """Récupère ou réutilise un jeton OAuth2 valide pour PISTE Légifrance."""
    global _piste_token, _piste_token_expires
    now = time.time()
    if _piste_token and now < _piste_token_expires:
        return _piste_token

    params = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": DEFAULT_CLIENT_ID,
        "client_secret": DEFAULT_CLIENT_SECRET,
        "scope": "openid"
    }).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=params, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _piste_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            _piste_token_expires = now + max(60, expires_in - 120)
            return _piste_token
    except Exception as e:
        raise RuntimeError(f"Échec de connexion OAuth2 PISTE Légifrance : {e}")

def _strip_tags(text: str) -> str:
    """Nettoie les balises HTML et <mark>."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()

def search_legifrance(query: str, fond: str = "CODE_DATE", limit: int = 4) -> dict:
    """Recherche des textes consolidés ou décisions de justice sur Légifrance."""
    token = get_piste_token()

    # Nettoyage des mots vides pour optimiser la recherche BM25
    words = re.findall(r"[\w'-]+", query.lower())
    filtered = [w for w in words if len(w) > 1 and w not in STOPWORDS]
    valeur = " ".join(filtered) if filtered else query

    payload = {
        "fond": fond,
        "recherche": {
            "champs": [{
                "typeChamp": "ALL",
                "criteres": [{
                    "valeur": valeur,
                    "typeRecherche": "UN_DES_MOTS",
                    "operateur": "ET"
                }],
                "operateur": "ET"
            }],
            "filtres": [],
            "pageNumber": 1,
            "pageSize": limit,
            "operateur": "ET",
            "sort": "PERTINENCE",
            "typePagination": "DEFAUT"
        }
    }

    req = urllib.request.Request(f"{API_BASE}/search", data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {token}",
        "KeyId": DEFAULT_API_KEY,
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_results = data.get("results", [])
            items = []
            for r in raw_results[:limit]:
                titles = r.get("titles") or [{}]
                title_clean = _strip_tags(titles[0].get("title") or r.get("title") or "Texte Légifrance")
                item_id = titles[0].get("id") or r.get("id") or ""
                num = r.get("num")
                
                # Extraction d'un résumé si disponible
                summary = ""
                for sec in r.get("sections", []):
                    for ext in sec.get("extracts", []):
                        vals = ext.get("values")
                        if vals and len(vals) > 0:
                            summary = _strip_tags(vals[0])[:250]
                            break
                    if summary:
                        break

                # Construction du lien officiel
                link = "https://www.legifrance.gouv.fr"
                if item_id:
                    if item_id.startswith("LEGIARTI"):
                        link = f"https://www.legifrance.gouv.fr/codes/article_lc/{item_id}"
                    elif item_id.startswith("CETATEXT"):
                        link = f"https://www.legifrance.gouv.fr/ceta/id/{item_id}"
                    elif item_id.startswith("JURITEXT"):
                        link = f"https://www.legifrance.gouv.fr/juri/id/{item_id}"
                    elif "LEGITEXT" in item_id:
                        clean_legitext = item_id.split("_")[0]
                        link = f"https://www.legifrance.gouv.fr/codes/texte_lc/{clean_legitext}"

                items.append({
                    "title": title_clean,
                    "id": item_id,
                    "num": num,
                    "summary": summary,
                    "link": link,
                    "nature": r.get("nature") or ("Code" if fond == "CODE_DATE" else "Décision")
                })

            return {
                "success": True,
                "total": data.get("totalResultNumber", len(items)),
                "results": items
            }
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}

def get_article_text(article_id: str) -> dict:
    """Récupère le texte intégral et les métadonnées d'un article par son identifiant LEGIARTI."""
    token = get_piste_token()
    payload = {"id": article_id}

    req = urllib.request.Request(f"{API_BASE}/consult/getArticle", data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {token}",
        "KeyId": DEFAULT_API_KEY,
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            art = data.get("article") or (data.get("listArticle") and data["listArticle"][0])
            if not art:
                return {"success": False, "error": "Article non trouvé"}

            num = art.get("num", "")
            etat = art.get("etat", "VIGUEUR")
            texte = art.get("texte") or art.get("texteHtml") or ""
            return {
                "success": True,
                "num": num,
                "id": article_id,
                "etat": etat,
                "texte": _strip_tags(texte),
                "link": f"https://www.legifrance.gouv.fr/codes/article_lc/{article_id}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def consult_legifrance(query: str) -> str:
    """Fonction principale appelée par le cerveau de HAL 9000."""
    q_clean = query.strip()

    # Détection si recherche de jurisprudence ou de texte de code
    is_jurisprudence = any(w in q_clean.lower() for w in [
        "jurisprudence", "conseil d'état", "conseil d'etat", "cour de cassation", "caa", "jugement", "arrêt", "tribunal"
    ])

    fond = "CETAT" if is_jurisprudence else "CODE_DATE"
    res = search_legifrance(q_clean, fond=fond, limit=4)

    if not res.get("success") or not res.get("results"):
        # Essayer sur l'autre fond en secours
        alt_fond = "CODE_DATE" if fond == "CETAT" else "CETAT"
        res = search_legifrance(q_clean, fond=alt_fond, limit=3)

    results = res.get("results", [])
    if not results:
        return (
            f"⚖️ **Légifrance (API PISTE / DILA)**\n\n"
            f"Aucun texte officiel consolidé n'a été trouvé pour la requête : *« {q_clean} »*.\n\n"
            f"💡 *Précisez le code (ex: CGFP, CGCT, Code civil) ou le numéro d'article (ex: L822-1).* "
        )

    lines = [
        f"⚖️ **Résultats Officiels Légifrance** (API PISTE / DILA)",
        f"Base : **{'Jurisprudence administrative' if fond == 'CETAT' else 'Codes consolidés en vigueur'}** | Requête : *« {q_clean} »*\n"
    ]

    for idx, r in enumerate(results, 1):
        num_str = f" **Article {r['num']}** —" if r.get("num") else ""
        lines.append(f"**{idx}.**{num_str} [{r['title']}]({r['link']})")
        if r.get("id"):
            lines.append(f"   • *Identifiant officiel* : `{r['id']}`")
        if r.get("summary"):
            lines.append(f"   • *Extrait* : *« {r['summary']}... »*")
        lines.append(f"   • 🔗 [Consulter le texte authentique sur Légifrance]({r['link']})\n")

    lines.append("💡 *Ces références proviennent directement de l'API certifiée de la DILA (Direction de l'information légale et administrative).*")
    return "\n".join(lines)
