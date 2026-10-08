"""Exercise real consent UI with isolated, fake provider SDKs; no external traffic."""
import json
import mimetypes
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from service_config import service_config, embed_service_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = dict(ga4Id='G-TEST123456', jivoId='TestWidget', jivoApproved=True,
              tawkProperty='a'*24, tawkWidget='testwidget', tawkApproved=True,
              networkEnabled=True, consentVersion='2026-10-05-v1')


class ConfigSafety(unittest.TestCase):
    def test_tawk_requires_terms_install_and_valid_pair(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            values = repo / 'services.public.json'
            values.write_text(json.dumps(dict(tawk_property_id='a'*24, tawk_widget_id='testwidget')))
            self.assertFalse(service_config(repo, preview=True)['networkEnabled'])
            with self.assertRaisesRegex(SystemExit, 'Tawk requires owner acceptance'):
                service_config(repo)
            approval = repo / 'service_approval.json'
            approval.write_text('{"tawk_terms_accepted":true}')
            with self.assertRaisesRegex(SystemExit, 'Tawk requires owner approval'):
                service_config(repo)
            approval.write_text('{"tawk_terms_accepted":true,"tawk_install_approved":true}')
            self.assertTrue(service_config(repo)['tawkApproved'])
            values.write_text('{"tawk_property_id":"not-a-property","tawk_widget_id":"testwidget"}')
            with self.assertRaisesRegex(SystemExit, 'Invalid public Tawk'):
                service_config(repo)
            values.write_text('{"tawk_property_id":"aaaaaaaaaaaaaaaaaaaaaaaa"}')
            with self.assertRaisesRegex(SystemExit, 'both public embed'):
                service_config(repo)

    def test_contract_gates_and_preview(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            values = repo / 'services.public.json'
            values.write_text(json.dumps(dict(ga4_id=CONFIG['ga4Id'], jivo_widget_id=CONFIG['jivoId'])))
            with self.assertRaisesRegex(SystemExit, 'GA4 requires'):
                service_config(repo)
            self.assertFalse(service_config(repo, preview=True)['networkEnabled'])
            (repo / 'service_approval.json').write_text('{"ga4_terms_accepted":true}')
            with self.assertRaisesRegex(SystemExit, 'Jivo requires'):
                service_config(repo)
            (repo / 'service_approval.json').write_text('{"ga4_terms_accepted":true,"jivo_dpa_confirmed":true}')
            self.assertTrue(service_config(repo)['jivoApproved'])
            values.write_text('{"ga4_id":"G-<script>","jivo_widget_id":""}')
            with self.assertRaisesRegex(SystemExit, 'Invalid public'):
                service_config(repo)


class BrowserConsent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
        options = {'executable_path': str(chrome)} if chrome.is_file() else {}
        cls.browser = cls.pw.chromium.launch(headless=True, **options)
        cls.evidence = ROOT / 'output/playwright/consent'
        cls.evidence.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.requests = []
        self.config = CONFIG.copy()
        self.noindex = False
        self.chat_fails = False
        self.errors = []
        self.context.route('**/*', self.route)
        self.page = self.context.new_page()
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.assertFalse(self.errors)
        self.context.close()

    def route(self, route):
        url = urlparse(route.request.url)
        if url.hostname in ('eglitisonline.com', 'preview.example'):
            path = ROOT / 'site' / (url.path.lstrip('/') or 'index.html')
            if path.suffix == '.html':
                soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
                embed_service_config(soup, self.config)
                soup.select_one('meta[name="robots"]')['content'] = 'noindex,nofollow' if self.noindex else 'index,follow'
                route.fulfill(body=str(soup), content_type='text/html')
            else:
                route.fulfill(body=path.read_bytes(), content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
        else:
            self.requests.append(route.request.url)
            if url.hostname == 'www.googletagmanager.com':
                route.fulfill(content_type='application/javascript', body="window.fakeAnalyticsReady=true; document.cookie='_ga=fixture;path=/'; window.addEventListener('pagehide',()=>{document.cookie='_ga_TEST123456=late-session-write;path=/;domain=eglitisonline.com';});")
            elif url.hostname == 'embed.tawk.to' and not self.chat_fails:
                route.fulfill(content_type='application/javascript', body="Object.assign(window.Tawk_API,{showWidget:()=>{},maximize:()=>window.chatOpened=true,shutdown:()=>{},hideWidget:()=>{}});document.cookie='TawkConnectionTime=fixture;path=/';localStorage.setItem('twk_test','fixture');window.Tawk_API.onLoad();")
            else:
                route.abort()

    def go(self, path='/'):
        self.page.goto('https://eglitisonline.com' + path)

    def test_no_request_before_choice_and_denial_persists(self):
        self.go()
        self.assertEqual(self.requests, [])
        self.assertEqual(self.context.cookies(), [])
        self.page.get_by_role('button', name='Без статистики', exact=True).click()
        self.go('/contact.html')
        self.assertEqual(self.requests, [])
        self.assertFalse(self.page.locator('.privacy-banner').count())

    def test_chat_launcher_visible_on_every_page_without_sdk(self):
        pages = ('/', '/about.html', '/approach.html', '/prices.html', '/articles.html',
                 '/contact.html', '/privacy.html', '/terms.html',
                 '/articles/kak-ponyat-problemu.html', '/articles/kak-brosit-pit.html')
        for width in (320, 390, 768, 1440):
            self.page.set_viewport_size(dict(width=width, height=844))
            for path in pages:
                self.go(path)
                launcher = self.page.locator('.chat-launcher')
                self.assertEqual(launcher.count(), 1)
                self.assertTrue(launcher.is_visible())
                before = launcher.bounding_box()
                self.assertGreaterEqual(before['x'], 0)
                self.assertLessEqual(before['x'] + before['width'], width)
                self.assertGreaterEqual(before['height'], 44)
                self.assertLessEqual(before['y'] + before['height'], 844)
                banner = self.page.locator('.privacy-banner')
                if banner.count():
                    rect = banner.bounding_box()
                    self.assertLessEqual(rect['y'] + rect['height'], before['y'])
                self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                self.assertAlmostEqual(launcher.bounding_box()['y'], before['y'], delta=1)
                self.page.screenshot(path=str(self.evidence / f'launcher-{width}.png'))
                launcher.click()
                self.assertTrue(self.page.locator('dialog').is_visible())
                self.assertFalse(self.page.locator('#chat-choice').is_checked())
                self.page.keyboard.press('Escape')
                self.assertTrue(launcher.evaluate('e=>e===document.activeElement'))
                self.assertEqual(self.requests, [])

    def test_analytics_redacts_url_referrer_and_contact_fields(self):
        self.go('/contact.html?email=private@example.com#health-history')
        self.page.get_by_role('button', name='Разрешить', exact=True).click()
        self.page.wait_for_function('window.fakeAnalyticsReady')
        self.page.locator('a[href^="https://wa.me/"]').first.evaluate('e=>e.addEventListener("click",v=>v.preventDefault())')
        self.page.locator('a[href^="https://wa.me/"]').first.click()
        layer = self.page.evaluate('Array.from(window.dataLayer, v=>Array.from(v))')
        serialized = json.dumps(layer, default=str)
        for private in ('private@example', 'health-history', '358466170891', 'wa.me', 'link_url'):
            self.assertNotIn(private, serialized)
        events = [v for v in layer if v[0] == 'event']
        self.assertEqual(events[0][1], 'page_view')
        contact = next(v for v in events if v[1] == 'contact_click')
        self.assertEqual(contact[2]['contact_method'], 'whatsapp')
        self.assertEqual(contact[2]['page_location'], 'https://eglitisonline.com/contact.html')
        self.assertEqual(len(self.requests), 1)
        self.page.get_by_role('button', name='Настройки приватности', exact=True).click()
        self.page.get_by_role('button', name='Отклонить всё', exact=True).click()
        self.page.wait_for_load_state()
        self.assertEqual(len(self.requests), 1)
        self.assertIsNone(self.page.evaluate('window.fakeAnalyticsReady || null'))
        self.assertFalse(any(v['name'].startswith('_ga') for v in self.context.cookies()))

    def test_expired_choice_and_unknown_referrer_are_discarded(self):
        self.context.add_init_script("localStorage.setItem('eglitisonline.privacy',JSON.stringify({version:'old',analytics:true,time:Date.now()}));")
        self.page.goto('https://eglitisonline.com/', referer='https://private.example/health?email=private@example.com')
        self.assertEqual(self.requests, [])
        self.page.get_by_role('button', name='Разрешить', exact=True).click()
        self.page.wait_for_function('window.fakeAnalyticsReady')
        self.assertEqual(self.page.evaluate("Array.from(dataLayer).find(v=>v[0]==='event')[2].page_referrer"), '')

    def test_campaign_attribution_uses_only_approved_values(self):
        self.go('/?utm_source=telegram&utm_medium=social&utm_campaign=launch_2026&utm_term=private-health-text')
        self.page.get_by_role('button', name='Разрешить', exact=True).click()
        self.page.wait_for_function('window.fakeAnalyticsReady')
        config = self.page.evaluate("Array.from(dataLayer).find(v=>v[0]==='config')[2]")
        self.assertEqual(config['campaign_source'], 'telegram')
        self.assertEqual(config['campaign_name'], 'launch_2026')
        self.assertNotIn('private-health-text', json.dumps(config))
        self.assertEqual(self.page.url, 'https://eglitisonline.com/')
        self.go('/?utm_source=private-health-text&utm_campaign=private-health-text')
        self.page.wait_for_function('window.fakeAnalyticsReady')
        config = self.page.evaluate("Array.from(dataLayer).find(v=>v[0]==='config')[2]")
        self.assertNotIn('campaign_source', config)
        self.assertNotIn('campaign_name', config)

    def test_wrong_origin_never_connects(self):
        self.page.goto('https://preview.example/')
        self.page.get_by_role('button', name='Разрешить', exact=True).click()
        self.assertEqual(self.requests, [])

    def test_failed_chat_cannot_survive_withdrawal(self):
        self.chat_fails = True
        self.go()
        self.page.get_by_role('button', name='Без статистики', exact=True).click()
        self.page.get_by_role('button', name='Чат на сайте', exact=True).first.click()
        self.page.locator('#chat-choice').check()
        self.page.get_by_role('button', name='Открыть чат', exact=True).click()
        self.page.get_by_text('Чат не загрузился.', exact=False).wait_for()
        self.page.get_by_role('button', name='Настройки приватности', exact=True).click()
        self.page.get_by_role('button', name='Отклонить всё', exact=True).click()
        self.page.wait_for_load_state()
        self.assertFalse(self.page.locator('script[src*="embed.tawk.to"]').count())
        self.assertEqual(len(self.requests), 1)

    def test_chat_needs_separate_consent_and_withdrawal_unloads(self):
        self.go('/contact.html?secret=private#message')
        self.page.get_by_role('button', name='Без статистики', exact=True).click()
        self.page.get_by_role('button', name='Чат на сайте', exact=True).first.click()
        self.page.get_by_role('button', name='Открыть чат', exact=True).click()
        self.assertTrue(self.page.locator('.consent-error').is_visible())
        self.assertEqual(self.requests, [])
        self.page.locator('#chat-choice').check()
        self.page.get_by_role('button', name='Открыть чат', exact=True).click()
        self.page.wait_for_function('window.chatOpened')
        self.assertFalse(self.page.locator('.chat-launcher').is_visible())
        self.assertEqual(self.page.url, 'https://eglitisonline.com/contact.html')
        self.assertFalse(any('jivosite' in v for v in self.requests))
        self.assertEqual(len(self.requests), 1)
        self.page.get_by_role('button', name='Настройки приватности', exact=True).click()
        self.page.get_by_role('button', name='Отклонить всё', exact=True).click()
        self.page.wait_for_load_state()
        self.assertIsNone(self.page.evaluate('window.chatOpened || null'))
        self.assertFalse(any(v['name'].startswith(('Tawk','twk')) for v in self.context.cookies()))
        self.assertIsNone(self.page.evaluate("localStorage.getItem('twk_test')"))
        self.assertEqual(len(self.requests), 1)

    def test_preview_and_noindex_never_connect(self):
        for preview, noindex in ((True, False), (False, True)):
            self.config['networkEnabled'] = not preview
            self.noindex = noindex
            self.go()
            button = self.page.get_by_role('button', name='Разрешить', exact=True)
            if button.count(): button.click()
            self.page.get_by_role('button', name='Чат на сайте', exact=True).first.click()
            self.page.locator('#chat-choice').check()
            self.page.get_by_role('button', name='Открыть чат', exact=True).click()
            self.assertEqual(self.requests, [])

    def test_mobile_dialog_geometry_keyboard_and_accessibility(self):
        axe = ROOT / 'output/qa-tools/node_modules/axe-core/axe.min.js'
        for width in (320, 390, 768, 1440):
            self.page.set_viewport_size(dict(width=width, height=844))
            self.go()
            self.page.screenshot(path=str(self.evidence / f'banner-{width}.png'), full_page=True)
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
            self.page.get_by_role('button', name='Настройки', exact=True).click()
            rect = self.page.locator('dialog').bounding_box()
            self.assertGreaterEqual(rect['x'], 0)
            self.assertLessEqual(rect['x'] + rect['width'], width)
            if axe.is_file():
                self.page.add_script_tag(path=str(axe))
                violations = self.page.evaluate('async()=> (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))')
                self.assertEqual(violations, [])
            self.page.screenshot(path=str(self.evidence / f'dialog-{width}.png'))
            self.page.keyboard.press('Escape')
            self.assertFalse(self.page.locator('dialog').is_visible())
            self.assertEqual(self.page.evaluate('document.activeElement.textContent'), 'Настройки')
        self.assertEqual(self.requests, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
