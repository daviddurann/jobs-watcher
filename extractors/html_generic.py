# extractors/html_generic.py
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random
import logging

logger = logging.getLogger(__name__)

# Rotating User Agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def get_random_headers():
    """Get random headers to avoid detection"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }

def fetch(url: str, selectors: Dict) -> List[Dict]:
    """Enhanced HTML fetcher with better error handling and anti-bot measures"""

    max_retries = 3
    backoff_factor = 2

    for attempt in range(max_retries):
        try:
            # Random delay to appear more human-like
            if attempt > 0:
                delay = backoff_factor ** attempt + random.uniform(0.5, 2.0)
                logger.info(f"  Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                time.sleep(random.uniform(1, 3))

            headers = get_random_headers()

            logger.debug(f"  Requesting: {url}")
            response = requests.get(
                url,
                timeout=45,  # Increased timeout
                headers=headers,
                allow_redirects=True,
                verify=False  # Disable SSL verification for sites with cert issues
            )

            # Check for common anti-bot responses
            if response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"  Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            elif response.status_code == 503:  # Service unavailable
                logger.warning(f"  Service unavailable, retrying...")
                continue

            elif response.status_code in [403, 406]:  # Forbidden/Not acceptable
                logger.warning(f"  Access denied ({response.status_code}), trying different approach...")
                # Try with minimal headers
                minimal_headers = {"User-Agent": random.choice(USER_AGENTS)}
                response = requests.get(url, timeout=45, headers=minimal_headers, verify=False)

            response.raise_for_status()
            break

        except requests.exceptions.Timeout:
            logger.warning(f"  Timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise Exception(f"Timeout after {max_retries} attempts")

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"  Connection error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise Exception(f"Connection failed after {max_retries} attempts: {e}")

        except requests.exceptions.HTTPError as e:
            if response.status_code in [404, 410]:  # Not found/Gone
                raise Exception(f"Page not found: {response.status_code}")
            elif response.status_code in [403, 406]:
                if attempt == max_retries - 1:
                    raise Exception(f"Access denied: {response.status_code}")
            else:
                raise Exception(f"HTTP error: {response.status_code} - {e}")

    # Parse the HTML
    try:
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        raise Exception(f"Failed to parse HTML: {e}")

    # Extract job items using selector
    try:
        items = soup.select(selectors["item"])
        logger.debug(f"  Found {len(items)} job items with selector '{selectors['item']}'")
    except Exception as e:
        raise Exception(f"Failed to find items with selector '{selectors['item']}': {e}")

    if not items:
        # Try alternative selectors if no items found
        alternative_selectors = [
            ".job-listing", ".job-item", ".job-card", ".position", ".vacancy",
            "[data-job]", ".career-item", ".opportunity", ".job-result",
            ".search-result-item"
        ]

        for alt_selector in alternative_selectors:
            try:
                items = soup.select(alt_selector)
                if items:
                    logger.info(f"  Found {len(items)} items with alternative selector '{alt_selector}'")
                    break
            except:
                continue

    out = []
    failed_extractions = 0

    for idx, el in enumerate(items):
        try:
            # Extract title
            title = None
            if selectors.get("title"):
                title_el = el.select_one(selectors.get("title"))
                if title_el:
                    title = title_el.get_text(strip=True)

            # If no title, use the text of the main element
            if not title:
                title = el.get_text(strip=True)
                # Clean up title - take first line or limit length
                if title:
                    title = title.split('\n')[0].strip()[:200]

            if not title:
                continue  # Skip if no title found

            # Extract location
            location = None
            if selectors.get("location"):
                location_el = el.select_one(selectors.get("location", ""))
                if location_el:
                    location = location_el.get_text(strip=True)

            # Extract description
            description = ""
            if selectors.get("description"):
                description_el = el.select_one(selectors.get("description", ""))
                if description_el:
                    description = description_el.get_text(strip=True)[:1000]  # Limit length

            # Extract department
            department = None
            if selectors.get("department"):
                department_el = el.select_one(selectors.get("department", ""))
                if department_el:
                    department = department_el.get_text(strip=True)

            # Extract URL - enhanced logic
            href = None
            url_sel = selectors.get("url", "")

            if url_sel and "::attr(" in url_sel:
                # Format "a::attr(href)"
                css, _, attr = url_sel.partition("::attr(")
                attr = attr.rstrip(")")
                link_el = el if css == "" else el.select_one(css)
                if link_el:
                    href = link_el.get(attr)
            elif url_sel:
                link_el = el.select_one(url_sel)
                if link_el:
                    href = link_el.get("href")
            else:
                # Try to find any link in the element
                link_el = el.select_one("a[href]")
                if link_el:
                    href = link_el.get("href")

            # Build complete URL
            job_url = urljoin(url, href) if href else url

            # Use URL as external_id with fallback
            external_id = job_url or f"{url}#{idx}"

            job_data = {
                "source": "html",
                "company": None,
                "external_id": external_id,
                "title": title,
                "location": location,
                "url": job_url,
                "department": department,
                "remote": None,
                "posted_at": None,
                "updated_at": None,
                "description": description,
            }

            out.append(job_data)

        except Exception as e:
            failed_extractions += 1
            logger.debug(f"  Failed to extract job {idx}: {e}")
            continue

    if failed_extractions > 0:
        logger.warning(f"  Failed to extract {failed_extractions} out of {len(items)} job items")

    logger.debug(f"  Successfully extracted {len(out)} jobs")
    return out
