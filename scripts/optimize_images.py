"""Lossless format conversion; verify every decoded pixel against approved PNGs."""

from pathlib import Path
from PIL import Image, ImageChops

assets = Path(__file__).resolve().parents[1] / 'site/assets'
for name in ('hero-sunset-v1', 'portrait-v1'):
    source = assets / (name + '.png')
    output = source.with_suffix('.webp')
    with Image.open(source) as original:
        assert original.convert('RGBA').getchannel('A').getextrema() == (255, 255), 'Expected opaque photo'
        pixels = original.convert('RGB')
        pixels.save(output, format='WEBP', lossless=True, method=6,
                    icc_profile=original.info.get('icc_profile', b''))
    with Image.open(output) as encoded:
        assert ImageChops.difference(pixels, encoded.convert('RGB')).getbbox() is None
    print(f'{name}: {source.stat().st_size} -> {output.stat().st_size} bytes; identical pixels')
