from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE = (sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8080/').rstrip('/') + '/'
SIZES = [(1440, 900), (768, 1024), (390, 844), (320, 700)]
stage = sys.argv[1] if len(sys.argv) > 1 else 'baseline'
out = Path(__file__).resolve().parents[1] / 'output' / 'playwright' / stage
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    for width, height in SIZES:
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
        page.goto(BASE, wait_until='networkidle')
        for img in page.locator('img').all():
            img.scroll_into_view_if_needed()
            try:
                img.evaluate('(el) => el.decode()')
            except Exception as error:
                raise RuntimeError(f'Image failed to decode at {width}px: {img.get_attribute("src")}') from error
        page.screenshot(path=str(out / f'home-{width}x{height}.png'), full_page=True)
        print(f'{width}x{height}: title={page.title()!r}, scrollWidth={page.evaluate("document.documentElement.scrollWidth")}, viewport={width}')
        page.close()
    browser.close()
