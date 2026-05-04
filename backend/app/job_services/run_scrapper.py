import random

from app.scrapers.indeed import scrape_indeed
from app.scrapers.jobstreet import scrape_jobstreet
from app.db.connection import upsert_job


def run_scrapper(location: str, keyword: str) -> str:
    """Fetch jobs from Indeed and JobStreet, store under one shared batch id. Returns batch id."""
    batch_seed = str(random.randint(1, 1000000))

    jobs: list[dict] = []
    try:
        jobs += scrape_indeed(location=location, keyword=keyword)
    except Exception as e:  # noqa: BLE001
        print("Indeed failed:", e)

    try:
        jobs += scrape_jobstreet(location=location, keyword=keyword)
    except Exception as e:  # noqa: BLE001
        print("JobStreet failed:", e)

    print(f"Fetched {len(jobs)} jobs")

    for job in jobs:
        upsert_job(job, batch_seed=batch_seed)
        print(f"Stored job batch: {batch_seed}")

    print("Done")

    return batch_seed
