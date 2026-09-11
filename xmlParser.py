
#$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
#playwright install

from playwright.sync_api import sync_playwright
import requests
import feedparser

url = "https://www.wf-vision.com/feed/"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]  # hides the flag Cloudflare checks for
    )
    page = browser.new_page()
    page.goto(url)

    try:
        page.frame_locator("iframe[src*='challenges.cloudflare.com']") \
            .locator("input[type=checkbox]") \
            .click(timeout=15000)
        page.wait_for_timeout(3000)
        print("clicked checkbox")
    except Exception as e:
        print("no checkbox found / click failed:", e)

    cookies = {c["name"]: c["value"] for c in page.context.cookies()}
    user_agent = page.evaluate("navigator.userAgent")
    browser.close()

response = requests.get(url, cookies=cookies, headers={"User-Agent": user_agent})
feed = feedparser.parse(response.text)
print(response.status_code, len(feed.entries))