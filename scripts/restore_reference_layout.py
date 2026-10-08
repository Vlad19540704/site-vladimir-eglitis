"""One-time restoration of the approved visual composition.

Keep article body content untouched; only shared shell, home, and contact pages change.
"""

from pathlib import Path

from bs4 import BeautifulSoup

SITE = Path(__file__).resolve().parents[1] / "site"
PAGES = sorted(SITE.glob("*.html")) + sorted((SITE / "articles").glob("*.html"))
TELEGRAM = "https://t.me/eglitisonline_contact_bot"
WHATSAPP = "https://wa.me/79811881562"
MAX = "https://max.ru/u/f9LHodD0cOJ57eetEyicu--mDK2NszjKeeEYBEHcl7uGccaQ9irTHc0Jg6k"
EMAIL = "mailto:eglvlad2025@outlook.com"


def fragment(markup: str, tag: str):
    return BeautifulSoup(markup, "html.parser").find(tag)


def shell_header(prefix: str, current: str):
    nav = [
        ("Главная", "index.html"),
        ("Обо мне", "about.html"),
        ("Консультации и цены", "prices.html"),
        ("Статьи", "articles.html"),
        ("Контакты", "contact.html"),
    ]
    nav_html = "".join(
        f'<a href="{prefix}{href}"{(" aria-current=\"page\"" if current == href else "")}>{label}</a>'
        for label, href in nav
    )
    return fragment(
        f'''<header class="site-head"><div class="wrap head-row">
        <a class="brand" href="{prefix}index.html">Владимир Эглитис<small>консультант по алкогольной зависимости</small></a>
        <button class="menu-toggle" type="button" aria-controls="main-nav" aria-expanded="false" aria-label="Открыть меню">Меню</button>
        <nav id="main-nav" class="nav" aria-label="Основная навигация">{nav_html}</nav>
        <a class="header-cta" href="{prefix}contact.html">Написать Владимиру</a>
        </div></header>''',
        "header",
    )


def shell_footer(prefix: str):
    return fragment(
        f'''<footer class="site-footer"><div class="wrap">
        <div class="footer-grid">
          <div class="footer-identity"><a class="footer-name" href="{prefix}index.html">Владимир Эглитис</a>
            <small>консультант по алкогольной зависимости</small><p>Онлайн · На русском языке</p></div>
          <div class="footer-quote"><p>«Изменения начинаются<br>с честного разговора»</p></div>
          <div class="footer-contact"><a class="footer-contact-cta" href="{prefix}contact.html">Написать Владимиру</a>
            <div class="footer-channels" aria-label="Мессенджеры">
              <a href="{TELEGRAM}" target="_blank" rel="noopener noreferrer">Telegram</a>
              <a href="{WHATSAPP}" target="_blank" rel="noopener noreferrer">WhatsApp</a>
              <a href="{MAX}" target="_blank" rel="noopener noreferrer">MAX</a>
            </div><a class="footer-email" href="{EMAIL}">Email: eglvlad2025@outlook.com</a></div>
        </div>
        <div class="footer-bottom"><span>© 2026 Владимир Эглитис · Предпубликационная версия</span>
          <span class="footer-legal"><a href="{prefix}privacy.html">Политика конфиденциальности</a><span aria-hidden="true">|</span><a href="{prefix}terms.html">Условия консультаций</a></span></div>
        </div></footer>''',
        "footer",
    )


