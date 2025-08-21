# extractors/lever.py
from typing import List, Dict
import requests
from dateutil import parser

def fetch(company_slug: str) -> List[Dict]:
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for j in data:
        external_id = j.get("id")
        title = j.get("text")
        job_url = j.get("hostedUrl") or j.get("applyUrl")
        location = None
        if j.get("categories") and j["categories"].get("location"):
            location = j["categories"]["location"]
        department = j.get("categories", {}).get("team")
        posted_at = j.get("createdAt")
        updated_at = j.get("updatedAt")
        remote = None
        if j.get("workplaceType"):
            remote = 1 if str(j["workplaceType"]).lower() in ("remote","hybrid") else 0
        out.append({
            "source": "lever",
            "company": company_slug,
            "external_id": external_id,
            "title": title,
            "location": location,
            "url": job_url,
            "department": department,
            "remote": remote,
            "posted_at": parser.parse(str(posted_at)).isoformat() if posted_at else None,
            "updated_at": parser.parse(str(updated_at)).isoformat() if updated_at else None,
        })
    return out
