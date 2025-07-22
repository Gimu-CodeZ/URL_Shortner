import datetime
from celery import Celery
from app.config import collection_url, get_redis_client
import os

c_app = Celery(
    'url_shortener',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
c_app.conf.update(
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=5,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
        beat_schedule={
        'cache-top-clicked-urls-every-hour': {
            'task': 'app.workers.celery.cache_top_urls',
            'schedule': 3600.0,  # every hour
        },
        'delete-expired-urls-every-day': {
            'task': 'app.workers.celery.delete_expired_urls',
            'schedule': 3600.0,  # every hour
        }
    }
)

@c_app.task(bind=True, retry_backoff=True, max_retries=3)
def click_event(self, short_code, ip_address, timestamp):
    try:
        collection_url.update_one(
            {"short_code": short_code},
            {
                "$inc": {"clicks": 1},
                "$push": {"click_logs": {"timestamp": timestamp, "ip": ip_address}}
            }
        )
    except Exception as exc:
        # Retry the task if it fails
        self.retry(exc=exc)

@c_app.task
def cache_top_urls():
    redis_client = get_redis_client()
    if not redis_client:
        print("Redis client not available")
        return

    print("Caching top 50 most-clicked URLs to Redis...")

    top_urls = collection_url.find().sort("clicks", -1).limit(50)
    for url in top_urls:
        if "short_code" in url and "original_url" in url:
            redis_client.setex(url["short_code"], 86400, url["original_url"])  # 24 hrs
            print(f"Cached: {url['short_code']} -> {url['original_url']}")


@c_app.task
def delete_expired_urls():
    now = datetime.utcnow().isoformat()
    result = collection_url.delete_many({
        "expire_at": {"$lte": now}
    })
    print(f"Deleted {result.deleted_count} expired URLs.")