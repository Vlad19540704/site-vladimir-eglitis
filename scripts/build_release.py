"""Build a minimal, domain-specific static release after explicit launch approval.

Usage: python scripts/build_release.py --domain example.com --checklist release_approval.json
All checklist values must be true. Keep approval file outside Git.
"""
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, ElementTree
import json
import re
import shutil
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PAGES = ['index.html', 'approach.html', 'about.html', 'prices.html', 'articles.html',
         'contact.html', 'privacy.html', 'terms.html',
         'articles/kak-ponyat-problemu.html', 'articles/kak-brosit-pit.html']
ASSETS = ['site-v10.css', 'site-v08.js', 'hero-sunset-v1.png', 'shore.webp',
          'desk.webp', 'book.webp', 'portrait.webp', 'favicon.svg',
          'icon-telegram.svg', 'icon-whatsapp.svg', 'icon-max.svg']
REQUIRED = ['domain_owned', 'public_launch_approved', 'contacts_verified', 'real_photo_approved',
            'ruble_terms_verified', 'education_verified', 'about_text_approved', 'legal_terms_approved', 'privacy_policy_approved',
            'article_dates_confirmed', 'visual_approved']

parser = ArgumentParser()
parser.add_argument('--domain', required=True)
parser.add_argument('--checklist', type=Path, required=True)
parser.add_argument('--published-on', help='Actual first public release date, YYYY-MM-DD')
args = parser.parse_args()
domain = args.domain.strip().lower()
parsed = urlparse('https://' + domain)
if not parsed.hostname or parsed.netloc != domain or '/' in domain:
    raise SystemExit('Invalid domain')
approval = json.loads(args.checklist.read_text(encoding='utf-8'))
missing = [key for key in REQUIRED if approval.get(key) is not True]
try:
    published_on = date.fromisoformat(args.published_on) if args.published_on else None
except ValueError as error:
    raise SystemExit(f'Invalid publication date: {error}')
if published_on is None:
    missing.append('publication_date')
missing += [f'file:{rel}' for rel in PAGES + ['assets/' + a for a in ASSETS] if not (SITE / rel).is_file()]
for rel in ['index.html', 'contact.html', 'prices.html']:
    if (SITE / rel).is_file() and any(term in (SITE / rel).read_text(encoding='utf-8').lower()
                                        for term in ['после подтверждения', 'уточняются', 'прайс обновляется']):
        missing.append(f'placeholder:{rel}')
for rel in ('index.html', 'about.html'):
    if (SITE / rel).is_file():
        page = BeautifulSoup((SITE / rel).read_text(encoding='utf-8'), 'html.parser')
        if page.select_one('.portrait-placeholder'):
            missing.append(f'placeholder:{rel}')
if (SITE / 'contact.html').is_file():
    contact = BeautifulSoup((SITE / 'contact.html').read_text(encoding='utf-8'), 'html.parser')
    if not contact.select('main a[href^="mailto:"], main a[href^="https://"]'):
        missing.append('verified_contact_link')
for rel in PAGES:
    if rel.startswith('articles/') and (SITE / rel).is_file():
        page = BeautifulSoup((SITE / rel).read_text(encoding='utf-8'), 'html.parser')
        if not page.select_one('.article-byline .publication-pending'):
            missing.append(f'article_date_slot:{rel}')
if missing:
    raise SystemExit('Release blocked: ' + ', '.join(missing))

out = ROOT / 'release' / domain
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
for rel in PAGES:
    source = SITE / rel
    dest = out / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(source.read_text(encoding='utf-8'), 'html.parser')
    robots = soup.select_one('meta[name="robots"]')
    robots['content'] = 'index,follow'
    if rel.startswith('articles/'):
        months = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
        stamp = soup.select_one('.publication-pending')
        stamp.replace_with(soup.new_tag('time', attrs={'class': 'publication-date', 'datetime': published_on.isoformat()}))
        soup.select_one('.publication-date').string = f'Опубликовано {published_on.day} {months[published_on.month - 1]} {published_on.year}'
        script = soup.select_one('script[type="application/ld+json"]')
        article_data = json.loads(script.string)
        article_data['datePublished'] = published_on.isoformat()
        article_data['dateModified'] = published_on.isoformat()
        script.string = json.dumps(article_data, ensure_ascii=False)
    for node in soup.find_all(string=True):
        if 'Предпубликационная версия' in node:
            node.replace_with(node.replace(' · Предпубликационная версия', '').replace('Предпубликационная версия', ''))
    canonical = soup.new_tag('link', rel='canonical', href='https://' + domain + '/' + ('' if rel == 'index.html' else rel))
    soup.head.append(canonical)
    html = str(soup)
    html = re.sub(r'<(meta|link|br|img)([^>]*)/>', r'<\1\2>', html)
    html = html.replace(' defer=""', ' defer')
    dest.write_text(html, encoding='utf-8')
for asset in ASSETS:
    dest = out / 'assets' / asset
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(SITE / 'assets' / asset, dest)
(out / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n', encoding='utf-8')
root = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
for rel in PAGES:
    SubElement(SubElement(root, 'url'), 'loc').text = 'https://' + domain + '/' + ('' if rel == 'index.html' else rel)
ElementTree(root).write(out / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
print(out)
