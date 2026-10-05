from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    for url, button in [
        ('https://www.vdsina.com/ru/pricing/standard', 'Заказать'),
        ('https://www.namecheap.com/domains/registration/results/?domain=vladimireglitis.com', None),
    ]:
        page = browser.new_page()
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=20000)
            print('PAGE', url, 'status', response.status if response else None, 'url', page.url)
            if button:
                try:
                    page.get_by_role('button', name=button).first.click(timeout=5000)
                    print('AFTER CLICK', page.url, page.locator('body').inner_text()[:500].replace('\n', ' '))
                    print('TABS', [p.url for p in page.context.pages])
                except Exception as error:
                    print('CLICK', type(error).__name__, str(error)[:120])
            else:
                print('BODY', page.locator('body').inner_text()[:700].replace('\n', ' '))
        except Exception as error:
            print('ERROR', url, type(error).__name__, str(error)[:120])
        page.close()
    browser.close()
