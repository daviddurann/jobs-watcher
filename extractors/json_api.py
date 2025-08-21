# extractors/json_api.py
from typing import List, Dict
import requests

def fetch(url: str, params: Dict = None) -> List[Dict]:
    """
    Extract jobs from direct JSON API endpoints.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Handle different JSON structures
        jobs_list = []
        if isinstance(data, list):
            jobs_list = data
        elif isinstance(data, dict):
            # Try common keys for job arrays
            for key in ['jobs', 'data', 'results', 'jobPostings', 'positions']:
                if key in data:
                    jobs_list = data[key]
                    break

        jobs = []
        for job_data in jobs_list:
            if isinstance(job_data, dict):
                job = {
                    'source': 'json_api',
                    'company': None,  # Will be set by caller
                    'external_id': (
                            job_data.get('id') or
                            job_data.get('jobId') or
                            job_data.get('requisitionId') or
                            str(job_data.get('position_id', ''))
                    ),
                    'title': (
                            job_data.get('title') or
                            job_data.get('jobTitle') or
                            job_data.get('position_title')
                    ),
                    'location': (
                            job_data.get('location') or
                            job_data.get('jobLocation') or
                            job_data.get('city')
                    ),
                    'url': (
                            job_data.get('url') or
                            job_data.get('jobUrl') or
                            job_data.get('apply_url')
                    ),
                    'department': (
                            job_data.get('department') or
                            job_data.get('category')
                    ),
                    'remote': None,
                    'posted_at': (
                            job_data.get('posted_at') or
                            job_data.get('postedDate') or
                            job_data.get('created_date')
                    ),
                    'updated_at': (
                            job_data.get('updated_at') or
                            job_data.get('updatedDate') or
                            job_data.get('modified_date')
                    ),
                    'description': (
                            job_data.get('description') or
                            job_data.get('jobDescription') or
                            job_data.get('summary', '')
                    )
                }

                jobs.append(job)

        return jobs

    except Exception as e:
        print(f"Error fetching from JSON API {url}: {e}")
        return []