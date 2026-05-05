import random

from app.scrapers.indeed import scrape_indeed
from app.scrapers.jobstreet import scrape_jobstreet
from app.db.connection import upsert_job

def run_scrapper(location: str, keyword: str, job_id: str) -> str:
    """Fetch jobs from Indeed and JobStreet, store under one shared batch id. Returns batch id."""
   

    # print("job_id:",job_id)
    
    # try:
    #     for job in scrape_indeed(location=location, keyword=keyword):
    #         upsert_job(job, job_id)
    # except Exception as e:  # noqa: BLE001
    #     print("Indeed failed:", e)

    try:
        for job in scrape_jobstreet(location=location, keyword=keyword):
            upsert_job(job, job_id)
    except Exception as e:  # noqa: BLE001
        print("JobStreet failed:", e)

  

    print("Done Scrapping")

    return job_id
