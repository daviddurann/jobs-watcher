# extractors/html_generic.py
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def fetch(url: str, selectors: Dict) -> List[Dict]:
    r = requests.get(url, timeout=30, headers={"User-Agent": "jobs-watcher/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select(selectors["item"])
    out = []
    for el in items:
        title_el = el.select_one(selectors.get("title"))
        location_el = el.select_one(selectors.get("location",""))
        url_sel = selectors.get("url")
        href = None
        if url_sel and "::attr(" in url_sel:
            # formato "a::attr(href)"
            css, _, attr = url_sel.partition("::attr(")
            attr = attr.rstrip(")")
            link_el = el.select_one(css)
            if link_el:
                href = link_el.get(attr)
        else:
            link_el = el.select_one(url_sel) if url_sel else None
            if link_el:
                href = link_el.get("href")
        job_url = urljoin(url, href) if href else url

        title = title_el.get_text(strip=True) if title_el else None
        location = location_el.get_text(strip=True) if location_el else None
        external_id = job_url  # si no hay ID propio, usa URL como external_id

        out.append({
            "source": "html",
            "company": None,
            "external_id": external_id,
            "title": title,
            "location": location,
            "url": job_url,
            "department": None,
            "remote": None,
            "posted_at": None,
            "updated_at": None,
        })
    return out
