from pathlib import Path
from urllib.parse import urlparse, unquote
import subprocess
import sys
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PAGES = sorted(path for path in SITE.glob('*.html') if path.name != '404.html') + sorted((SITE / 'articles').glob('*.html'))
BASELINE = '68a8d59'
CONTACT_URLS = {
    'https://wa.me/79811881562',
    'mailto:eglvlad2025@outlook.com',
    'https://max.ru/u/f9LHodD0cOJ57eetEyicu--mDK2NszjKeeEYBEHcl7uGccaQ9irTHc0Jg6k',
    'https://t.me/eglitisonline_contact_bot',
}
PRIVACY_URLS = {
    'https://www.tawk.to/data-protection/dpa-data-processing-addendum/',
    'https://www.tawk.to/privacy-policy/',
}
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
            check(href in CONTACT_URLS or (rel == 'privacy.html' and href in PRIVACY_URLS), f'{rel}: unexpected external link: {href}')
            if parsed.scheme == 'https':
                check(a.get('rel') == ['noopener', 'noreferrer'] and a.get('target') == '_blank', f'{rel}: unsafe external link: {href}')
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
            return [(e.name, e.get_text(' ', strip=True)) for e in s.select('main .readable > p, main .readable > h2, main .readable > ul, main .readable > aside') if 'article-cta' not in e.get('class', []) and 'article-action' not in e.get('class', []) and 'subtle' not in e.get('class', [])]
        check(authored(soup) == authored(old), f'{rel}: authored article body changed')
        ld = soup.select('script[type="application/ld+json"]')
        check(len(ld) == 1, f'{rel}: expected one Article JSON-LD')
        check(soup.select_one('.article-cover img') is not None, f'{rel}: cover missing')
        check(soup.select_one('.article-byline .publication-pending') is not None, f'{rel}: publication field missing')
        check(len(soup.select('.article-action a[href="../contact.html"]')) == 1, f'{rel}: contact CTA missing')
        check(not soup.select_one('.contact-band, .article-cta'), f'{rel}: old CTA remains')

check(len(PAGES) == 10, f'expected 10 pages, got {len(PAGES)}')
check(len(list((SITE / 'articles').glob('*.html'))) == 2, 'unapproved article present')
check('Disallow: /' in (SITE / 'robots.txt').read_text(), 'staging robots allows crawl')
home = BeautifulSoup((SITE / 'index.html').read_text(encoding='utf-8'), 'html.parser')
contact = BeautifulSoup((SITE / 'contact.html').read_text(encoding='utf-8'), 'html.parser')
primary = {
    'https://t.me/eglitisonline_contact_bot',
    'https://wa.me/79811881562',
    'https://max.ru/u/f9LHodD0cOJ57eetEyicu--mDK2NszjKeeEYBEHcl7uGccaQ9irTHc0Jg6k',
}
check({a['href'] for a in home.select('.hero-direct a')} == primary, 'home: primary messengers differ')
check({a['href'] for a in contact.select('.primary-channels a')} == primary, 'contact: primary messengers differ')
check(home.select_one('.hero h1').get_text(' ', strip=True) == 'Есть место, где можно говорить честно.', 'home: approved hero headline changed')
check(len(home.select('.article-grid article')) == 2, 'home: wrong article count')
check(home.select_one('.about-section img.portrait-photo[src="assets/portrait-v1.webp"]') is not None, 'home: approved portrait missing')
check(not home.select_one('.hero-more, .about-quote'), 'home: removed links or quote returned')
check('Для клиентов из России стоимость указана в рублях. Оплата через Сбер.' not in home.get_text(' ', strip=True), 'home: removed price sentence returned')
check(len(BeautifulSoup((SITE / 'articles.html').read_text(encoding='utf-8'), 'html.parser').select('.article-list img')) == 2, 'articles: card covers missing')
prices = BeautifulSoup((SITE / 'prices.html').read_text(encoding='utf-8'), 'html.parser')
about = BeautifulSoup((SITE / 'about.html').read_text(encoding='utf-8'), 'html.parser')
approach = BeautifulSoup((SITE / 'approach.html').read_text(encoding='utf-8'), 'html.parser')
about_text = about.select_one('main').get_text(' ', strip=True)
approach_text = approach.select_one('main').get_text(' ', strip=True)
check(about.select_one('.about-story img.portrait-photo[src="assets/portrait-v1.webp"]') is not None, 'about: approved portrait missing')
check('Сообщество Анонимных Алкоголиков занимает важное место' not in about_text, 'about: removed AA paragraph returned')
check(not contact.select('.primary-channels small'), 'contact: visible phone numbers returned')
check('wrap' in contact.select_one('.contact-page').get('class', []), 'contact: main section not aligned to site grid')
for fact in ('15 августа 1999', '2012 года', '520 учебных часов', '28 октября 2016',
             '2017 · Варшава', '2011 · Таллинн', 'Oxford Learning'):
    check(fact in about_text, f'about: missing restored fact {fact}')
