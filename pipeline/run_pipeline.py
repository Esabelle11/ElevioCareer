from db import get_conn, upsert_job
from scrapers.indeed import scrape_indeed
from scrapers.jobstreet import scrape_jobstreet

def run():
    conn = get_conn()


    jobs = []
    # try:
    #     jobs += scrape_indeed()
    # except Exception as e:
    #     print("Indeed failed:", e)

    try:
        jobs += scrape_jobstreet()
    except Exception as e:
        print("JobStreet failed:", e)
        

    print(f"Fetched {len(jobs)} jobs")

    for job in jobs:
        upsert_job(conn, job)

    print("Done")

if __name__ == "__main__":
    run()