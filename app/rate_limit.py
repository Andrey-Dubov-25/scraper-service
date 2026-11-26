import logging
import os
import time

import redis


logger = logging.getLogger(__name__)

RATELIMIT_REDIS_URL = os.getenv(
    'RATELIMIT_REDIS_URL', 'redis://localhost:6379/3'
)
redis_client = redis.from_url(RATELIMIT_REDIS_URL, decode_responses=True)

DEFAULT_INTERVAL_SECONDS = 2.0


def wait_for_slot(
    domain: str, min_interval: float = DEFAULT_INTERVAL_SECONDS
) -> float:
    """
    Блокирует выполнение, пока с последнего запроса к этому домену
    не пройдет min_interval секунд. Атомарно через Redis SET NX PX.
    Возвращает суммарно прожданное время в секундах.
    """
    key = f'ratelimit:{domain}'
    interval_ms = int(min_interval * 1000)
    waited = 0.0

    while True:
        if redis_client.set(key, '1', nx=True, px=interval_ms):
            if waited > 0:
                logger.info('rate_limit: waited %.2fs for %s', waited, domain)
            return waited

        ttl_ms = redis_client.pttl(key)
        if ttl_ms < 0:
            time.sleep(0.05)
            waited += 0.05
            continue

        sleep_s = min(ttl_ms / 1000.0 + 0.01, 0.5)
        time.sleep(sleep_s)
        waited += sleep_s