HOME = f'''<main id="main">
  <section class="hero" aria-labelledby="home-title"><div class="hero-photo" aria-hidden="true"></div>
    <div class="wrap hero-wrap"><div class="hero-copy">
      <h1 id="home-title">Есть место, <br>где можно говорить <br>честно.</h1>
      <p class="hero-sub">Консультации по алкогольной зависимости.<br>На русском языке, онлайн.</p>
      <div class="hero-actions"><a class="pill main-cta" href="contact.html">Написать Владимиру</a>
        <a class="hero-more" href="#problema">Узнать больше →</a></div>
      <div class="hero-direct" aria-label="Написать в мессенджер">
        <a href="{TELEGRAM}" target="_blank" rel="noopener noreferrer">Telegram</a>
        <a href="{WHATSAPP}" target="_blank" rel="noopener noreferrer">WhatsApp</a>
        <a href="{MAX}" target="_blank" rel="noopener noreferrer">MAX</a>
      </div>
    </div></div>
  </section>
  <section class="section warm problem-section" id="problema"><div class="wrap split problem-grid">
    <img class="visual shore" src="assets/shore.webp" alt="Тихий вечерний берег с соснами и камнями" loading="eager">
    <div class="copy"><h2>Когда алкоголь становится проблемой?</h2>
      <p>Не обязательно пить каждый день, чтобы терять контроль. Иногда проблема заметна по обещаниям, которые трудно выполнять, по отношениям с близкими или по тому, сколько места алкоголь занимает в мыслях.</p>
      <a class="text-link" href="articles/kak-ponyat-problemu.html">Читать дальше →</a></div>
  </div></section>
  <section class="section olive about-section" id="obo-mne"><div class="wrap about-grid">
    <div class="copy"><h2>Обо мне</h2>
      <p>Меня зовут Владимир Эглитис. Я консультант по алкогольной зависимости, и сам прошёл этот путь. Мой опыт трезвости с 1999 года, профессиональная работа с 2012 года.</p>
      <a class="text-link light-link" href="about.html">Подробнее обо мне →</a></div>
    <div class="portrait-placeholder" role="img" aria-label="Место для реальной фотографии Владимира"><span>Место для фотографии Владимира</span></div>
    <blockquote class="about-quote"><p>«Я знаю, как это может быть.<br>И знаю, что другой путь возможен.»</p><cite>Владимир Эглитис</cite></blockquote>
  </div></section>
  <section class="section sand consultation-section" id="konsultacii"><div class="wrap split consult-grid">
    <div class="copy"><h2>Консультации и цены</h2>
      <p>Я работаю индивидуально с людьми, которым трудно остановиться или сохранить трезвость. Консультации проходят онлайн, на русском языке.</p>
      <p>Для клиентов из России стоимость указана в рублях. Оплата через Сбер.</p>
      <a class="pill brown-pill" href="prices.html">Стоимость и формат →</a></div>
    <img class="visual desk" src="assets/desk.webp" alt="Блокнот и чашка на столе в тёплом кабинете" loading="eager">
  </div></section>
  <section class="section articles-section" id="stati"><div class="wrap">
    <div class="section-title"><div><p class="kicker">СТАТЬИ</p><h2>Материалы, которые могут быть полезны</h2></div>
      <a class="text-link light-link" href="articles.html">Все статьи →</a></div>
    <div class="article-grid">
      <article><a href="articles/kak-ponyat-problemu.html"><img src="assets/shore.webp" alt="Вечерний берег" loading="eager"><h3>Как понять, что алкоголь стал проблемой?</h3></a>
        <a class="text-link light-link" href="articles/kak-ponyat-problemu.html">Читать →</a></article>
      <article><a href="articles/kak-brosit-pit.html"><img src="assets/book.webp" alt="Книга и чашка на столе" loading="eager"><h3>Как бросить пить и не начать снова?</h3></a>
        <a class="text-link light-link" href="articles/kak-brosit-pit.html">Читать →</a></article>
    </div>
  </div></section>
</main>'''

CONTACT = f'''<main id="main">
  <section class="inner-hero"><div class="wrap"><p class="kicker">Контакты</p><h1>Написать Владимиру</h1>
    <p>Выберите удобный мессенджер. Для первого сообщения достаточно нескольких слов.</p></div></section>
  <section class="content-panel"><div class="readable contact-page"><h2>Связаться</h2>
    <p>Telegram, WhatsApp и MAX — равноправные способы связи. Медицинские подробности не нужно отправлять в первом сообщении.</p>
    <div class="channel-list primary-channels">
      <a href="{TELEGRAM}" target="_blank" rel="noopener noreferrer"><strong>Telegram ↗</strong><small>+358 46 617 08 91</small></a>
      <a href="{WHATSAPP}" target="_blank" rel="noopener noreferrer"><strong>WhatsApp ↗</strong><small>+358 46 617 08 91</small></a>
      <a href="{MAX}" target="_blank" rel="noopener noreferrer"><strong>MAX ↗</strong><small>+7 981 188 15 62</small></a>
    </div>
    <p class="contact-email">Можно также написать по email: <a href="{EMAIL}">eglvlad2025@outlook.com</a>.</p>
    <p>Ознакомительная консультация бесплатна. Для клиентов из России стоимость в рублях, оплата через Сбер. Полный прайс — на <a href="prices.html">странице стоимости</a>.</p>
    <h2>Если сейчас нужна медицинская помощь</h2>
    <p>При судорогах, галлюцинациях, выраженной спутанности или тяжёлой абстиненции обратитесь в местную службу экстренной медицинской помощи. Консультирование не заменяет медицинскую помощь.</p>
  </div></section>
</main>'''


for path in PAGES:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    prefix = "../" if path.parent.name == "articles" else ""
    if path.name == "index.html":
        soup.body["class"] = ["home"]
    soup.header.replace_with(shell_header(prefix, path.name))
    soup.footer.replace_with(shell_footer(prefix))
    css = soup.select_one('link[rel="stylesheet"]')
    css["href"] = prefix + "assets/site-v09.css"
    if path.name == "index.html":
        soup.main.replace_with(fragment(HOME, "main"))
    elif path.name == "contact.html":
        soup.main.replace_with(fragment(CONTACT, "main"))
    path.write_text(str(soup), encoding="utf-8")
    print(path.relative_to(SITE))
