# extractors/indeed_api.py
from typing import List, Dict
import requests
import time
import random
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

def fetch_indeed_jobs(query: str = "airline pilot", location: str = "", limit: int = 50) -> List[Dict]:
    """
    Fetch jobs from Indeed using their public job search
    Note: This uses web scraping as Indeed doesn't have a free public API
    """

    # Build search URL
    params = {
        'q': query,
        'l': location,
        'limit': limit,
        'sort': 'date'
    }

    base_url = "https://www.indeed.com/jobs"
    url = f"{base_url}?{urlencode(params)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        logger.info(f"Fetching Indeed jobs: {query} in {location or 'anywhere'}")

        # Add longer random delay for Indeed to avoid rate limiting
        time.sleep(random.uniform(5, 10))

        # Use more stealthy headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }

        # Try multiple variations if first attempt fails
        urls_to_try = [
            f"{base_url}?{urlencode(params)}",
            f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l={location}",
            f"https://www.indeed.com/jobs?q=pilot&l={location}"
        ]

        response = None
        for url_attempt in urls_to_try:
            try:
                response = requests.get(url_attempt, headers=headers, timeout=30, verify=False)
                if response.status_code == 200:
                    break
                else:
                    logger.warning(f"Indeed returned status {response.status_code}, trying next URL")
                    time.sleep(random.uniform(3, 6))
            except:
                continue

        if not response or response.status_code != 200:
            logger.warning(f"All Indeed URL attempts failed, using fallback")
            # Return empty list instead of raising exception
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find job cards - Indeed uses multiple selectors
        job_cards = soup.select('.job_seen_beacon, [data-jk], .result')

        jobs = []
        for card in job_cards[:limit]:  # Limit results
            try:
                # Extract job title
                title_elem = card.select_one('.jobTitle a, h2 a, .jobTitle span')
                title = title_elem.get_text(strip=True) if title_elem else None

                # Extract company
                company_elem = card.select_one('.companyName, [data-testid="company-name"]')
                company = company_elem.get_text(strip=True) if company_elem else None

                # Extract location
                location_elem = card.select_one('.companyLocation, [data-testid="job-location"]')
                job_location = location_elem.get_text(strip=True) if location_elem else None

                # Extract URL
                link_elem = card.select_one('.jobTitle a, h2 a')
                job_url = None
                if link_elem and link_elem.get('href'):
                    job_url = f"https://www.indeed.com{link_elem.get('href')}"

                # Extract snippet/description
                snippet_elem = card.select_one('.summary, [data-testid="job-snippet"]')
                description = snippet_elem.get_text(strip=True) if snippet_elem else ""

                # Extract job key for unique ID
                job_key = card.get('data-jk') or card.get('data-empn', '')
                if not job_key and job_url:
                    # Extract from URL
                    import re
                    match = re.search(r'jk=([^&]+)', job_url)
                    job_key = match.group(1) if match else job_url

                if title and job_key:
                    job_data = {
                        "source": "indeed",
                        "company": company,
                        "external_id": job_key,
                        "title": title,
                        "location": job_location,
                        "url": job_url,
                        "department": None,
                        "remote": None,
                        "posted_at": None,
                        "updated_at": None,
                        "description": description[:500] if description else "",
                    }
                    jobs.append(job_data)

            except Exception as e:
                logger.debug(f"Failed to parse Indeed job card: {e}")
                continue

        logger.info(f"Successfully extracted {len(jobs)} jobs from Indeed")
        return jobs

    except Exception as e:
        logger.error(f"Failed to fetch Indeed jobs: {e}")
        return []

def fetch(config: Dict) -> List[Dict]:
    """Wrapper function to match extractor interface"""
    query = config.get('query', 'airline pilot')
    location = config.get('location', '')
    limit = config.get('limit', 50)

    return fetch_indeed_jobs(query, location, limit)