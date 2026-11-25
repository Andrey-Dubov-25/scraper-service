from fastapi import FastAPI
from pydantic import BaseModel

from app.routing import get_queue_for_url
from app.tasks import scrape_url


app = FastAPI(title='Scraper Service')


class ScrapeRequest(BaseModel):
    urls: list[str]


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/debug/scrape')
def debug_scrape(req: ScrapeRequest):
    """Временно: отправляет задачи и возвращает job_id + очередь."""
    jobs = []
    for url in req.urls:
        queue = get_queue_for_url(url)
        if not queue:
            jobs.append({'url': url, 'error': 'unsupported domain'})
            continue
        task = scrape_url.delay(url)
        jobs.append({'url': url, 'job_id': task.id, 'queue': queue})
    return {'jobs': jobs}