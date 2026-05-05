from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from app.job_services.region import indeed_site_base, is_singapore_location
from app.scrapers.browser_helpers import launch_chromium, new_browser_context


def _indeed_likely_blocked(page) -> bool:
    """Avoid false positives: normal job HTML often contains words like 'verify'."""
    url = (page.url or "").lower()
    if any(x in url for x in ("captcha", "challenge", "intercept")):
        return True
    try:
        if page.locator('iframe[src*="recaptcha" i], iframe[title*="captcha" i]').count() > 0:
            return True
    except Exception:
        pass
    try:
        body = page.inner_text("body", timeout=5000).lower()
    except Exception:
        return False
    needles = (
        "unusual traffic from your computer network",
        "prove you are human",
        "enable javascript and cookies to continue",
        "robot or human",
        "why did this happen",
        "access denied",
        "please complete the security check",
    )
    return any(n in body for n in needles)


def scrape_indeed(location, keyword):
    jobs = []
    print("In indeed scraper", flush=True)

    base = indeed_site_base(location)
    keyword_url = quote_plus(keyword)
    location_url = quote_plus(location)
    url = f"{base}/jobs?q={keyword_url}&l={location_url}"

    print("url:", url, flush=True)

    tz = "Asia/Singapore" if is_singapore_location(location) else "Asia/Kuala_Lumpur"

    with sync_playwright() as p:
        browser = launch_chromium(p)
        context = new_browser_context(browser, timezone_id=tz)
        page = context.new_page()

        page.goto(url, timeout=3000, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        if _indeed_likely_blocked(page):
            print("Indeed: challenge or block page detected (URL/body heuristics)")
            context.close()
            browser.close()
            return []

        try:
            page.wait_for_selector("div.job_seen_beacon, a.tapItem", timeout=20000)
        except Exception:
            print("Indeed: job list selectors not found in time")

        cards = page.query_selector_all("div.job_seen_beacon")
        if not cards:
            cards = page.query_selector_all("a.tapItem")

        cards = cards[:10]
        print("cards found:", len(cards), flush=True)

        job_page = context.new_page()

        for c in cards:
            try:
                title_el = c.query_selector("h2 span") or c.query_selector("h2 a")
                company_el = c.query_selector('[data-testid="company-name"]')
                location_el = c.query_selector('[data-testid="text-location"]')
                link_el = c.query_selector("a")

                title = title_el.inner_text().strip() if title_el else ""
                company = company_el.inner_text().strip() if company_el else ""
                loc_text = location_el.inner_text().strip() if location_el else ""

                job_url = ""
                if link_el:
                    href = link_el.get_attribute("href")
                    if href:
                        job_url = href if href.startswith("http") else base.rstrip("/") + href

                description = ""

                if job_url:
                    try:
                        job_page.goto(job_url, timeout=3000, wait_until="domcontentloaded")
                        job_page.wait_for_timeout(1500)
                        if _indeed_likely_blocked(job_page):
                            print("Indeed: detail page blocked, skipping description")
                        else:
                            desc_el = job_page.query_selector("#jobDescriptionText")
                            if desc_el:
                                description = desc_el.inner_text().strip()
                    except Exception as e:
                        print("job page error:", e)

                if title:
                    jobs.append(
                        {
                            "title": title,
                            "company": company,
                            "location": loc_text,
                            "job_url": job_url,
                            "source": "indeed",
                            "description": description,
                        }
                    )

            except Exception as e:
                print("card error:", e)
                continue

        job_page.close()
        context.close()
        browser.close()

    return jobs
