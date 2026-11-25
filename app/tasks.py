import logging
import re
from datetime import datetime, timezone

import httpx

from app.celery_app import app


logger = logging.getLogger(__name__)

TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)

USER_AGENT = 'ScraperService/1.0 (+https://example.local)'


@app.task
def scrape_url(url: str) -> dict:
    """
    Реально идёт в интернет и достаёт <title>.
    Ошибки сети/таймаута не валят задачу — возвращаем {'error': ...}.
    Ретраи сюда добавим на шаге 5.
    """
    logger.info('scrape_url: fetching %s', url)
    started_at = datetime.now(timezone.utc)

    try:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={'User-Agent': USER_AGENT},
        ) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        logger.warning('scrape_url: network error for %s: %s', url, exc)
        return {
            'url': url,
            'error': f'{type(exc).__name__}: {exc}',
            'fetched_at': started_at.isoformat(),
        }

    elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    title: str | None = None
    if 'html' in response.headers.get('content-type', '').lower():
        match = TITLE_RE.search(response.text)
        if match:
            title = match.group(1).strip()

    logger.info(
        'scrape_url: %s -> %s (title=%r, %dms)',
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