"""External production checks: HTTPS, redirects, indexing and public pages."""

import json
from urllib.request import urlopen
from urllib.error import HTTPError
from xml.etree import ElementTree
from bs4 import BeautifulSoup

DOMAIN = 'eglitisonline.com'
BASE = 'https://' + DOMAIN
PAGES = ('', 'about.html', 'approach.html', 'prices.html', 'contact.html', 'articles.html',
         'privacy.html', 'terms.html', 'articles/kak-ponyat-problemu.html', 'articles/kak-brosit-pit.html')

for rel in PAGES:
    url = BASE + '/' + rel
    with urlopen(url, timeout=30) as response:
        assert response.status == 200 and response.url == url, rel
        assert 'noindex' not in response.headers.get('X-Robots-Tag', ''), rel
        soup = BeautifulSoup(response.read().decode('utf-8'), 'html.parser')
    assert soup.select_one('meta[name="robots"]')['content'] == 'index,follow', rel
    assert soup.select_one('link[rel="canonical"]')['href'] == url, rel
    assert 'Предпубликационная версия' not in soup.get_text(), rel
    assert not soup.select_one('.publication-pending'), rel
    assert soup.select_one('script[type="application/ld+json"]'), rel
    if rel.startswith('articles/'):
        graph = json.loads(soup.select_one('script[type="application/ld+json"]').string)['@graph']
        article = next(node for node in graph if node['@type'] == 'Article')
        assert article['datePublished'] == soup.select_one('time')['datetime'], rel
    print('HTTPS/canonical/indexing:', '/' + rel)
for url in ('http://' + DOMAIN + '/', BASE + '/index.html', 'https://www.' + DOMAIN + '/'):
    with urlopen(url, timeout=30) as response:
        assert response.url == BASE + '/', url
with urlopen(BASE + '/robots.txt', timeout=30) as response:
    robots = response.read().decode('utf-8')
    assert 'Allow: /' in robots and 'Disallow: /' not in robots
    assert BASE + '/sitemap.xml' in robots
with urlopen(BASE + '/sitemap.xml', timeout=30) as response:
    nodes = ElementTree.fromstring(response.read())
    assert {node.text for node in nodes.iter() if node.tag.endswith('}loc')} == {BASE + '/' + rel for rel in PAGES}
for rel in ('.git/config', '.env', 'scripts/build_release.py', 'deploy/RUNBOOK.md', 'release-manifest.json', 'not-a-page.html'):
    try:
        urlopen(BASE + '/' + rel, timeout=30)
    except HTTPError as error:
        assert error.code == 404, (rel, error.code)
    else:
        raise AssertionError('Private or nonexistent path exposed: ' + rel)
print('PASS: ten public pages, valid HTTPS, redirects, sitemap, robots and private-file protection')
