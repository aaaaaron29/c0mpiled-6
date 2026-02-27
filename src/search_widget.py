"""Reusable Streamlit search + select widget for academic papers."""
import io
import requests
import streamlit as st
from src.paper_search import search_papers


def render_search_widget(key: str, min_select: int = 1) -> list[dict]:
    """
    Render the full search interface and return selected paper dicts.

    Returns list of {title, authors, year, abstract, pdf_url, source}.
    Returns [] if no papers have been confirmed yet.
    """
    results_key = f"{key}_results"
    confirmed_key = f"{key}_confirmed"

    # Search bar
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Search query",
            key=f"{key}_query",
            placeholder="e.g. transformer attention long sequences",
            label_visibility="collapsed",
        )
    with col2:
        search_clicked = st.button("Search", key=f"{key}_search_btn", use_container_width=True)

    if search_clicked:
        if not query.strip():
            st.warning("Enter a search query first.")
        else:
            with st.spinner(f"Searching for '{query}'..."):
                results = search_papers(query)
            if results:
                st.session_state[results_key] = results
                # Clear previous confirmation when a new search runs
                st.session_state.pop(confirmed_key, None)
            else:
                st.warning("No results found. Try a different query or check your connection.")

    results = st.session_state.get(results_key, [])
    if not results:
        st.caption("Search for papers above to get started.")
        return st.session_state.get(confirmed_key, [])

    st.markdown(f"**{len(results)} results** — select papers to use:")

    selected_indices = []
    for i, paper in enumerate(results):
        year_str = f" ({paper['year']})" if paper.get("year") else ""
        availability = " · PDF available" if paper.get("pdf_url") else " · Abstract only"
        label = f"{paper['title']}{year_str}{availability}"
        abstract = paper.get("abstract") or ""
        checked = st.checkbox(label, key=f"{key}_check_{i}")
        if checked:
            selected_indices.append(i)
            if abstract:
                st.caption(f"  {abstract[:220]}{'...' if len(abstract) > 220 else ''}")

    if st.button("Use Selected Papers", key=f"{key}_confirm_btn", type="primary", use_container_width=True):
        if len(selected_indices) < min_select:
            st.warning(f"Please select at least {min_select} paper(s).")
        else:
            confirmed = [results[i] for i in selected_indices]
            st.session_state[confirmed_key] = confirmed
            st.success(f"{len(confirmed)} paper(s) ready.")

    return st.session_state.get(confirmed_key, [])


def search_results_to_papers(selected: list[dict]) -> list[dict]:
    """
    Convert selected search result dicts to the same format as ingest_paper().
    Downloads PDF where available; falls back to abstract text.
    """
    from src.paper_ingestion import ingest_paper

    papers = []
    for item in selected:
        pdf_url = item.get("pdf_url")
        if pdf_url:
            try:
                resp = requests.get(pdf_url, timeout=15)
                resp.raise_for_status()
                buf = io.BytesIO(resp.content)
                buf.name = f"{item['title'][:50]}.pdf"
                paper = ingest_paper(buf)
                papers.append(paper)
                continue
            except Exception:
                pass  # Fall through to abstract fallback

        # Abstract fallback
        abstract = item.get("abstract") or ""
        note = " [Full PDF unavailable — using abstract only]" if pdf_url else ""
        papers.append({
            "title": item.get("title", "Untitled"),
            "abstract": abstract,
            "sections": {k: "" for k in ["introduction", "methods", "results", "discussion", "conclusion"]},
            "full_text": abstract + note,
            "source": "search",
        })

    return papers
