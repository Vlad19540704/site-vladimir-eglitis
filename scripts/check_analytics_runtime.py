"""Production consent check; --live opts a disposable test browser into GA4.

This sends technical test page/click events, never a message or a lead claim.
Raw request bodies/client IDs are inspected in memory, never saved in reports.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check(live=False):
    providers = []
    collections = []
    collection_statuses = []
    errors = []
    with sync_playwright() as pw:
        chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
        browser = pw.chromium.launch(headless=True, **({'executable_path':str(chrome)} if chrome.is_file() else {}))
        context = browser.new_context()
        if live:
            context.add_init_script("""window.dataLayer=[];const push=window.dataLayer.push;
                window.dataLayer.push=function(...items){for(const v of items){
                  if((v[0]==='config'||v[0]==='event')&&v[2]) v[2].debug_mode=true;
                }return push.apply(this,items);};""")
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        def request(req):
            host = urlparse(req.url).hostname
            if host != 'eglitisonline.com':
                providers.append(host)
                raw = req.url + (req.post_data or '')
                assert 'qa-hidden-text' not in raw and 'qa-test%40example' not in raw and 'qa-test@example' not in raw, 'Arbitrary URL content leaked'
                if urlparse(req.url).path.endswith('/collect'):
                    query = parse_qs(urlparse(req.url).query)
                    for line in (req.post_data or '').splitlines() or ['']:
                        event = {**query, **parse_qs(line)}
                        # Persist only whitelisted harmless fields, never client/session IDs.
                        collections.append({key: value for key,value in event.items() if key in ('tid','en','dl','dt','dr','ep.contact_method','ep.placement')})
        page.on('request', request)
        page.on('response', lambda response: collection_statuses.append(response.status)
                if urlparse(response.url).path.endswith('/collect') else None)
        page.goto('https://eglitisonline.com/contact.html?text=qa-hidden-text&email=qa-test%40example.com#qa-hidden-text')
        page.wait_for_timeout(1500)
        assert not providers, 'Provider loaded before visitor consent'
        assert not context.cookies(), 'Provider cookie exists before visitor consent'
        page.get_by_role('button',name='Без статистики',exact=True).click()
        page.reload()
        page.wait_for_timeout(500)
        assert not providers, 'Provider loaded after denial'
        page.get_by_role('button',name='Настройки приватности',exact=True).click()
        page.locator('#analytics-choice').check()
        if live:
            page.get_by_role('button',name='Сохранить выбор',exact=True).click()
            page.wait_for_function("performance.getEntriesByType('resource').some(e=>e.name.includes('/collect'))",timeout=30000)
            link = page.locator('main a[href^="https://wa.me/"]').first
            link.evaluate('e=>e.addEventListener("click",v=>v.preventDefault())')
            link.click()
            page.wait_for_timeout(3000)
            assert any(v.get('en') == ['page_view'] for v in collections), 'No GA4 page_view transport'
            assert any(v.get('en') == ['contact_click'] for v in collections), 'No GA4 contact_click transport'
            for event in collections:
                if 'dl' in event: assert event['dl'] == ['https://eglitisonline.com/contact.html']
                if 'dt' in event: assert event['dt'] == ['Контакты']
            page.get_by_role('button',name='Настройки приватности',exact=True).click()
        before = len(providers)
        if live:
            with page.expect_navigation():
                page.get_by_role('button',name='Отклонить всё',exact=True).click()
        else:
            page.get_by_role('button',name='Отклонить всё',exact=True).click()
        page.wait_for_timeout(1000)
        assert len(providers) == before, 'Provider resumed after withdrawal'
        assert not any(v['name'].startswith('_ga') for v in context.cookies()), 'Analytics cookies survived withdrawal'
        assert not errors, errors
        report = dict(live=live, no_requests_before_consent=True, denial_persists=True,
                      withdrawal_stops_requests=True, cookies_cleared=True, events=collections,
                      collection_statuses=collection_statuses,
                      provider_hosts=sorted(set(providers)), jivo_loaded=any('jivo' in (host or '') for host in providers))
        assert not report['jivo_loaded'], 'Unapproved Jivo must remain disabled'
        output = ROOT / 'output/analytics-runtime.json'
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        browser.close()
        print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    check(parser.parse_args().live)
