# extractors/__init__.py
from typing import List, Dict
from . import greenhouse, lever
from .html_generic import fetch as fetch_html
from .playwright_generic import fetch as fetch_play

def fetch_one(target: Dict) -> List[Dict]:
    source = target["source"]
    if source == "greenhouse":
        jobs = greenhouse.fetch(target["slug"])
        for j in jobs:
            j["company"] = target.get("company") or target["slug"]
        return jobs
    if source == "lever":
        jobs = lever.fetch(target["slug"])
        for j in jobs:
            j["company"] = target.get("company") or target["slug"]
        return jobs
    if source == "html":
        jobs = fetch_html(target["url"], target["selectors"])
        for j in jobs:
            j["company"] = target.get("company")
        return jobs
    if source == "playwright":
        jobs = fetch_play(target["url"], target["wait_for"], target["selectors"])
        for j in jobs:
            j["company"] = target.get("company")
        return jobs
    raise ValueError(f"Fuente no soportada: {source}")
