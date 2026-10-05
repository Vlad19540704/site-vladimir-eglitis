"""Validate generated SEO and ensure authored article bodies survive the build."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup


def verify(root, site):
    manifest = json.loads((root / 'release-manifest.json').read_text(encoding='utf-8'))
    base = 'https://' + manifest['domain']
    pages = sorted(path for path in root.rglob('*.html') if path.name != '404.html')
    assert len(pages) == 10, 'Expected ten release pages'
    titles, descriptions, urls = set(), set(), set()
    for path in pages:
        rel = path.relative_to(root).as_posix()
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        original = BeautifulSoup((site / rel).read_text(encoding='utf-8'), 'html.parser')
        url = base + '/' + ('' if rel == 'index.html' else rel)
        titles.add(soup.title.get_text())
        descriptions.add(soup.select_one('meta[name="description"]')['content'])
        urls.add(url)
        assert soup.select_one('link[rel="canonical"]')['href'] == url, rel
        expected_robots = 'noindex,nofollow' if manifest['preview'] else 'index,follow'
        assert soup.select_one('meta[name="robots"]')['content'] == expected_robots, rel
        assert len(soup.select('main h1')) == 1, rel
        assert soup.select_one('meta[property="og:url"]')['content'] == url, rel
        image = soup.select_one('meta[property="og:image"]')['content']
        assert (root / urlparse(image).path.lstrip('/')).is_file(), rel
        graph = json.loads(soup.select_one('script[type="application/ld+json"]').string)['@graph']
        assert any(node['@type'] == 'WebPage' and node['url'] == url for node in graph), rel
        for img in soup.select('img'):
            assert int(img['width']) > 0 and int(img['height']) > 0, rel
        if rel.startswith('articles/'):
            def body(page):
                return [(node.name, node.get_text(' ', strip=True)) for node in page.select('.readable > *')]
            assert body(soup) == body(original), 'Article text changed: ' + rel
            article = next(node for node in graph if node['@type'] == 'Article')
            assert article['headline'] == soup.h1.get_text(' ', strip=True), rel
            assert article['author']['url'] == base + '/about.html', rel
            if manifest['preview']:
                assert 'datePublished' not in article, rel
            else:
                assert article['datePublished'] == soup.select_one('time')['datetime'], rel
    assert len(titles) == len(pages) and len(descriptions) == len(pages), 'Duplicate search metadata'
    sitemap_urls = {node.text for node in ElementTree.parse(root / 'sitemap.xml').iter()
                    if node.tag.endswith('}loc')}
    assert urls == sitemap_urls, 'Sitemap and canonical URLs differ'
    robots = (root / 'robots.txt').read_text(encoding='utf-8')
    assert ('Disallow: /' in robots) == manifest['preview'], 'Incorrect robots.txt'
    actual_files = {path.relative_to(root).as_posix() for path in root.rglob('*')
                    if path.is_file() and path.name != 'release-manifest.json'}
    assert actual_files == set(manifest['files']), 'Missing or unexpected artifact files'
    for rel, digest in manifest['files'].items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest, rel
        if rel.startswith('assets/'):
            fingerprint = re.search(r'\.([a-f0-9]{12})\.[^.]+$', rel)
            assert fingerprint and fingerprint.group(1) == digest[:12], 'Unsafe cached asset: ' + rel
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('release', type=Path)
    args = parser.parse_args()
    result = verify(args.release, Path(__file__).resolve().parents[1] / 'site')
    print(f"PASS: 10 pages, canonical/sitemap, structured data, original article text, {len(result['files'])} hashes; preview={result['preview']}")
