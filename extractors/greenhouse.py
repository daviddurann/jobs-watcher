# extractors/greenhouse.py
from typing import List, Dict
import requests
from dateutil import parser

def fetch(company_slug: str) -> List[Dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json().get("jobs", [])
    out = []
    for j in data:
        external_id = str(j.get("id"))
        title = j.get("title")
        job_url = j.get("absolute_url")
        locations = j.get("location", {}) or {}
        location = locations.get("name")
        depts = j.get("departments") or []
        department = depts[0]["name"] if depts else None
        updated_at = j.get("updated_at")
        posted_at = j.get("updated_at")  # GH no siempre da posted_at; usamos updated_at como mínimo
        out.append({
            "source": "greenhouse",
            "company": company_slug,
            "external_id": external_id,
            "title": title,
            "location": location,
            "url": job_url,
            "department": department,
            "remote": None,
            "posted_at": parser.isoparse(posted_at).isoformat() if posted_at else None,
            "updated_at": parser.isoparse(updated_at).isoformat() if updated_at else None,
        })
    return out
