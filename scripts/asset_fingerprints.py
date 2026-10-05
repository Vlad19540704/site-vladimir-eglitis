"""Content-addressed asset names keep long browser caching safe after a release."""

import hashlib
from pathlib import Path


def asset_map(site, names):
    result = {}
    for name in names:
        if not name.endswith(('.css', '.js')):
            digest = hashlib.sha256((site / 'assets' / name).read_bytes()).hexdigest()[:12]
            result[name] = f'{Path(name).stem}.{digest}{Path(name).suffix}'
    for name in names:
        if name.endswith(('.css', '.js')):
            content = rewrite_assets((site / 'assets' / name).read_text(encoding='utf-8'), result).encode('utf-8')
            digest = hashlib.sha256(content).hexdigest()[:12]
            result[name] = f'{Path(name).stem}.{digest}{Path(name).suffix}'
    return result


def rewrite_assets(text, names):
    # Full asset filename tokens only: avoid touching source prose or a different variant.
    import re
    pattern = re.compile(r'(?<![\w.-])(' + '|'.join(re.escape(name) for name in sorted(names, key=len, reverse=True)) + r')(?=["\s\),?]|$)')
    return pattern.sub(lambda match: names[match.group(1)], text)
