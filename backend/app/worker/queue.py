# worker/queue.py
from rq import Queue
from redis import Redis
from app.job_services.run_scrapper import run_scrapper
import os

# redis_conn = Redis()
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
queue = Queue(connection=redis_conn)

def enqueue_scrape_job(location, keyword,job_id):
    job = queue.enqueue(run_scrapper, location, keyword,job_id)
    
    return job.id