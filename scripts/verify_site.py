from pathlib import Path
from urllib.parse import urlparse, unquote
import subprocess
import sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PAGES = sorted(SITE.glob('*.html')) + sorted((SITE / 'articles').glob('*.html'))
BASELINE = '68a8d59'
errors = []

def check(ok, message):
    if not ok:
        errors.append(message)

for path in PAGES:
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    rel = path.relative_to(SITE).as_posix()
    check(len(soup.select('main h1')) == 1, f'{rel}: expected one h1')
    check(bool(soup.title and soup.title.get_text(strip=True)), f'{rel}: missing title')
    check(bool(soup.select_one('meta[name="description"][content]')), f'{rel}: missing description')
    check(soup.select_one('meta[name="robots"]').get('content') == 'noindex,nofollow', f'{rel}: staging is indexable')
    check(len(soup.select('#main-nav a')) == 5, f'{rel}: navigation is not five items')
    for a in soup.select('a[href]'):
        href = a['href']
        check(href not in ('#', '') and not href.startswith('javascript:'), f'{rel}: false href {href}')
        parsed = urlparse(href)
        if parsed.scheme in ('http', 'https', 'mailto'):
            check(False, f'{rel}: external contact needs confirmation: {href}')
        elif not parsed.scheme and parsed.path:
            target = (path.parent / unquote(parsed.path)).resolve()
            check(target.is_file() and SITE in target.parents, f'{rel}: broken link {href}')
            if target.is_file() and parsed.fragment:
                target_soup = BeautifulSoup(target.read_text(encoding='utf-8'), 'html.parser')
                check(target_soup.find(id=parsed.fragment) is not None, f'{rel}: missing anchor {href}')
    for img in soup.select('img'):
        check(bool(img.get('alt')), f'{rel}: image missing alt')
        check((path.parent / img['src']).is_file(), f'{rel}: missing image {img["src"]}')
    if path.parent.name == 'articles':
        original = subprocess.check_output(['git', 'show', f'{BASELINE}:{path.relative_to(ROOT).as_posix()}'], cwd=ROOT).decode('utf-8')
        old = BeautifulSoup(original, 'html.parser')
        def authored(s):
            return [(e.name, e.get_text(' ', strip=True)) for e in s.select('main .readable > p, main .readable > h2, main .readable > ul, main .readable > aside')]
        check(authored(soup) == authored(old), f'{rel}: authored article body changed')
        ld = soup.select('script[type="application/ld+json"]')
        check(len(ld) == 1, f'{rel}: expected one Article JSON-LD')

check(len(PAGES) == 8, f'expected 8 pages, got {len(PAGES)}')
check(len(list((SITE / 'articles').glob('*.html'))) == 2, 'unapproved article present')
check('Disallow: /' in (SITE / 'robots.txt').read_text(), 'staging robots allows crawl')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    for width, height in [(1440,900),(768,1024),(390,844),(320,700)]:
        page = browser.new_page(viewport={'width':width,'height':height})
        for path in PAGES:
            rel = path.relative_to(SITE).as_posix()
            response = page.goto('http://127.0.0.1:8080/' + rel, wait_until='networkidle')
            check(response.status == 200, f'{rel}@{width}: HTTP {response.status}')
            check(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'{rel}@{width}: horizontal scroll')
            for img in page.locator('img').all():
                img.scroll_into_view_if_needed()
                img.evaluate('(el) => el.decode()')
                check(img.evaluate('(el) => el.complete && el.naturalWidth > 0'), f'{rel}@{width}: broken image')
        page.goto('http://127.0.0.1:8080/')
        if width <= 920:
            page.get_by_role('button', name='Открыть меню').focus()
            page.keyboard.press('Enter')
            check(page.locator('#main-nav').is_visible(), f'{width}: menu did not open by keyboard')
            page.keyboard.press('Escape')
            check(not page.locator('#main-nav').is_visible(), f'{width}: menu did not close with Escape')
            check(page.get_by_role('button', name='Открыть меню').evaluate('(el) => document.activeElement === el'), f'{width}: focus not restored')
        page.get_by_role('link', name='Как связаться').first.click()
        check(page.url.endswith('/contact.html'), f'{width}: CTA did not reach contacts')
        page.close()
    browser.close()

if errors:
    for error in errors:
        print('FAIL', error)
    raise SystemExit(f'{len(errors)} failures')
print(f'PASS: {len(PAGES)} pages, 2 unchanged article bodies, links, metadata, images, responsive widths, keyboard menu and CTA')
