"""Exercise public UI, links, responsive layouts and accessibility; save evidence.

External navigation is intercepted during click tests. Real messenger landing
pages are checked separately in the authenticated user browser; no messages sent.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['', 'about.html', 'approach.html', 'prices.html', 'articles.html',
         'contact.html', 'privacy.html', 'terms.html',
         'articles/kak-ponyat-problemu.html', 'articles/kak-brosit-pit.html']
SIZES = [(320,700),(360,800),(375,812),(390,844),(412,915),(430,932),
         (768,1024),(1024,768),(1440,900),(1920,1080)]


def audit(base, output, engines, clicks=True, quick=False):
    output.mkdir(parents=True, exist_ok=True)
    report = {'base':base, 'layouts':[], 'issues':[], 'clicks':[], 'controls':[],
              'accessibility':[], 'http_errors':[], 'js_errors':[]}
    origin = urlparse(base).netloc
    axe = ROOT / 'output/qa-tools/node_modules/axe-core/axe.min.js'
    with sync_playwright() as playwright:
        for engine in engines:
            launcher = getattr(playwright, 'chromium' if engine == 'edge' else engine)
            options = {}
            chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
            if engine == 'chromium' and chrome.is_file():
                options['executable_path'] = str(chrome)
            if engine == 'edge':
                options['channel'] = 'msedge'
            browser = launcher.launch(headless=True, **options)
            context = browser.new_context(reduced_motion='reduce')
            page = context.new_page()
            page.set_default_timeout(8000)
            page.on('pageerror', lambda error: report['js_errors'].append(str(error)))
            def response_check(response):
                if response.status >= 400:
                    report['http_errors'].append({'url':response.url,'status':response.status})
            page.on('response', response_check)
            sizes = SIZES if engine == 'chromium' and not quick else [(390,844),(1440,900)]
            try:
                for width,height in sizes:
                    page.set_viewport_size({'width':width,'height':height})
                    for route in PAGES:
                        page.goto(urljoin(base,route), wait_until='load')
                        for image in page.locator('img').all():
                            image.scroll_into_view_if_needed()
                            image.evaluate('el=>el.decode()')
                        page.evaluate('window.scrollTo(0,0)')
                        geometry = page.evaluate('''()=>({scroll:document.documentElement.scrollWidth,
                            overflow:[...document.querySelectorAll('main *,.site-head *,.site-footer *')]
                            .filter(e=>{const r=e.getBoundingClientRect();return r.width&&getComputedStyle(e).display!=='none'&&(r.right>innerWidth+1||r.left< -1)})
                            .slice(0,10).map(e=>({tag:e.tagName,class:e.className,text:e.innerText?.slice(0,80)})),
                            brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src)})''')
                        result={'engine':engine,'page':route or '/','width':width,**geometry}
                        report['layouts'].append(result)
                        if geometry['scroll'] > width or geometry['overflow'] or geometry['brokenImages']:
                            report['issues'].append(result)
                        page.screenshot(path=str(output/f'{engine}-{(route or "home").replace("/","-").replace(".html","")}-{width}.png'),full_page=True)
                        if width in (390,1440) and axe.is_file() and engine=='chromium':
                            page.add_script_tag(path=str(axe))
                            violations=page.evaluate('async()=> (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})).violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))')
                            report['accessibility'].append({'page':route or '/','width':width,'violations':violations})
                        # All five native FAQ controls, pointer and keyboard.
                        for details in page.locator('details').all():
                            summary=details.locator('summary')
                            summary.click()
                            assert details.get_attribute('open') is not None
                            summary.focus();page.keyboard.press('Enter')
                            assert details.get_attribute('open') is None
                            report['controls'].append({'engine':engine,'page':route,'width':width,'control':summary.inner_text(),'result':'pass'})
                        if width <= 920:
                            toggle=page.locator('.menu-toggle')
                            toggle.focus();page.keyboard.press('Enter')
                            assert toggle.get_attribute('aria-expanded')=='true'
                            assert page.locator('#main-nav').is_visible()
                            page.keyboard.press('Escape')
                            assert toggle.get_attribute('aria-expanded')=='false'
                            assert toggle.evaluate('el=>document.activeElement===el')
                            toggle.click()
                            # Footer lies outside the menu overlay; heading may be covered.
                            page.locator('.footer-name').click()
                            assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
                            report['controls'].append({'engine':engine,'page':route,'width':width,'control':'menu keyboard/Escape/outside navigation','result':'pass'})
                    print(f'{engine}: ten pages/layouts and controls at {width}px',flush=True)
                if clicks and engine=='chromium':
                    # Isolate provider side effects but verify each site's real link activation.
                    def provider_route(route):
                        if urlparse(route.request.url).netloc != origin:
                            route.fulfill(status=200,content_type='text/html',body='<p>External navigation test</p>')
                        else: route.continue_()
                    context.route('**/*',provider_route)
                    for width,height in [(390,844),(1440,900)]:
                        page.set_viewport_size({'width':width,'height':height})
                        for route in PAGES:
                            current=urljoin(base,route)
                            page.goto(current,wait_until='load')
                            count=page.locator('a[href]').count()
                            for index in range(count):
                                page.goto(current,wait_until='load')
                                link=page.locator('a[href]').nth(index)
                                href=link.get_attribute('href');text=link.inner_text()
                                if width<=920 and link.evaluate('el=>!!el.closest("#main-nav")'):
                                    page.locator('.menu-toggle').click()
                                if not link.is_visible() and 'skip' not in (link.get_attribute('class') or ''):
                                    report['clicks'].append({'page':route,'width':width,'href':href,'result':'responsive-hidden'})
                                    continue
                                if 'skip' in (link.get_attribute('class') or ''):link.focus()
                                expected=urljoin(current,href)
                                if href.startswith('mailto:'):
                                    # Test activation/URI, never compose or send an email.
                                    link.evaluate('el=>el.addEventListener("click",event=>{event.preventDefault();document.documentElement.dataset.mailActivation=el.href},{once:true})')
                                    link.click()
                                    assert page.locator('html').get_attribute('data-mail-activation')==href
                                elif urlparse(expected).netloc != origin:
                                    with page.expect_popup() as pending:link.click()
                                    popup=pending.value
                                    popup.wait_for_load_state()
                                    assert popup.url==expected,(expected,popup.url)
                                    popup.close()
                                else:
                                    link.click()
                                    target=page.url
                                    # Canonical homepage redirect and local preview index both allowed.
                                    expected_path=urlparse(expected).path
                                    if expected_path.endswith('/index.html'):expected_path=expected_path[:-10]
                                    actual_path=urlparse(target).path
                                    if actual_path.endswith('/index.html'):actual_path=actual_path[:-10]
                                    assert actual_path==expected_path,(expected,target)
                                    if href.startswith('#'):assert page.locator('#main').evaluate('el=>document.activeElement===el')
                                report['clicks'].append({'page':route or '/','width':width,'href':href,'text':text,'result':'pass'})
                            print('All links activated:',route or '/',width,flush=True)
            except Exception as error:
                report['issues'].append({'engine':engine,'exception':str(error)})
                raise
            finally:
                (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                browser.close()
    violations=sum(len(row['violations']) for row in report['accessibility'])
    assert not report['issues'] and not report['http_errors'] and not report['js_errors'] and not violations, 'Audit found issues; inspect results.json'
    print(f'PASS: {len(report["layouts"])} page/layout combinations, {len(report["clicks"])} link records, {len(report["controls"])} controls, {len(report["accessibility"])} accessibility checks',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',default='https://eglitisonline.com/')
    parser.add_argument('--output',type=Path,default=ROOT/'output/playwright/full-audit')
    parser.add_argument('--engines',nargs='+',choices=['chromium','firefox','webkit','edge'],default=['chromium','webkit'])
    parser.add_argument('--no-clicks',action='store_true')
    parser.add_argument('--quick',action='store_true')
    args=parser.parse_args()
    audit(args.base.rstrip('/')+'/',args.output,args.engines,not args.no_clicks,args.quick)
