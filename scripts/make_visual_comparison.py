"""Place the supplied reference next to the local desktop capture for review."""

from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT.parent / "Главная непидорская.png"
STAGE = sys.argv[1] if len(sys.argv) > 1 else "desktop-content-restored"
CURRENT = ROOT / "output/playwright" / STAGE / "home-1440x900.png"
OUT = ROOT / "output/playwright" / f"reference-vs-{STAGE}.png"

reference = Image.open(REFERENCE).convert("RGB")
current = Image.open(CURRENT).convert("RGB")
height = reference.height
current = current.resize((round(current.width * height / current.height), height), Image.Resampling.LANCZOS)
gap = 24
label_height = 56
canvas = Image.new("RGB", (reference.width + current.width + gap * 3, height + label_height + gap), "#e8ddce")
canvas.paste(reference, (gap, label_height))
canvas.paste(current, (reference.width + gap * 2, label_height))
draw = ImageDraw.Draw(canvas)
font_path = Path("C:/Windows/Fonts/arial.ttf")
font = ImageFont.truetype(str(font_path), 23) if font_path.exists() else ImageFont.load_default()
draw.text((gap, 15), "Утверждённый референс", fill="#29261f", font=font)
draw.text((reference.width + gap * 2, 15), "Текущая локальная версия · 1440 px", fill="#29261f", font=font)
OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, optimize=True)
print(OUT)