for fact in ('отрицание', 'триггеры', 'предупреждающие признаки', 'Если произошёл срыв',
             'Между консультациями', 'не платное спонсорство'):
    check(fact in approach_text, f'approach: missing restored topic {fact}')
check(len(approach.select('.approach-faq details')) == 5, 'approach: FAQ missing')
check(len(contact.select('.booking-grid > div')) == 3, 'contact: booking sequence missing')
if prices.select_one('.price-pending'):
    ruble_section = prices.select_one('.price-list h2').find_next_sibling()
    check('₽' not in ruble_section.get_text(), 'prices: outdated ruble amount shown')
else:
    amounts = {row.get_text(' ', strip=True) for row in prices.select('.price-list .amount') if '₽' in row.get_text()}
    check(amounts == {'5 000 ₽', '4 500 ₽', '3 500 ₽'}, 'prices: confirmed ruble amounts changed')
    durations = [row.select_one('p').get_text(' ', strip=True) for row in prices.select('.price-row') if '₽' in row.get_text()]
    check(durations == ['60 минут', '50 минут', '30–40 минут'], 'prices: confirmed durations changed')
for brand in ('telegram', 'whatsapp', 'max'):
    check((SITE / 'assets' / f'icon-{brand}.svg').is_file(), f'{brand}: icon asset missing')
for path in PAGES:
    page = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    check(not page.select_one('.footer-quote, .footer-contact-cta'), f'{path.name}: old footer elements returned')
    check(len(page.select('.footer-channels .messenger-icon')) == 3, f'{path.name}: messenger icons missing')

with sync_playwright() as p:
    chrome = os.environ.get('CHROME_EXECUTABLE_PATH', r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    browser = p.chromium.launch(executable_path=chrome if Path(chrome).is_file() else None, headless=True)
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
        size = float(page.locator('.problem-section .copy p').evaluate('(el) => getComputedStyle(el).fontSize.replace("px", "")'))
        check(size >= 18, f'{width}: body text still too small ({size}px)')
        if width <= 920:
            page.get_by_role('button', name='Открыть меню').focus()
            page.keyboard.press('Enter')
            check(page.locator('#main-nav').is_visible(), f'{width}: menu did not open by keyboard')
            page.keyboard.press('Escape')
            check(not page.locator('#main-nav').is_visible(), f'{width}: menu did not close with Escape')
            check(page.get_by_role('button', name='Открыть меню').evaluate('(el) => document.activeElement === el'), f'{width}: focus not restored')
        check(page.locator('.main-cta').get_attribute('href') == 'contact.html', f'{width}: main CTA does not offer all messengers')
        page.locator('.main-cta').click()
        check(page.url.endswith('/contact.html'), f'{width}: CTA did not reach contacts')
        check(page.locator('main a[href="mailto:eglvlad2025@outlook.com"]').count() == 1, f'{width}: email missing from contacts')
        lefts = page.eval_on_selector_all('.inner-hero .wrap, .contact-page, .booking-steps .wrap, .medical-copy', 'els => els.map(el => Math.round(el.getBoundingClientRect().left))')
        check(len(lefts) == 4 and len(set(lefts)) == 1, f'{width}: contact section alignment differs: {lefts}')
        page.close()
    browser.close()

if errors:
    for error in errors:
        print('FAIL', error)
    raise SystemExit(f'{len(errors)} failures')
print(f'PASS: {len(PAGES)} pages, 2 unchanged article bodies, links, metadata, images, responsive widths, keyboard menu and CTA')
