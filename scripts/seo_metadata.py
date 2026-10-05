"""Metadata derived from the page visitors can actually read."""

import json
import posixpath
from PIL import Image


def enrich(soup, rel, domain, site, published_on=None):
    base = f'https://{domain}'
    url = base + '/' + ('' if rel == 'index.html' else rel)
    title = soup.title.get_text(strip=True)
    description = soup.select_one('meta[name="description"]')['content']
    heading = soup.select_one('main h1').get_text(' ', strip=True)
    article = rel.startswith('articles/')
    cover = soup.select_one('.article-cover img') if article else None
    image_rel = (posixpath.normpath(posixpath.join(posixpath.dirname(rel), cover['src']))
                 if cover else 'assets/' + {
                     'about.html': 'portrait-v1.webp', 'prices.html': 'desk.webp',
                     'approach.html': 'desk.webp', 'articles.html': 'shore.webp',
                 }.get(rel, 'hero-sunset-v1.webp'))
    with Image.open(site / image_rel) as source_image:
        width, height = source_image.size

    for old in soup.select('link[rel="canonical"], meta[property^="og:"], meta[name^="twitter:"]'):
        old.decompose()
    soup.head.append(soup.new_tag('link', rel='canonical', href=url))
    if rel == 'index.html':
        soup.head.append(soup.new_tag('link', rel='preload', href='assets/hero-sunset-v1.webp',
                                      attrs={'as': 'image', 'fetchpriority': 'high'}))
    fields = {
        'og:locale': 'ru_RU', 'og:site_name': 'Владимир Эглитис',
        'og:type': 'article' if article else 'website', 'og:title': title,
        'og:description': description, 'og:url': url, 'og:image': base + '/' + image_rel,
        'og:image:width': str(width), 'og:image:height': str(height),
        'og:image:alt': cover['alt'] if cover else heading,
    }
    if article and published_on:
        fields['article:published_time'] = published_on.isoformat()
        fields['article:author'] = base + '/about.html'
    for key, value in fields.items():
        soup.head.append(soup.new_tag('meta', attrs={'property': key, 'content': value}))
    for key, value in {'twitter:card': 'summary_large_image', 'twitter:title': title,
                       'twitter:description': description, 'twitter:image': base + '/' + image_rel}.items():
        soup.head.append(soup.new_tag('meta', attrs={'name': key, 'content': value}))
    for image in soup.select('img[src]'):
        source = site / posixpath.normpath(posixpath.join(posixpath.dirname(rel), image['src']))
        with Image.open(source) as source_image:
            image['width'], image['height'] = map(str, source_image.size)
        image['decoding'] = 'async'

    person = {'@type': 'Person', '@id': base + '/about.html#author',
              'name': 'Владимир Эглитис', 'url': base + '/about.html'}
    website = {'@type': 'WebSite', '@id': base + '/#website', 'url': base + '/',
               'name': 'Владимир Эглитис', 'inLanguage': 'ru'}
    web_page = {'@type': 'WebPage', '@id': url + '#page', 'url': url,
                'name': title, 'description': description, 'inLanguage': 'ru',
                'isPartOf': {'@id': website['@id']}}
    trail = [('Главная', base + '/')]
    if article:
        trail.append(('Статьи', base + '/articles.html'))
    if rel != 'index.html':
        trail.append((heading, url))
    graph = [website, web_page]
    if len(trail) > 1:
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': index, 'name': name, 'item': item}
            for index, (name, item) in enumerate(trail, 1)]})
    if rel == 'about.html':
        graph.append({**person, 'image': base + '/assets/portrait-v1.webp',
                      'jobTitle': 'Консультант по алкогольной зависимости'})
    if article:
        existing = soup.select_one('script[type="application/ld+json"]')
        data = json.loads(existing.string)
        data.pop('@context', None)
        data.update({'@id': url + '#article', 'url': url, 'headline': heading,
                     'author': person, 'image': [base + '/' + image_rel],
                     'mainEntityOfPage': {'@id': web_page['@id']}})
        if published_on:
            data.update({'datePublished': published_on.isoformat(),
                         'dateModified': published_on.isoformat()})
        graph.append(data)
    for old in soup.select('script[type="application/ld+json"]'):
        old.decompose()
    structured = soup.new_tag('script', type='application/ld+json')
    structured.string = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)
    soup.head.append(structured)
