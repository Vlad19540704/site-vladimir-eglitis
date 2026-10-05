"""Check the VPS preview through a local SSH tunnel without publishing it."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


PAGES = (
    "index.html", "about.html", "approach.html", "prices.html",
    "articles.html", "contact.html", "privacy.html", "terms.html", "articles/kak-brosit-pit.html",
    "articles/kak-ponyat-problemu.html",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8081/")
    args = parser.parse_args()
    base = args.base.rstrip("/") + "/"

    for path in PAGES:
        with urlopen(base + path, timeout=10) as response:
            body = response.read()
            assert response.status == 200 and body
            assert response.headers.get("X-Robots-Tag") == "noindex, nofollow"
    with urlopen(base + "robots.txt", timeout=10) as response:
        assert b"Disallow: /" in response.read()
    for path in ("deploy/RUNBOOK.md", "QA_REPORT.txt", ".git/config"):
        try:
            urlopen(base + path, timeout=10)
        except HTTPError as error:
            assert error.code == 404, (path, error.code)
        else:
            raise AssertionError(f"Private file exposed: {path}")

    out = Path(__file__).resolve().parents[1] / "output" / "playwright" / "vps-preview-home-390.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
        )
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(base, wait_until="networkidle")
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        page.screenshot(path=str(out), full_page=True)
        browser.close()
    print(f"PASS: {len(PAGES)} pages, noindex, robots, private files, mobile rendering")


if __name__ == "__main__":
    main()
