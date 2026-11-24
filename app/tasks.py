from app.celery_app import app


@app.task
def ping() -> str:
    """Проверочная задача: убедиться, что воркер жив и видит задачи."""
    return 'pong'