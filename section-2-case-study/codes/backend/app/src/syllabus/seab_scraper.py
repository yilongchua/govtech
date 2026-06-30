from __future__ import annotations

from urllib.parse import unquote, urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


def resolve_seab_syllabus_pdf(source_url: str) -> tuple[str, str | None, str]:
    """Resolve a SEAB syllabus page/text-fragment URL or direct PDF URL to a PDF URL."""
    parsed = urlparse(source_url)
    if parsed.netloc and not _is_allowed_syllabus_host(parsed.netloc):
        raise ValueError("Only SEAB syllabus pages and SEAB-hosted syllabus PDFs are supported.")

    page_url, fragment = urldefrag(source_url)
    if page_url.lower().endswith(".pdf"):
        return page_url, None, page_url

    text_fragment = _extract_text_fragment(fragment)
    response = httpx.get(page_url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    if text_fragment:
        pdf_url = _find_pdf_near_text(soup, page_url, text_fragment)
        if pdf_url:
            return pdf_url, text_fragment, page_url

    pdf_links = _pdf_links(soup, page_url)
    if len(pdf_links) == 1:
        return pdf_links[0], text_fragment, page_url
    if text_fragment:
        raise ValueError(f"Could not find a syllabus PDF near '{text_fragment}'.")
    raise ValueError("Provide a SEAB URL with a text fragment, or a direct syllabus PDF URL.")


def _extract_text_fragment(fragment: str) -> str | None:
    marker = ":~:text="
    if marker not in fragment:
        return None
    text = fragment.split(marker, 1)[1].split("&", 1)[0]
    return " ".join(unquote(text).replace("%20", " ").split())


def _find_pdf_near_text(soup: BeautifulSoup, page_url: str, target_text: str) -> str | None:
    target = _normalise_text(target_text)
    for node in soup.find_all(string=True):
        if target not in _normalise_text(str(node)):
            continue
        for parent in [node.parent, *list(node.parents)]:
            if parent is None:
                continue
            if parent.name == "a" and parent.get("href") and _is_pdf(parent["href"]):
                return urljoin(page_url, parent["href"])
            link = parent.find("a", href=lambda href: bool(href and _is_pdf(href)))
            if link:
                return urljoin(page_url, link["href"])
    return None


def _pdf_links(soup: BeautifulSoup, page_url: str) -> list[str]:
    return [urljoin(page_url, link["href"]) for link in soup.find_all("a", href=True) if _is_pdf(link["href"])]


def _is_pdf(href: str) -> bool:
    return urlparse(href).path.lower().endswith(".pdf")


def _normalise_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _is_allowed_syllabus_host(host: str) -> bool:
    host = host.lower()
    return host.endswith("seab.gov.sg") or host == "isomer-user-content.by.gov.sg"
