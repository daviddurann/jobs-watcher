# extractors/playwright_generic.py
from typing import List, Dict
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

def fetch(url: str, wait_for: str, selectors: Dict) -> List[Dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(wait_for, timeout=30000)
        items = page.query_selector_all(selectors["item"])
        out = []
        for el in items:
            title = el.query_selector(selectors.get("title")).inner_text().strip() if selectors.get("title") else None
            location = el.query_selector(selectors.get("location")).inner_text().strip() if selectors.get("location") else None
            job_el = el.query_selector(selectors.get("url")) if selectors.get("url") else None
            href = job_el.get_attribute("href") if job_el else None
            job_url = urljoin(url, href) if href else url
            out.append({
                "source": "playwright",
                "company": None,
                "external_id": job_url,
                "title": title,
                "location": location,
                "url": job_url,
                "department": None,
                "remote": None,
                "posted_at": None,
                "updated_at": None,
            })
        browser.close()
        return out
