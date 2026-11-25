from urllib.parse import urlparse


DOMAIN_QUEUES: dict[str, str] = {
    'example.com': 'scrape_example_com',
    'httpbin.org': 'scrape_httpbin_org',
    'quotes.toscrape.com': 'scrape_quotes_toscrape_com',
    'books.toscrape.com': 'scrape_books_toscrape_com'
}

def normalize_host(hostname: str | None) -> str:
    """Убираем www. и приводим к нижнему регистру."""
    if not hostname:
        return ''
    hostname = hostname.lower()
    if hostname.startswith('www.'):
        hostname = hostname[4:]
    return hostname


def get_queue_for_url(url: str) -> str | None:
    """
    Возвращает имя очереди для URL или None, если домен не поддерживается.
    """
    hostname = normalize_host(urlparse(url).hostname)
    return DOMAIN_QUEUES.get(hostname)


def route_task(name, args, kwargs, options, task=None, **kw):
    """
    Вычисляется Celery при .delay()/.()apply_async().
    Возвращает {'queue': '...'} или None (тогда дефолтная очередь).
    """
    if name == 'app.tasks.scrape_url':
        url = args[0] if args else kwargs.get('url', '')
        queue = get_queue_for_url(url)
        if queue:
            return {'queue': queue}
    return None