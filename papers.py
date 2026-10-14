"""Fetch paper suggestions from Hugging Face Daily Papers and arXiv."""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from config import CACHE_DIR

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_API = "https://export.arxiv.org/api/query"
HF_API = "https://huggingface.co/api/daily_papers"
TIMEOUT = 15

CV_CATS = {"cs.CV", "eess.IV"}
NLP_CATS = {"cs.CL"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-log/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _area_from_cats(cats):
    cats = set(cats)
    cv, nlp = bool(cats & CV_CATS), bool(cats & NLP_CATS)
    if cv and nlp:
        return "Multimodal"
    if cv:
        return "CV"
    if nlp:
        return "NLP"
    return "Other"


def parse_arxiv_id(text):
    """Accept an arXiv id or any arxiv.org / hf.co/papers URL."""
    text = (text or "").strip()
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", text)
    return m.group(1) if m else None


def _parse_arxiv_feed(raw):
    papers = []
    for entry in ET.fromstring(raw).findall(f"{ATOM}entry"):
        id_url = entry.findtext(f"{ATOM}id", "")
        arxiv_id = parse_arxiv_id(id_url)
        if not arxiv_id:
            continue
        cats = [c.get("term") for c in entry.findall(f"{ATOM}category")]
        papers.append({
            "id": arxiv_id,
            "title": _clean(entry.findtext(f"{ATOM}title")),
            "summary": _clean(entry.findtext(f"{ATOM}summary")),
            "authors": ", ".join(_clean(a.findtext(f"{ATOM}name")) for a in entry.findall(f"{ATOM}author")),
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "area": _area_from_cats(cats),
            "source": "arXiv",
        })
    return papers


def fetch_arxiv(arxiv_id):
    """Metadata for a single paper, or None."""
    url = f"{ARXIV_API}?id_list={urllib.parse.quote(arxiv_id)}"
    try:
        papers = _parse_arxiv_feed(_get(url))
    except Exception:
        return None
    return papers[0] if papers and papers[0]["title"] else None


def _latest_arxiv(category, n):
    query = urllib.parse.urlencode({
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": n,
    })
    return _parse_arxiv_feed(_get(f"{ARXIV_API}?{query}"))


def _hf_daily(n):
    items = json.loads(_get(f"{HF_API}?limit=50"))
    papers = []
    for item in items:
        p = item.get("paper", {})
        if not p.get("id"):
            continue
        papers.append({
            "id": p["id"],
            "title": _clean(p.get("title") or item.get("title")),
            "summary": _clean(p.get("summary") or item.get("summary")),
            "authors": ", ".join(a.get("name", "") for a in p.get("authors", [])),
            "url": f"https://arxiv.org/abs/{p['id']}",
            "area": "",
            "upvotes": p.get("upvotes", 0),
            "source": "HF Daily",
        })
    papers.sort(key=lambda x: x["upvotes"], reverse=True)
    return papers[:n]


def suggestions(refresh=False):
    """Today's suggestions, cached per day. Returns {"hf": [...], "cv": [...], "nlp": [...], "errors": [...]}."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"suggestions-{date.today().isoformat()}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())

    result = {"hf": [], "cv": [], "nlp": [], "errors": []}
    for key, fn in (("hf", lambda: _hf_daily(8)),
                    ("cv", lambda: _latest_arxiv("cs.CV", 6)),
                    ("nlp", lambda: _latest_arxiv("cs.CL", 6))):
        try:
            result[key] = fn()
        except Exception as e:
            result["errors"].append(f"{key}: {e}")

    if not result["errors"]:
        for old in CACHE_DIR.glob("suggestions-*.json"):
            old.unlink()
        cache.write_text(json.dumps(result))
    return result
