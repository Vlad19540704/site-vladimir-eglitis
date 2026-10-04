"""Import supplied legal HTML as closed-index staging drafts with project shell."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

SITE = Path(__file__).resolve().parents[1] / "site"
SOURCE_PAGES = {
    "privacy.html": ("privacy.html", "Политика конфиденциальности"),
    "consultation-terms.html": ("terms.html", "Условия консультаций"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch_zip", type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.patch_zip) as archive:
        for source, (target, title) in SOURCE_PAGES.items():
            supplied = BeautifulSoup(archive.read(source).decode("utf-8"), "html.parser")
            main = supplied.main
            if main is None or main.select_one("h1") is None:
                raise SystemExit(f"Missing legal content: {source}")
            heading = main.select_one("h1")
            heading.extract()
            draft = BeautifulSoup(
                f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
                <meta name="viewport" content="width=device-width,initial-scale=1">
                <meta name="robots" content="noindex,nofollow">
                <meta name="description" content="{title} Владимира Эглитиса.">
                <title>{title} — Владимир Эглитис</title>
                <link rel="stylesheet" href="assets/site-v09.css">
                <link rel="icon" type="image/svg+xml" href="assets/favicon.svg"></head>
                <body><header class="site-head"></header>
                <main id="main"><section class="inner-hero"><div class="wrap"><h1>{title}</h1></div></section>
                <section class="content-panel"><div class="readable legal-content"></div></section></main>
                <footer class="site-footer"></footer><script defer src="assets/site-v08.js"></script>
                </body></html>''',
                "html.parser",
            )
            container = draft.select_one(".legal-content")
            for child in list(main.contents):
                container.append(child)
            (SITE / target).write_text(str(draft), encoding="utf-8")
            print(f"Staged supplied {source} as {target}, noindex")


if __name__ == "__main__":
    main()
