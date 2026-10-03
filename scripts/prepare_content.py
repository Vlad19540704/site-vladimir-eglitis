"""One-time, reviewable migration of the supplied staging HTML.

The approved article bodies inside main .readable are left untouched.
"""
from pathlib import Path
import json
import re
from bs4 import BeautifulSoup

SITE = Path(__file__).resolve().parents[1] / 'site'
PAGES = sorted(SITE.glob('*.html')) + sorted((SITE / 'articles').glob('*.html'))
WHATSAPP = 'https://wa.me/358466170891'
EMAIL = 'mailto:eglvlad2025@outlook.com'
MAX = 'https://max.ru/u/f9LHodD0cOJ57eetEyicu--mDK2NszjKeeEYBEHcl7uGccaQ9irTHc0Jg6k'
TELEGRAM = 'https://t.me/+358466170891'

for path in PAGES:
    article = path.parent.name == 'articles'
    prefix = '../' if article else ''
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    for old in soup.select('link[rel="icon"]'):
        old.decompose()
    favicon = soup.new_tag('link', rel='icon', type='image/svg+xml', href=prefix + 'assets/favicon.svg')
    soup.head.append(favicon)
    nav = soup.select_one('#main-nav')
    nav.clear()
    for label, href in [
        ('Главная', 'index.html'),
        ('Консультация', 'approach.html'),
        ('О Владимире', 'about.html'),
        ('Статьи', 'articles.html'),
        ('Контакты', 'contact.html'),
    ]:
        link = soup.new_tag('a', href=prefix + href)
        link.string = label
        if path.name == href:
            link['aria-current'] = 'page'
        nav.append(link)
    nav['aria-label'] = 'Основная навигация'
    button = soup.select_one('.menu-toggle')
    button['type'] = 'button'
    button['aria-label'] = 'Открыть меню'

    footer = soup.select_one('.footer-grid')
    for group in footer.select('.footer-links'):
        group.decompose()
    links = soup.new_tag('div', attrs={'class': 'footer-links'})
    for label, href in [('Консультация', 'approach.html'), ('О Владимире', 'about.html'),
                        ('Статьи', 'articles.html'), ('Контакты', 'contact.html')]:
        a = soup.new_tag('a', href=prefix + href)
        a.string = label
        links.append(a)
    footer.append(links)
    channels = soup.new_tag('div', attrs={'class': 'footer-links'})
    for label, href in [('WhatsApp', WHATSAPP), ('Email', EMAIL), ('MAX', MAX), ('Telegram', TELEGRAM)]:
        a = soup.new_tag('a', href=href)
        a.string = label
        if href.startswith('https://'):
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'
        channels.append(a)
    footer.append(channels)
    copyright_line = soup.select_one('.footer-bottom span')
    if copyright_line:
        copyright_line.string = '© 2026 Владимир Эглитис · Предпубликационная версия'

    if article:
        for old in soup.select('script[type="application/ld+json"]'):
            old.decompose()
        for target in soup.select('.contact-band a'):
            target.string = 'Написать в WhatsApp →'
            target['href'] = WHATSAPP
            target['target'] = '_blank'
            target['rel'] = 'noopener noreferrer'
        title = soup.select_one('h1').get_text(' ', strip=True)
        meta = soup.select_one('meta[name="description"]')
        data = {
            '@context': 'https://schema.org', '@type': 'Article',
            'headline': title, 'description': meta.get('content', '') if meta else '',
            'author': {'@type': 'Person', 'name': 'Владимир Эглитис'},
            'inLanguage': 'ru',
        }
        script = soup.new_tag('script', type='application/ld+json')
        script.string = json.dumps(data, ensure_ascii=False)
        soup.head.append(script)
        if path.name == 'kak-ponyat-problemu.html':
            soup.title.string = 'Как понять, что алкоголь стал проблемой? — Владимир Эглитис'

    if path.name == 'index.html':
        if not soup.select_one('.hero-channels'):
            channels = soup.new_tag('div', attrs={'class': 'hero-channels'})
            soup.select_one('.main-cta').insert_after(channels)
        for node in soup.select('.hero-channels'):
            node.clear()
            a = soup.new_tag('a', href=EMAIL)
            a.string = 'Или написать по email →'
            node.append(a)
        for node in soup.select('.contact-actions'):
            node.clear()
            for label, href in [('WhatsApp', WHATSAPP), ('Email', EMAIL), ('MAX', MAX), ('Telegram', TELEGRAM)]:
                a = soup.new_tag('a', href=href)
                a.string = label + ' ↗'
                a['class'] = 'pill brown-pill' if label in ('WhatsApp', 'Email') else 'text-link contact-secondary'
                if href.startswith('https://'):
                    a['target'] = '_blank'
                    a['rel'] = 'noopener noreferrer'
                node.append(a)
        for node in soup.select('.payment-line'):
            node.clear()
            strong = soup.new_tag('strong')
            strong.string = 'Онлайн, на русском языке.'
            node.append(strong)
            node.append(soup.new_tag('br'))
            node.append('Стоимость для России — в рублях. Оплата через Сбер.')
        for node in soup.select('.main-cta'):
            node.clear()
            node.string = 'Написать в WhatsApp →'
            node['href'] = WHATSAPP
            node['target'] = '_blank'
            node['rel'] = 'noopener noreferrer'
        for node in soup.select('.portrait-placeholder'):
            node.clear()
            node.string = 'Место для фотографии Владимира'
        for node in soup.select('.article-grid img'):
            node['loading'] = 'eager'

    if path.name == 'contact.html':
        main = soup.select_one('main')
        main.clear()
        fragment = BeautifulSoup(f'''<section class="inner-hero"><div class="wrap"><p class="kicker">Контакты</p><h1>Связаться с Владимиром</h1><p>Для записи достаточно короткого сообщения. Не нужно заранее описывать всю историю.</p></div></section><section class="content-panel"><div class="readable"><h2>Написать Владимиру</h2><p>Начните с удобного способа связи. Медицинские подробности не нужно отправлять в первом сообщении.</p><div class="channel-list"><a href="{WHATSAPP}" target="_blank" rel="noopener noreferrer"><strong>WhatsApp ↗</strong><small>+358 46 617 08 91</small></a><a href="{EMAIL}"><strong>Email ↗</strong><small>eglvlad2025@outlook.com</small></a><a href="{MAX}" target="_blank" rel="noopener noreferrer"><strong>MAX ↗</strong><small>+7 981 188 15 62</small></a><a href="{TELEGRAM}" target="_blank" rel="noopener noreferrer"><strong>Telegram ↗</strong><small>+358 46 617 08 91</small></a></div><p>Ознакомительная консультация бесплатна. Для клиентов из России стоимость в рублях, оплата через Сбер. Полный прайс — на <a href="prices.html">странице стоимости</a>.</p><h2>Если сейчас нужна медицинская помощь</h2><p>При судорогах, галлюцинациях, выраженной спутанности или тяжёлой абстиненции обратитесь в местную службу экстренной медицинской помощи. Консультирование не заменяет медицинскую помощь.</p></div></section>''', 'html.parser')
        for child in list(fragment.contents):
            main.append(child)

    if path.name == 'prices.html':
        main = soup.select_one('main')
        main.clear()
        fragment = BeautifulSoup('''<section class="inner-hero"><div class="wrap"><p class="kicker">Стоимость</p><h1>Консультации и цены</h1><p>Основной формат — онлайн на русском языке. Можно начать с бесплатной ознакомительной встречи.</p></div></section><section class="content-panel"><div class="readable price-list"><h2>Для клиентов из России</h2><p>Стоимость в рублях. Оплата через Сбер; порядок оплаты сообщу при записи.</p><div class="price-row"><div><strong>Ознакомительная встреча</strong><p>Знакомимся и обсуждаем, какая помощь нужна.</p></div><div class="amount">Бесплатно</div></div><div class="price-row"><div><strong>Первая консультация</strong><p>60 минут</p></div><div class="amount">5 000 ₽</div></div><div class="price-row"><div><strong>Последующая консультация</strong><p>50 минут</p></div><div class="amount">4 500 ₽</div></div><div class="price-row"><div><strong>Поддерживающая консультация</strong><p>30–40 минут</p></div><div class="amount">3 500 ₽</div></div><h2>Для клиентов из других стран</h2><div class="price-row"><div>Первая консультация · 60 минут</div><div class="amount">60 €</div></div><div class="price-row"><div>Последующая · 50 минут</div><div class="amount">50 €</div></div><div class="price-row"><div>Поддерживающая · 30–40 минут</div><div class="amount">40 €</div></div><h2>Условия</h2><p>Цены указаны за одну консультацию, обязательных пакетов нет. Бесплатный перенос или отмена — не позднее чем за 24 часа до встречи. Условия более поздней отмены уточняются.</p><p>Консультирование не заменяет медицинскую или экстренную помощь.</p><p><a class="pill brown-pill" href="contact.html">Как связаться →</a></p></div></section>''', 'html.parser')
        for child in list(fragment.contents):
            main.append(child)
        soup.select_one('meta[name="description"]')['content'] = 'Стоимость онлайн-консультаций по алкогольной зависимости в рублях и евро. Оплата через Сбер для клиентов из России.'

    # Preserve text and structure of article .readable; only shared shell changes.
    html = str(soup)
    html = re.sub(r'<(meta|link|br|img)([^<>]*?)/>', r'<\1\2>', html)
    html = html.replace(' defer=""', ' defer')
    path.write_text(html, encoding='utf-8')
