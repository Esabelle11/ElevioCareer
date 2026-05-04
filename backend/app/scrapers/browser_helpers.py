"""Shared Chromium launch + context for headless scraping on Linux (e.g. Render)."""

from playwright.sync_api import Browser, Playwright

# Required on many cloud hosts; reduces automation fingerprint noise.
CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1365,900",
]

STEALTH_INIT_SCRIPT = """
(() => {
  const def = (obj, key, val) => {
    try {
      Object.defineProperty(obj, key, { get: () => val, configurable: true });
    } catch (e) {}
  };
  def(navigator, "webdriver", undefined);
  def(navigator, "languages", ["en-GB", "en-US", "en"]);
  if (!window.chrome) window.chrome = { runtime: {} };
})();
"""


def launch_chromium(p: Playwright):
    return p.chromium.launch(headless=True, args=CHROMIUM_ARGS)


def new_browser_context(
    browser: Browser,
    *,
    timezone_id: str = "Asia/Kuala_Lumpur",
    locale: str = "en-GB",
):
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1365, "height": 900},
        locale=locale,
        timezone_id=timezone_id,
        color_scheme="light",
        extra_http_headers={
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        },
    )
    context.add_init_script(STEALTH_INIT_SCRIPT)
    return context
