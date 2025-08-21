# job_filter.py
import re
from typing import List, Dict

# Keywords that indicate pilot positions
PILOT_KEYWORDS = [
    'pilot',
    'copilot',
    'co-pilot',
    'first officer',
    'pilot cadet',
    'second officer',
    'captain',
    'flight officer',
    'airline pilot',
    'commercial pilot',
    'airline transport pilot',
    'atp',
    'atpl'
]

def is_pilot_job(job: Dict) -> bool:
    """
    Check if a job posting is for a pilot position based on title and description.
    """
    title = (job.get('title') or '').lower()
    description = (job.get('description') or '').lower()
    department = (job.get('department') or '').lower()

    # Combine all text fields for searching
    text_to_search = f"{title} {description} {department}"

    # Check if any pilot keyword appears in the text
    for keyword in PILOT_KEYWORDS:
        if keyword in text_to_search:
            return True

    return False

def filter_pilot_jobs(jobs: List[Dict]) -> List[Dict]:
    """
    Filter a list of jobs to return only pilot-related positions.
    """
    pilot_jobs = []
    for job in jobs:
        if is_pilot_job(job):
            pilot_jobs.append(job)

    return pilot_jobs

def add_pilot_score(job: Dict) -> Dict:
    """
    Add a pilot_score field to indicate how relevant the job is to pilot positions.
    Score ranges from 0 (not pilot related) to 10 (definitely pilot related).
    """
    title = (job.get('title') or '').lower()
    description = (job.get('description') or '').lower()
    department = (job.get('department') or '').lower()

    score = 0
    text_to_search = f"{title} {description} {department}"

    # High priority keywords (worth more points)
    high_priority = ['pilot', 'captain', 'first officer', 'copilot', 'co-pilot']
    for keyword in high_priority:
        if keyword in text_to_search:
            score += 3

    # Medium priority keywords
    medium_priority = ['pilot cadet', 'second officer', 'flight officer', 'airline pilot']
    for keyword in medium_priority:
        if keyword in text_to_search:
            score += 2

    # Technical keywords
    technical = ['atp', 'atpl', 'commercial pilot', 'airline transport pilot']
    for keyword in technical:
        if keyword in text_to_search:
            score += 1

    # Cap the score at 10
    job['pilot_score'] = min(score, 10)
    return job