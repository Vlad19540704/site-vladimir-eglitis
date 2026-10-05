"""Capture the changed inner pages at desktop and mobile sizes."""

from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STAGE = sys.argv[1] if len(sys.argv) > 1 else "editorial-revisions-final"
OUT = ROOT / "output/playwright" / STAGE
OUT.mkdir(parents=True, exist_ok=True)
PAGES = {
    "about": "about.html",
    "approach": "approach.html",
    "articles": "articles.html",
    "article-problem": "articles/kak-ponyat-problemu.html",
    "article-stop": "articles/kak-brosit-pit.html",
    "contact": "contact.html",
    "prices": "prices.html",
}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True
    )
    for width, height in ((1440, 900), (390, 844)):
        page = browser.new_page(viewport={"width": width, "height": height})
        for name, route in PAGES.items():
            page.goto("http://127.0.0.1:8080/" + route, wait_until="networkidle")
            for img in page.locator("img").all():
                img.scroll_into_view_if_needed()
                img.evaluate("el => el.decode()")
            page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
            print(name, width, page.evaluate("document.documentElement.scrollWidth"))
        page.close()
    browser.close()
