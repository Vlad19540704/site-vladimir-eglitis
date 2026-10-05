"""Create delivery encodings of approved photos; keep the PNG masters unchanged."""

from pathlib import Path
from PIL import Image

assets = Path(__file__).resolve().parents[1] / 'site/assets'
for name in ('hero-sunset-v1', 'portrait-v1'):
    source = assets / (name + '.png')
    output = source.with_suffix('.webp')
    with Image.open(source) as original:
        assert original.convert('RGBA').getchannel('A').getextrema() == (255, 255), 'Expected opaque photo'
        pixels = original.convert('RGB')
        pixels.save(output, format='WEBP', quality=94, method=6,
                    icc_profile=original.info.get('icc_profile', b''))
    with Image.open(output) as encoded:
        assert encoded.size == pixels.size
    if name == 'portrait-v1':
        for width in (480, 800):
            resized = pixels.resize((width, round(pixels.height * width / pixels.width)), Image.Resampling.LANCZOS)
            resized.save(assets / f'{name}-{width}.webp', 'WEBP', quality=94, method=6)
    print(f'{name}: {source.stat().st_size} -> {output.stat().st_size} bytes; original dimensions, PNG master retained')
