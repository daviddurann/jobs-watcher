# extractors/aviation_jobs.py
from typing import List, Dict
import requests
import time
import random
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def fetch_jsfirm_jobs() -> List[Dict]:
    """Fetch pilot jobs from JSFirm.com aviation job board"""

    url = "https://www.jsfirm.com/FirmJobs?srchJobCategory=pilot"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.jsfirm.com/'
    }

    try:
        logger.info("Fetching jobs from JSFirm.com")
        time.sleep(random.uniform(2, 4))

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # JSFirm specific selectors
        job_cards = soup.select('.FirmJobListing, .job-listing, tr[bgcolor]')

        jobs = []
        for idx, card in enumerate(job_cards):
            try:
                # Extract title
                title_elem = card.select_one('a[href*="FirmJobPost"], .job-title, td a')
                title = title_elem.get_text(strip=True) if title_elem else None

                # Extract company
                company_elem = card.select_one('.company, .employer, td:nth-child(2)')
                company = company_elem.get_text(strip=True) if company_elem else None

                # Extract location
                location_elem = card.select_one('.location, td:nth-child(3)')
                location = location_elem.get_text(strip=True) if location_elem else None

                # Extract URL
                job_url = None
                if title_elem and title_elem.get('href'):
                    job_url = urljoin(url, title_elem.get('href'))

                # Create unique ID
                external_id = job_url or f"jsfirm_{idx}"

                if title:
                    job_data = {
                        "source": "jsfirm",
                        "company": company or "JSFirm Aviation",
                        "external_id": external_id,
                        "title": title,
                        "location": location,
                        "url": job_url,
                        "department": "Aviation",
                        "remote": None,
                        "posted_at": None,
                        "updated_at": None,
                        "description": "",
                    }
                    jobs.append(job_data)

            except Exception as e:
                logger.debug(f"Failed to parse JSFirm job card {idx}: {e}")
                continue

        logger.info(f"Successfully extracted {len(jobs)} jobs from JSFirm")
        return jobs

    except Exception as e:
        logger.error(f"Failed to fetch JSFirm jobs: {e}")
        return []

def fetch_avcrew_jobs() -> List[Dict]:
    """Fetch pilot jobs from AvCrew.com aviation careers site"""

    url = "https://www.avcrew.com/pilot-jobs"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    try:
        logger.info("Fetching jobs from AvCrew.com")
        time.sleep(random.uniform(2, 4))

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # AvCrew specific selectors
        job_cards = soup.select('.job-posting, .job-item, .pilot-job')

        jobs = []
        for idx, card in enumerate(job_cards):
            try:
                # Extract title
                title_elem = card.select_one('h3, .job-title, .title')
                title = title_elem.get_text(strip=True) if title_elem else None

                # Extract company
                company_elem = card.select_one('.company, .employer')
                company = company_elem.get_text(strip=True) if company_elem else None

                # Extract location
                location_elem = card.select_one('.location')
                location = location_elem.get_text(strip=True) if location_elem else None

                # Extract URL
                job_url = None
                link_elem = card.select_one('a')
                if link_elem and link_elem.get('href'):
                    job_url = urljoin(url, link_elem.get('href'))

                # Create unique ID
                external_id = job_url or f"avcrew_{idx}"

                if title:
                    job_data = {
                        "source": "avcrew",
                        "company": company or "AvCrew Aviation",
                        "external_id": external_id,
                        "title": title,
                        "location": location,
                        "url": job_url,
                        "department": "Aviation",
                        "remote": None,
                        "posted_at": None,
                        "updated_at": None,
                        "description": "",
                    }
                    jobs.append(job_data)

            except Exception as e:
                logger.debug(f"Failed to parse AvCrew job card {idx}: {e}")
                continue

        logger.info(f"Successfully extracted {len(jobs)} jobs from AvCrew")
        return jobs

    except Exception as e:
        logger.error(f"Failed to fetch AvCrew jobs: {e}")
        return []

def fetch(config: Dict) -> List[Dict]:
    """Fetch jobs from multiple aviation job boards"""
    all_jobs = []

    source_type = config.get('source_type', 'all')

    if source_type in ['all', 'jsfirm']:
        all_jobs.extend(fetch_jsfirm_jobs())

    if source_type in ['all', 'avcrew']:
        all_jobs.extend(fetch_avcrew_jobs())

    return all_jobs