from playwright.sync_api import sync_playwright

def scrape_indeed():
    jobs = []
    print("In indeed scraper")

    url = "https://malaysia.indeed.com/jobs?q=admin&l=Kuala+Lumpur"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(url, timeout=3000)
        page.wait_for_timeout(8000)

        cards = page.query_selector_all("div.job_seen_beacon")
        cards = cards[:20]
        print("cards found:", len(cards))

        for c in cards:
            try:
                title_el = c.query_selector("h2 span")
                company_el = c.query_selector('[data-testid="company-name"]')
                location_el = c.query_selector('[data-testid="text-location"]')
                link_el = c.query_selector("a")

                title = title_el.inner_text().strip() if title_el else ""
                company = company_el.inner_text().strip() if company_el else ""
                location = location_el.inner_text().strip() if location_el else ""

                job_url = ""
                if link_el:
                    href = link_el.get_attribute("href")
                    if href:
                        job_url = "https://malaysia.indeed.com" + href

                description = ""

                # ✅ STEP 2: visit job page
                if job_url:
                    job_page = browser.new_page()
                    job_page.goto(job_url, timeout=5000)

                    # wait for description container (Indeed changes this often)
                    try:
                        job_page.wait_for_selector("#jobDescriptionText", timeout=20000)
                        desc_el = job_page.query_selector("#jobDescriptionText")
                        if desc_el:
                            description = desc_el.inner_text().strip()
                    except:
                        description = ""

                    job_page.close()

                if title:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "job_url": job_url,
                        "source": "indeed",
                        "description": description
                    })

            except Exception as e:
                print("error:", e)
                continue

        browser.close()

    return jobs