# extractors/html_generic.py
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def fetch(url: str, selectors: Dict) -> List[Dict]:
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Usar el selector de items
    items = soup.select(selectors["item"])
    out = []

    for el in items:
        # Extraer título
        title = None
        if selectors.get("title"):
            title_el = el.select_one(selectors.get("title"))
            if title_el:
                title = title_el.get_text(strip=True)

        # Si no hay título, usar el texto del elemento principal
        if not title:
            title = el.get_text(strip=True)

        # Extraer ubicación
        location = None
        if selectors.get("location"):
            location_el = el.select_one(selectors.get("location", ""))
            if location_el:
                location = location_el.get_text(strip=True)

        # Extraer descripción
        description = ""
        if selectors.get("description"):
            description_el = el.select_one(selectors.get("description", ""))
            if description_el:
                description = description_el.get_text(strip=True)

        # Extraer departamento
        department = None
        if selectors.get("department"):
            department_el = el.select_one(selectors.get("department", ""))
            if department_el:
                department = department_el.get_text(strip=True)

        # Extraer URL
        href = None
        url_sel = selectors.get("url")
        if url_sel and "::attr(" in url_sel:
            # formato "a::attr(href)"
            css, _, attr = url_sel.partition("::attr(")
            attr = attr.rstrip(")")
            link_el = el if css == "" else el.select_one(css)
            if link_el:
                href = link_el.get(attr)
        else:
            link_el = el.select_one(url_sel) if url_sel else el
            if link_el:
                href = link_el.get("href")

        # Construir URL completa
        job_url = urljoin(url, href) if href else url

        # Usar URL como external_id si no hay ID propio
        external_id = job_url

        out.append({
            "source": "html",
            "company": None,
            "external_id": external_id,
            "title": title,
            "location": location,
            "url": job_url,
            "department": department,
            "remote": None,
            "posted_at": None,
            "updated_at": None,
            "description": description,
        })
    return out
