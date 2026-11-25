from app.celery_app import app


@app.task
def scrape_url(url: str) -> dict:
    """Заглушка. Реальный HTTP-парсинг - на шаге 3."""
    print(f'--- scrape_url: получен {url} ---')
    return {'url': url, 'status': 'stub'}