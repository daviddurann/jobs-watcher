# extractors/workday.py
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import json
import re

def fetch(url: str) -> List[Dict]:
    """
    Extract jobs from Workday-based career sites.
    Workday sites typically use AJAX calls to load job data.
    """
    try:
        # First, get the main page to extract session info
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        session.headers.update(headers)

        # Get the main page first
        main_response = session.get(url, timeout=30)
        main_response.raise_for_status()

        # Try to find AJAX endpoint for jobs
        soup = BeautifulSoup(main_response.text, 'html.parser')

        # Look for JSON data in script tags
        script_tags = soup.find_all('script')
        jobs_data = []

        for script in script_tags:
            script_content = script.get_text()
            if 'jobRequisitions' in script_content or 'jobs' in script_content:
                # Try to extract JSON data
                try:
                    # Look for JSON patterns
                    json_match = re.search(r'\{.*"jobs".*\}', script_content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        if 'jobs' in data:
                            jobs_data = data['jobs']
                            break
                except:
                    continue

        # If no JSON found in scripts, try common Workday AJAX endpoints
        if not jobs_data:
            possible_endpoints = [
                f"{url}/jobs",
                f"{url.rstrip('/')}/jobSearch",
                f"{url.rstrip('/')}/search"
            ]

            for endpoint in possible_endpoints:
                try:
                    response = session.get(endpoint, timeout=30)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if isinstance(data, dict) and 'jobPostings' in data:
                                jobs_data = data['jobPostings']
                                break
                            elif isinstance(data, list):
                                jobs_data = data
                                break
                        except:
                            continue
                except:
                    continue

        # Parse the jobs data
        jobs = []
        for job_data in jobs_data:
            if isinstance(job_data, dict):
                job = {
                    'source': 'workday',
                    'company': None,  # Will be set by caller
                    'external_id': job_data.get('id') or job_data.get('jobId'),
                    'title': job_data.get('title') or job_data.get('jobTitle'),
                    'location': job_data.get('location') or job_data.get('jobLocation'),
                    'url': job_data.get('url') or job_data.get('jobUrl'),
                    'department': job_data.get('department'),
                    'remote': None,
                    'posted_at': job_data.get('postedDate'),
                    'updated_at': job_data.get('updatedDate'),
                    'description': job_data.get('description') or job_data.get('jobDescription', '')
                }

                # Build full URL if relative
                if job['url'] and not job['url'].startswith('http'):
                    base_url = url.split('/jobSearch')[0].split('/search')[0]
                    job['url'] = f"{base_url}{job['url']}"

                jobs.append(job)

        return jobs

    except Exception as e:
        print(f"Error fetching from Workday site {url}: {e}")
        return []