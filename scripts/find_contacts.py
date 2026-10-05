"""Inventory contact URLs in the supplied current and archived text files."""
from pathlib import Path
from zipfile import ZipFile
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

root = Path(__file__).resolve().parents[1]
workspace = root.parent
download_archives = Path.home() / 'Downloads' / 'Telegram Desktop'
pattern = re.compile(r'https?://[^\s"<>]+', re.I)

def report(label, data):
    urls = sorted({u.rstrip('.,)') for u in pattern.findall(data) if any(
        token in u.lower() for token in ('max.ru', 't.me/', 'wa.me/', 'telegram.me/'))})
    if urls:
        print(label, *urls, sep='\n  ')

for path in workspace.rglob('*'):
    if '.git' in path.parts or not path.is_file():
        continue
    if path.suffix.lower() in {'.html', '.js', '.json', '.md', '.txt', '.mhtml'}:
        report(str(path.relative_to(workspace)), path.read_text(encoding='utf-8', errors='ignore'))
    elif path.suffix.lower() == '.zip':
        with ZipFile(path) as archive:
            for name in archive.namelist():
                if name.lower().endswith(('.html', '.js', '.json', '.md', '.txt')):
                    report(f'{path.name}:{name}', archive.read(name).decode('utf-8', errors='ignore'))
if download_archives.is_dir():
    for path in download_archives.glob('*.zip'):
        with ZipFile(path) as archive:
            for name in archive.namelist():
                if name.lower().endswith(('.html', '.js', '.json', '.md', '.txt')):
                    report(f'{path.name}:{name}', archive.read(name).decode('utf-8', errors='ignore'))
