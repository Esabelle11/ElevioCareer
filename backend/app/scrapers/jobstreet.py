from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from app.job_services.region import is_singapore_location, jobstreet_search_base
from app.scrapers.browser_helpers import launch_chromium, new_browser_context


def _jobstreet_likely_blocked(page) -> bool:
    url = (page.url or "").lower()
    if any(x in url for x in ("captcha", "challenge", "blocked")):
        return True
    try:
        if page.locator('iframe[src*="recaptcha" i]').count() > 0:
            return True
    except Exception:
        pass
    try:
        body = page.inner_text("body", timeout=5000).lower()
    except Exception:
        return False
    needles = (
        "access denied",
        "unusual traffic",
        "prove you are human",
        "please enable javascript",
        "pardon our interruption",
    )
    return any(n in body for n in needles)


def scrape_jobstreet(location, keyword):
    jobs = []
    print("In job street scraper", flush=True)

    base = jobstreet_search_base(location)
    location_url = location.replace(" ", "-")
    keyword_url = keyword.replace(" ", "-")
    url = f"{base.rstrip('/')}/{keyword_url}-jobs/in-{location_url}"

    print("url:", url, flush=True)

    tz = "Asia/Singapore" if is_singapore_location(location) else "Asia/Kuala_Lumpur"

    with sync_playwright() as p:
        browser = launch_chromium(p)
        context = new_browser_context(browser, timezone_id=tz)
        page = context.new_page()

        page.goto(url, timeout=3000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        if _jobstreet_likely_blocked(page):
            print("JobStreet: challenge or block page detected")
            context.close()
            browser.close()
            return []

        page.wait_for_selector("body")
        try:
            page.wait_for_selector('[data-testid="job-card"]', timeout=25000)
        except Exception:
            print("JobStreet: job cards not found in time")

        cards = page.query_selector_all('[data-testid="job-card"]')

        cards = cards[:15]
        print("cards found:", len(cards), flush=True)

        job_page = context.new_page()

        for c in cards:
            try:
                title_el = c.query_selector('[data-testid="job-card-title"]')
                company_el = c.query_selector(
                    '[data-type="company"][data-automation="jobCompany"]'
                )
                location_el = c.query_selector(
                    '[data-type="location"][data-automation="jobLocation"]'
                )
                link_el = c.query_selector("a")

                title = title_el.inner_text().strip() if title_el else ""
                company = company_el.inner_text().strip() if company_el else ""
                loc_text = location_el.inner_text().strip() if location_el else ""

                job_url = ""
                if link_el:
                    href = link_el.get_attribute("href")
                    if href:
                        job_url = urljoin(base + "/", href.lstrip("/"))

                description = ""

                if job_url:
                    try:
                        job_page.goto(job_url, timeout=3000, wait_until="domcontentloaded")
                        job_page.wait_for_timeout(1500)
                        if not _jobstreet_likely_blocked(job_page):
                            job_page.wait_for_selector(
                                '[data-automation="jobAdDetails"]',
                                timeout=20000,
                            )
                            desc_el = job_page.query_selector('[data-automation="jobAdDetails"]')
                            if desc_el:
                                description = desc_el.inner_text().strip()
                    except Exception:
                        description = ""

                if title:
                    jobs.append(
                        {
                            "title": title,
                            "company": company,
                            "location": loc_text,
                            "job_url": job_url,
                            "source": "jobstreet",
                            "description": description,
                        }
                    )
                print("card done", flush=True)


            except Exception:
                continue

        job_page.close()
        context.close()
        browser.close()

    return jobs
