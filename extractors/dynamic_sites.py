# extractors/dynamic_sites.py
"""
Enhanced extractor for dynamic job boards like Bizneo, SuccessFactors, Oracle, etc.
Supports JavaScript-heavy sites with better anti-bot evasion.
"""

import time
import random
import logging
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext
from urllib.parse import urljoin, urlparse
import json
import re

logger = logging.getLogger(__name__)

# Enhanced user agents for better evasion
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
]

class DynamicJobExtractor:
    def __init__(self):
        self.browser = None
        self.context = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        # Launch browser with enhanced stealth settings
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--disable-extensions'
            ]
        )

        # Create context with random user agent
        self.context = self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='Europe/Madrid'  # Use Spanish timezone for Spanish sites
        )

        # Add stealth scripts to avoid detection
        self.context.add_init_script("""
            // Remove webdriver property
            delete navigator.__proto__.webdriver;
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'es-ES', 'es']
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def extract_jobs(self, url: str, config: Dict) -> List[Dict]:
        """Extract jobs from dynamic sites with enhanced detection"""
        logger.info(f"Extracting from dynamic site: {url}")

        page = self.context.new_page()

        try:
            # Navigate with realistic timing
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Random human-like delay
            time.sleep(random.uniform(2, 4))

            # Detect site type and apply specific strategies
            site_type = self._detect_site_type(page, url)
            logger.info(f"Detected site type: {site_type}")

            if site_type == 'bizneo':
                return self._extract_bizneo_jobs(page, url, config)
            elif site_type == 'workday':
                return self._extract_workday_jobs(page, url, config)
            elif site_type == 'successfactors':
                return self._extract_successfactors_jobs(page, url, config)
            else:
                return self._extract_generic_dynamic_jobs(page, url, config)

        except Exception as e:
            logger.error(f"Failed to extract from {url}: {e}")
            return []
        finally:
            page.close()

    def _detect_site_type(self, page: Page, url: str) -> str:
        """Detect the type of job board platform"""

        # Check URL patterns
        if 'bizneo.cloud' in url:
            return 'bizneo'
        elif 'myworkdayjobs.com' in url:
            return 'workday'
        elif 'successfactors' in url:
            return 'successfactors'

        # Check page content for platform indicators
        try:
            page_content = page.content()

            if 'bizneo' in page_content.lower():
                return 'bizneo'
            elif 'workday' in page_content.lower():
                return 'workday'
            elif 'successfactors' in page_content.lower():
                return 'successfactors'
            elif any(indicator in page_content.lower() for indicator in ['job-listing', 'job-card', 'career']):
                return 'generic'

        except Exception:
            pass

        return 'generic'

    def _extract_bizneo_jobs(self, page: Page, url: str, config: Dict) -> List[Dict]:
        """Extract jobs from Bizneo platform (Air Europa uses this)"""
        logger.info("Using Bizneo extraction strategy")

        jobs = []

        # Wait for jobs to load
        selectors_to_try = [
            '.job-offer',
            '.job-item',
            '.job-card',
            '[data-job-id]',
            '.position-item',
            '.career-opportunity'
        ]

        # Try different selectors
        job_elements = None
        for selector in selectors_to_try:
            try:
                page.wait_for_selector(selector, timeout=10000)
                job_elements = page.query_selector_all(selector)
                if job_elements:
                    logger.info(f"Found {len(job_elements)} jobs with selector: {selector}")
                    break
            except:
                continue

        if not job_elements:
            # Try to find any clickable job-related elements
            job_elements = page.query_selector_all('a[href*="job"], a[href*="position"], div[onclick*="job"]')
            logger.info(f"Found {len(job_elements)} potential job elements as fallback")

        for element in job_elements:
            try:
                # Extract job data
                title = self._extract_text(element, ['.job-title', 'h2', 'h3', '.title', '[data-job-title]'])
                location = self._extract_text(element, ['.job-location', '.location', '.city', '[data-location]'])
                description = self._extract_text(element, ['.job-description', '.description', '.summary'])

                # Extract URL
                job_url = self._extract_url(element, url)

                if title:  # Only add if we have at least a title
                    job = {
                        'source': 'dynamic_bizneo',
                        'company': config.get('company'),
                        'external_id': job_url or f"{url}#{len(jobs)}",
                        'title': title,
                        'location': location,
                        'url': job_url,
                        'department': None,
                        'remote': None,
                        'posted_at': None,
                        'updated_at': None,
                        'description': description,
                    }
                    jobs.append(job)

            except Exception as e:
                logger.debug(f"Failed to extract job element: {e}")
                continue

        return jobs

    def _extract_workday_jobs(self, page: Page, url: str, config: Dict) -> List[Dict]:
        """Extract jobs from Workday platform"""
        logger.info("Using Workday extraction strategy")

        jobs = []

        # Workday-specific selectors
        selectors_to_try = [
            '[data-automation-id="jobTitle"]',
            '.jobs-list-item',
            '[data-automation-id="searchResultItem"]'
        ]

        job_elements = None
        for selector in selectors_to_try:
            try:
                page.wait_for_selector(selector, timeout=10000)
                job_elements = page.query_selector_all(selector)
                if job_elements:
                    break
            except:
                continue

        if not job_elements:
            return jobs

        for element in job_elements:
            try:
                title = self._extract_text(element, ['[data-automation-id="jobTitle"] a', 'h3', '.title'])
                location = self._extract_text(element, ['[data-automation-id="locations"]', '.location'])

                # Workday URLs are usually in specific elements
                job_url = self._extract_url(element, url, ['[data-automation-id="jobTitle"] a'])

                if title:
                    job = {
                        'source': 'dynamic_workday',
                        'company': config.get('company'),
                        'external_id': job_url or f"{url}#{len(jobs)}",
                        'title': title,
                        'location': location,
                        'url': job_url,
                        'department': None,
                        'remote': None,
                        'posted_at': None,
                        'updated_at': None,
                        'description': '',
                    }
                    jobs.append(job)

            except Exception as e:
                logger.debug(f"Failed to extract Workday job: {e}")
                continue

        return jobs

    def _extract_successfactors_jobs(self, page: Page, url: str, config: Dict) -> List[Dict]:
        """Extract jobs from SuccessFactors platform"""
        logger.info("Using SuccessFactors extraction strategy")

        # SuccessFactors often loads jobs via AJAX
        # Wait for the job list to appear
        try:
            page.wait_for_selector('.job-tile, .job-item, [data-job]', timeout=15000)
        except:
            logger.warning("SuccessFactors jobs not found with standard selectors")

        return self._extract_generic_dynamic_jobs(page, url, config)

    def _extract_generic_dynamic_jobs(self, page: Page, url: str, config: Dict) -> List[Dict]:
        """Generic extraction for dynamic sites"""
        logger.info("Using generic dynamic extraction strategy")

        jobs = []

        # Comprehensive list of selectors to try
        selectors_to_try = [
            '.job-listing', '.job-item', '.job-card', '.job-offer',
            '.position', '.career-item', '.vacancy', '.opening',
            '[data-job]', '[data-job-id]', '[data-position]',
            '.search-result-item', '.job-result', '.opportunity',
            'li[role="listitem"]', '.list-item', '.result-item'
        ]

        job_elements = []

        # Try each selector
        for selector in selectors_to_try:
            try:
                elements = page.query_selector_all(selector)
                if elements and len(elements) > len(job_elements):
                    job_elements = elements
                    logger.info(f"Best match: {len(elements)} elements with selector '{selector}'")
            except:
                continue

        # If still no elements, try to find any structured content
        if not job_elements:
            # Look for repeated patterns that might be job listings
            potential_patterns = [
                'a[href*="job"]', 'a[href*="career"]', 'a[href*="position"]',
                'div[onclick*="job"]', '[class*="job"]', '[id*="job"]'
            ]

            for pattern in potential_patterns:
                elements = page.query_selector_all(pattern)
                if elements:
                    job_elements = elements[:20]  # Limit to avoid false positives
                    logger.info(f"Using pattern fallback: {len(job_elements)} elements")
                    break

        # Extract jobs from elements
        for i, element in enumerate(job_elements):
            try:
                title = self._extract_text(element, [
                    '.job-title', '.title', 'h1', 'h2', 'h3', 'h4',
                    '[data-job-title]', '[title]', '.name'
                ])

                location = self._extract_text(element, [
                    '.job-location', '.location', '.city', '.place',
                    '[data-location]', '.geo', '.address'
                ])

                description = self._extract_text(element, [
                    '.job-description', '.description', '.summary', '.snippet'
                ])

                job_url = self._extract_url(element, url)

                # Only add jobs with at least a title
                if title and len(title.strip()) > 0:
                    job = {
                        'source': 'dynamic_generic',
                        'company': config.get('company'),
                        'external_id': job_url or f"{url}#{i}",
                        'title': title.strip(),
                        'location': location.strip() if location else None,
                        'url': job_url,
                        'department': None,
                        'remote': None,
                        'posted_at': None,
                        'updated_at': None,
                        'description': description.strip() if description else '',
                    }
                    jobs.append(job)

            except Exception as e:
                logger.debug(f"Failed to extract job {i}: {e}")
                continue

        return jobs

    def _extract_text(self, element, selectors: List[str]) -> Optional[str]:
        """Extract text from element using multiple selector strategies"""
        for selector in selectors:
            try:
                if selector in ['.', '']:  # Current element
                    text = element.inner_text()
                else:
                    sub_element = element.query_selector(selector)
                    if sub_element:
                        text = sub_element.inner_text()
                    else:
                        continue

                if text and text.strip():
                    return text.strip()
            except:
                continue

        # Fallback: try to get any text from the element
        try:
            text = element.inner_text()
            if text and text.strip():
                # Clean up and take first meaningful line
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                return lines[0] if lines else None
        except:
            pass

        return None

    def _extract_url(self, element, base_url: str, selectors: List[str] = None) -> Optional[str]:
        """Extract URL from element"""
        if selectors is None:
            selectors = ['a', '[href]', '[onclick*="http"]']

        for selector in selectors:
            try:
                if selector == 'a' or selector == '[href]':
                    # Look for any link in the element
                    link_element = element.query_selector('a[href]')
                    if link_element:
                        href = link_element.get_attribute('href')
                    else:
                        href = element.get_attribute('href')
                else:
                    link_element = element.query_selector(selector)
                    if link_element:
                        href = link_element.get_attribute('href')
                    else:
                        continue

                if href:
                    # Handle relative URLs
                    if href.startswith('http'):
                        return href
                    else:
                        return urljoin(base_url, href)
            except:
                continue

        return None


def fetch_dynamic_jobs(url: str, config: Dict) -> List[Dict]:
    """Main function to fetch jobs from dynamic sites"""
    with DynamicJobExtractor() as extractor:
        return extractor.extract_jobs(url, config)


# Convenience function for backward compatibility
def fetch(url: str, config: Dict) -> List[Dict]:
    return fetch_dynamic_jobs(url, config)