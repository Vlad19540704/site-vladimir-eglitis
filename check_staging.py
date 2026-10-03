from pathlib import Path
from bs4 import BeautifulSoup
import sys
root=Path(__file__).parent/'site'
errors=[]
html=list(root.rglob('*.html'))
for f in html:
    soup=BeautifulSoup(f.read_text(encoding='utf8'),'html.parser')
    headings=soup.find_all('h1')
    if len(headings)!=1: errors.append(f'{f.name}: expected one h1, got {len(headings)}')
    meta=soup.find('meta',attrs={'name':'robots'})
    if not meta or 'noindex' not in meta.get('content',''): errors.append(f'{f.name}: STAGING noindex missing')
    for e in soup.select('[href],[src]'):
        link=e.get('href',e.get('src','')).split('#')[0].split('?')[0]
        if not link or link.startswith(('https:','http:','mailto:','tel:','data:','#')): continue
        target=(f.parent/link).resolve()
        if not target.is_file(): errors.append(f'{f.relative_to(root)} broken: {link}')
articles=list((root/'articles').glob('*.html'))
if len(articles)!=2:errors.append('Only 2 approved article pages allowed in staging')
index=(root/'articles.html').read_text(encoding='utf8')
for approved in ['kak-brosit-pit','kak-ponyat-problemu']:
    if approved not in index: errors.append(f'{approved} missing from article listing')
for rejected in ['sryv-nachinaetsya-ranshe','aa-i-konsultant','zhit-trezvo']:
    if rejected in index:errors.append(f'unapproved {rejected} listed')
print(f'HTML pages: {len(html)}; article pages: {len(articles)}; issues: {len(errors)}')
for err in errors:print('ERROR',err)
sys.exit(1 if errors else 0)
