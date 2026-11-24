from fastapi import FastAPI

from app.tasks import ping


app = FastAPI(title='Scraper Service')

@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/debug/ping')
def debug_ping():
    """Отправить ping-задачу в очередь. Проверка, что Celery работает"""
    task = ping.delay()
    return {'job_id': task.id}
