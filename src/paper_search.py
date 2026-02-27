"""Academic paper search via Semantic Scholar + OpenAlex fallback."""
import os
import requests


def search_papers(query: str, limit: int = 8) -> list[dict]:
    """
    Search for academic papers. Tries Semantic Scholar first, falls back to OpenAlex.

    Returns list of dicts: {title, authors, year, abstract, pdf_url, source}
    Never raises — returns [] on any failure.
    """
    results = _search_semantic_scholar(query, limit)
    if not results:
        results = _search_openalex(query, limit)
    return results


def _search_semantic_scholar(query: str, limit: int) -> list[dict]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,openAccessPdf",
    }
    headers = {}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        papers = []
        for item in data.get("data", []):
            pdf_url = None
            if item.get("openAccessPdf"):
                pdf_url = item["openAccessPdf"].get("url")
            papers.append({
                "title": item.get("title") or "Untitled",
                "authors": ", ".join(a.get("name", "") for a in (item.get("authors") or [])),
                "year": item.get("year"),
                "abstract": item.get("abstract") or "",
                "pdf_url": pdf_url,
                "source": "semantic_scholar",
            })
        return papers
    except Exception:
        return []


def _search_openalex(query: str, limit: int) -> list[dict]:
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": limit,
        "select": "title,authorships,publication_year,abstract_inverted_index,primary_location",
    }
    email = os.getenv("OPENALEX_EMAIL")
    if email:
        params["mailto"] = email

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        papers = []
        for item in data.get("results", []):
            abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
            pdf_url = None
            primary = item.get("primary_location") or {}
            if primary.get("pdf_url"):
                pdf_url = primary["pdf_url"]
            authors = ", ".join(
                a.get("author", {}).get("display_name", "")
                for a in (item.get("authorships") or [])[:5]
            )
            papers.append({
                "title": item.get("title") or "Untitled",
                "authors": authors,
                "year": item.get("publication_year"),
                "abstract": abstract,
                "pdf_url": pdf_url,
                "source": "openalex",
            })
        return papers
    except Exception:
        return []


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruct abstract from OpenAlex inverted index {word: [positions]}."""
    if not inverted_index:
        return ""
    try:
        positions = {}
        for word, pos_list in inverted_index.items():
            for pos in pos_list:
                positions[pos] = word
        return " ".join(positions[i] for i in sorted(positions.keys()))
    except Exception:
        return ""
