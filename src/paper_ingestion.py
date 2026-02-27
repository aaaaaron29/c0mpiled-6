"""PDF paper parsing with PyMuPDF."""
import re
import fitz  # PyMuPDF


SECTION_HEADERS = {
    "abstract": r"\babstract\b",
    "introduction": r"\b(?:1\.?\s*)?introduction\b",
    "methods": r"\b(?:2\.?\s*)?(?:methods?|methodology|materials?\s+and\s+methods?|experimental\s+setup)\b",
    "results": r"\b(?:3\.?\s*)?results?\b",
    "discussion": r"\b(?:4\.?\s*)?discussion\b",
    "conclusion": r"\b(?:5\.?\s*)?conclusions?\b",
    "references": r"\breferences?\b",
}


def ingest_paper(uploaded_file) -> dict:
    """
    Parse a PDF and return structured content.

    Returns:
        {
            "title": str,
            "abstract": str,
            "sections": {"introduction": str, "methods": str, "results": str, "discussion": str, "conclusion": str},
            "full_text": str,
            "source": "pdf_upload"
        }
    """
    try:
        raw_bytes = uploaded_file.read()
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            try:
                pages_text.append(page.get_text())
            except Exception:
                pages_text.append("")
        doc.close()

        full_text = "\n".join(pages_text).strip()
    except Exception as e:
        # Graceful fallback for bad PDFs
        name = getattr(uploaded_file, "name", "unknown.pdf")
        return {
            "title": name.replace(".pdf", ""),
            "abstract": "",
            "sections": {k: "" for k in ["introduction", "methods", "results", "discussion", "conclusion"]},
            "full_text": f"[PDF extraction failed: {str(e)}]",
            "source": "pdf_upload",
        }

    # Extract title: first meaningful non-empty line
    title = _extract_title(full_text, getattr(uploaded_file, "name", "unknown.pdf"))

    # Split into sections
    sections = _split_sections(full_text)

    return {
        "title": title,
        "abstract": sections.get("abstract", ""),
        "sections": {
            "introduction": sections.get("introduction", ""),
            "methods": sections.get("methods", ""),
            "results": sections.get("results", ""),
            "discussion": sections.get("discussion", ""),
            "conclusion": sections.get("conclusion", ""),
        },
        "full_text": full_text,
        "source": "pdf_upload",
    }


def _extract_title(text: str, filename: str) -> str:
    lines = text.split("\n")
    for line in lines[:20]:
        stripped = line.strip()
        if len(stripped) > 10 and len(stripped) < 200 and not stripped.lower().startswith("abstract"):
            return stripped
    return filename.replace(".pdf", "")


def _split_sections(text: str) -> dict:
    """Split text into sections by header detection."""
    sections = {}
    lower_text = text.lower()

    # Find positions of all section headers
    found = {}
    for section, pattern in SECTION_HEADERS.items():
        for m in re.finditer(pattern, lower_text, re.IGNORECASE | re.MULTILINE):
            # Only consider matches near line starts
            start = m.start()
            line_start = text.rfind("\n", 0, start)
            prefix = text[line_start:start].strip()
            if len(prefix) < 10:  # Close to line start
                if section not in found or found[section] > start:
                    found[section] = start
                break

    # Sort by position
    sorted_sections = sorted(found.items(), key=lambda x: x[1])

    # Extract text between section boundaries
    for i, (section, start_pos) in enumerate(sorted_sections):
        end_pos = sorted_sections[i + 1][1] if i + 1 < len(sorted_sections) else len(text)
        # Skip the header line itself
        section_text = text[start_pos:end_pos]
        lines = section_text.split("\n")
        content = "\n".join(lines[1:]).strip()
        sections[section] = content

    return sections


def truncate_paper(paper: dict, max_chars: int = 3000) -> str:
    """Return a truncated summary string for LLM consumption."""
    parts = []
    if paper.get("abstract"):
        parts.append(f"Abstract: {paper['abstract'][:500]}")
    for sec in ["introduction", "methods", "results", "conclusion"]:
        content = paper.get("sections", {}).get(sec, "")
        if content:
            parts.append(f"{sec.title()}: {content[:400]}")
    combined = "\n\n".join(parts)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "..."
    if not combined.strip():
        combined = paper.get("full_text", "")[:max_chars]
    return combined
