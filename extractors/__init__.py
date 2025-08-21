# extractors/__init__.py
from typing import List, Dict
from . import greenhouse, lever
from .html_generic import fetch as fetch_html
from .playwright_generic import fetch as fetch_play
from .workday import fetch as fetch_workday
from .json_api import fetch as fetch_json_api

# Import job filter functions
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from job_filter import filter_pilot_jobs, add_pilot_score

def fetch_one(target: Dict) -> List[Dict]:
    source = target["source"]
    jobs = []

    if source == "greenhouse":
        jobs = greenhouse.fetch(target["slug"])
        for j in jobs:
            j["company"] = target.get("company") or target["slug"]

    elif source == "lever":
        jobs = lever.fetch(target["slug"])
        for j in jobs:
            j["company"] = target.get("company") or target["slug"]

    elif source == "html":
        jobs = fetch_html(target["url"], target["selectors"])
        for j in jobs:
            j["company"] = target.get("company")

    elif source == "playwright":
        jobs = fetch_play(target["url"], target["wait_for"], target["selectors"])
        for j in jobs:
            j["company"] = target.get("company")

    elif source == "workday":
        jobs = fetch_workday(target["url"])
        for j in jobs:
            j["company"] = target.get("company")

    elif source == "json_api":
        jobs = fetch_json_api(target["url"], target.get("params"))
        for j in jobs:
            j["company"] = target.get("company")

    else:
        raise ValueError(f"Fuente no soportada: {source}")

    # Add pilot relevance scores
    jobs = [add_pilot_score(job) for job in jobs]

    return jobs
