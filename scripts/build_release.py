"""Build a minimal, domain-specific static release after explicit launch approval.

Usage: python scripts/build_release.py --domain example.com --checklist release_approval.json
All checklist values must be true. Keep approval file outside Git.
"""
from argparse import ArgumentParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, ElementTree
import json
import shutil
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PAGES = ['index.html', 'approach.html', 'about.html', 'prices.html', 'articles.html',
         'contact.html', 'privacy.html', 'terms.html',
         'articles/kak-ponyat-problemu.html', 'articles/kak-brosit-pit.html']
ASSETS = ['site-v08.css', 'site-v08.js', 'shore.webp', 'desk.webp', 'book.webp',
          'study-detail.webp', 'portrait.webp', 'favicon.svg']
REQUIRED = ['domain_owned', 'public_launch_approved', 'contacts_verified', 'real_photo_approved',
            'ruble_terms_verified', 'legal_terms_approved', 'privacy_policy_approved',
            'article_dates_confirmed', 'visual_approved']

parser = ArgumentParser()
parser.add_argument('--domain', required=True)
parser.add_argument('--checklist', type=Path, required=True)
args = parser.parse_args()
domain = args.domain.strip().lower()
parsed = urlparse('https://' + domain)
if not parsed.hostname or parsed.netloc != domain or '/' in domain:
    raise SystemExit('Invalid domain')
approval = json.loads(args.checklist.read_text(encoding='utf-8'))
missing = [key for key in REQUIRED if approval.get(key) is not True]
missing += [f'file:{rel}' for rel in PAGES + ['assets/' + a for a in ASSETS] if not (SITE / rel).is_file()]
for rel in ['index.html', 'contact.html', 'prices.html']:
    if (SITE / rel).is_file() and any(term in (SITE / rel).read_text(encoding='utf-8').lower()
                                        for term in ['после подтверждения', 'уточняются', 'предпубликационная версия']):
        missing.append(f'placeholder:{rel}')
if (SITE / 'contact.html').is_file():
    contact = BeautifulSoup((SITE / 'contact.html').read_text(encoding='utf-8'), 'html.parser')
    if not contact.select('main a[href^="mailto:"], main a[href^="https://"]'):
        missing.append('verified_contact_link')
for rel in PAGES:
    if rel.startswith('articles/') and (SITE / rel).is_file():
        page = BeautifulSoup((SITE / rel).read_text(encoding='utf-8'), 'html.parser')
        if not any('datePublished' in s.get_text() for s in page.select('script[type="application/ld+json"]')):
            missing.append(f'article_date:{rel}')
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
    canonical = soup.new_tag('link', rel='canonical', href='https://' + domain + '/' + ('' if rel == 'index.html' else rel))
    soup.head.append(canonical)
    dest.write_text(str(soup), encoding='utf-8')
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
