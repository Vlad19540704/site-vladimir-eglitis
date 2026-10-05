"""Vendor compact monochrome messenger marks for the site's calm palette."""

from io import BytesIO
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ASSETS = Path(__file__).resolve().parents[1] / "site" / "assets"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


telegram_zip = zipfile.ZipFile(BytesIO(fetch(
    "https://telegram.org/file/464001088/1/bI7AJLo7oX4.287931.zip/374fe3b0a59dc60005"
)))
telegram = ET.fromstring(telegram_zip.read("Logo.svg"))
ns = {"svg": "http://www.w3.org/2000/svg"}
plane = next(path.attrib["d"] for path in telegram.findall(".//svg:path", ns) if path.attrib.get("id") == "Path-3")
(ASSETS / "icon-telegram.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="140 260 640 540"><path d="{plane}"/></svg>',
    encoding="utf-8",
)

max_zip = zipfile.ZipFile(BytesIO(fetch("https://st.max.ru/brandbook/max-white.zip")))
(ASSETS / "icon-max.svg").write_bytes(max_zip.read("Max white.svg"))

whatsapp = fetch("https://cdn.jsdelivr.net/npm/simple-icons@v15/icons/whatsapp.svg")
(ASSETS / "icon-whatsapp.svg").write_bytes(whatsapp)

for path in ASSETS.glob("icon-*.svg"):
    ET.parse(path)
    print(path.name, path.stat().st_size)
