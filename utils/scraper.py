import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Site-specific extractors
# ---------------------------------------------------------------------------

def _extract_linkedin(soup: BeautifulSoup) -> Optional[str]:
    """Extract job description from LinkedIn job posting."""
    selectors = [
        'div.description__text',
        'div.show-more-less-html__markup',
        'section.description',
        '[class*="description"]',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 100:
            return el.get_text(separator='\n', strip=True)
    return None


def _extract_indeed(soup: BeautifulSoup) -> Optional[str]:
    """Extract job description from Indeed job posting."""
    selectors = [
        'div#jobDescriptionText',
        'div.jobsearch-jobDescriptionText',
        '[class*="jobDescription"]',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 100:
            return el.get_text(separator='\n', strip=True)
    return None


def _extract_naukri(soup: BeautifulSoup) -> Optional[str]:
    """Extract job description from Naukri job posting."""
    selectors = [
        'div.job-desc',
        'div.dang-inner-html',
        'section.job-desc-cont',
        '[class*="job-desc"]',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 100:
            return el.get_text(separator='\n', strip=True)
    return None


def _extract_generic(soup: BeautifulSoup) -> Optional[str]:
    """
    Generic extractor — tries common job description patterns.
    Works on most job boards.
    """
    # Try common class/id patterns
    candidates = [
        'job-description', 'jobDescription', 'job_description',
        'description', 'job-details', 'jobDetails', 'posting-description',
        'job-posting', 'vacancy-description', 'position-description',
    ]
    for candidate in candidates:
        el = soup.find(id=re.compile(candidate, re.I)) or \
             soup.find(class_=re.compile(candidate, re.I))
        if el and len(el.get_text(strip=True)) > 150:
            return el.get_text(separator='\n', strip=True)

    # Fallback: find the longest <div> or <section> with substantial text
    best_text = ''
    for tag in soup.find_all(['div', 'section', 'article']):
        text = tag.get_text(separator='\n', strip=True)
        if 200 < len(text) < 8000 and len(text) > len(best_text):
            best_text = text

    return best_text if len(best_text) > 200 else None


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Remove excessive whitespace and boilerplate from scraped text."""
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove very short lines (nav items, buttons etc)
    lines = [l for l in text.split('\n') if len(l.strip()) > 3 or l.strip() == '']
    text = '\n'.join(lines)
    # Trim
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_job_description(url: str) -> dict:
    """
    Fetch a job posting URL and extract the job description text.

    Args:
        url: Full URL of the job posting.

    Returns:
        dict with keys:
            - success (bool)
            - job_description (str) — extracted text
            - source (str) — detected site name
            - error (str) — only present on failure
    """
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Detect site
    source = 'generic'
    if 'linkedin.com' in url:
        source = 'linkedin'
    elif 'indeed.com' in url:
        source = 'indeed'
    elif 'naukri.com' in url:
        source = 'naukri'

    logger.info("Scraping %s (%s)", url, source)

    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Request timed out. The job site took too long to respond.'}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return {'success': False, 'error': 'Access denied (403). This site blocks scrapers. Try copying the job description manually.'}
        if e.response.status_code == 404:
            return {'success': False, 'error': 'Job posting not found (404). The link may have expired.'}
        return {'success': False, 'error': f'HTTP error: {e}'}
    except Exception as e:
        return {'success': False, 'error': f'Could not fetch URL: {str(e)}'}

    soup = BeautifulSoup(response.text, 'lxml')

    # Remove script/style/nav noise
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
        tag.decompose()

    # Try site-specific extractor first, then generic
    extractors = {
        'linkedin': _extract_linkedin,
        'indeed':   _extract_indeed,
        'naukri':   _extract_naukri,
    }
    text = None
    if source in extractors:
        text = extractors[source](soup)

    if not text:
        text = _extract_generic(soup)

    if not text or len(text) < 100:
        return {
            'success': False,
            'error': (
                'Could not extract job description from this page. '
                'The site may require login or use JavaScript rendering. '
                'Try copying the job description manually.'
            )
        }

    return {
        'success': True,
        'job_description': _clean(text)[:5000],  # cap at 5000 chars
        'source': source,
    }