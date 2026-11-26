import logging
import re
from datetime import datetime, timezone

import httpx
from urllib.parse import urlparse

from app.celery_app import app
from app.exceptions import TemporaryError
from app.rate_limit import wait_for_slot

logger = logging.getLogger(__name__)

TRANSIENT_HTTP_STATUSES = {500, 502, 503, 504}
RETRYABLE_NETWORK_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError
)
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)
USER_AGENT = 'ScraperService/1.0 (+https://example.local)'


def _parse_retry_after(response: httpx.Response, default: int = 60) -> int:
    """Парсит Retry-After (в секундах). Игнорирует HTTP-date формат - нам хватит."""
    raw = response.headers.get('retry-after')
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


@app.task(
    bind=True,
    autoretry_for=RETRYABLE_NETWORK_ERRORS + (TemporaryError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5
)
def scrape_url(self, url: str) -> dict:
    """Боевая задача с pre-domain rate limit через Redis."""
    logger.info('scrape: fetching %s', url)
    domain = (urlparse(url).hostname or '').lower()
    if domain.startswith('www.'):
        domain = domain[4:]

    wait_for_slot(domain, min_interval=2.0)
    logger.info(
        'scrape: fetching %s (attempt %d/%d)',
        url, self.request.retries + 1, self.max_retries + 1,
    )
    started_at = datetime.now(timezone.utc)

    try:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={'User-Agent': USER_AGENT},
        ) as client:
            response = client.get(url)
    except RETRYABLE_NETWORK_ERRORS:
        raise
    except httpx.HTTPError as exc:
        logger.warning('scrape: non-retryable network error for %s: %s', url, exc)
        return {
            'url': url,
            'error': f'{type(exc).__name__}: {exc}',
            'fetched_at': started_at.isoformat(),
        }

    if response.status_code == 429:
        retry_after = _parse_retry_after(response, default=60)
        logger.warning('scrape: 429 for %s, honoring Retry-After=%ds', url, retry_after)
        raise self.retry(countdown=retry_after)

    if response.status_code in TRANSIENT_HTTP_STATUSES:
        raise TemporaryError(f'HTTP {response.status_code} for {url}')

    if response.status_code >= 400:
        logger.warning(f'scraper: %s ->%d (not retrying)', url, response.status_code)
        return {
            'url': str(response.url),
            'status_code': response.status_code,
            'ok': False,
            'error': f'HTTP {response.status_code}',
            'fetched_at': started_at.isoformat(),
        }

    elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    title: str | None = None
    if 'html' in response.headers.get('content-type', '').lower():
        match = TITLE_RE.search(response.text)
        if match:
            title = match.group(1).strip()

    logger.info(
        'scrape: %s -> %s (title=%r, %dms)',
        url, response.status_code, title, elapsed_ms,
    )

    return {
        'url': str(response.url),
        'status_code': response.status_code,
        'ok': response.status_code < 400,
        'title': title,
        'content_type': response.headers.get('content-type'),
        'elapsed_ms': elapsed_ms,
        'fetched_at': started_at.isoformat(),
    }
