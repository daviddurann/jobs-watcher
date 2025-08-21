# extractors/__init__.py
from typing import List, Dict
from . import greenhouse, lever
from .html_generic import fetch as fetch_html
from .playwright_generic import fetch as fetch_play
from .workday import fetch as fetch_workday
from .json_api import fetch as fetch_json_api
from .indeed_api import fetch as fetch_indeed
from .aviation_jobs import fetch as fetch_aviation_jobs
from .dynamic_sites import fetch_dynamic_jobs

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

    elif source == "dynamic":
        # New dynamic extractor for JavaScript-heavy sites
        config = {
            'company': target.get('company'),
            'wait_for': target.get('wait_for', ''),
            'selectors': target.get('selectors', {})
        }
        jobs = fetch_dynamic_jobs(target["url"], config)
        for j in jobs:
            j["company"] = j.get("company") or target.get("company")

    elif source == "workday":
        jobs = fetch_workday(target["url"])
        for j in jobs:
            j["company"] = target.get("company")

    elif source == "json_api":
        jobs = fetch_json_api(target["url"], target.get("params"))
        for j in jobs:
            j["company"] = target.get("company")

    elif source == "indeed":
        config = {
            'query': target.get('query', 'airline pilot'),
            'location': target.get('location', ''),
            'limit': target.get('limit', 50)
        }
        jobs = fetch_indeed(config)
        for j in jobs:
            j["company"] = j.get("company") or target.get("company")

    elif source == "aviation_jobs":
        config = {
            'source_type': target.get('source_type', 'all')
        }
        jobs = fetch_aviation_jobs(config)
        for j in jobs:
            j["company"] = j.get("company") or target.get("company")

    else:
        raise ValueError(f"Fuente no soportada: {source}")

    # Add pilot relevance scores
    jobs = [add_pilot_score(job) for job in jobs]

    return jobs
