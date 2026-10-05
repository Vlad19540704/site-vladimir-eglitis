"""Protect GitHub/server parity and truthful article metadata."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import date
from bs4 import BeautifulSoup

from git_release_guard import published_revision
from seo_metadata import enrich

ROOT = Path(__file__).resolve().parents[1]


class ReleaseSafety(unittest.TestCase):
    def test_uncommitted_changes_cannot_deploy(self):
        with patch('git_release_guard.subprocess.check_output', return_value=' M site/index.html\n'):
            with self.assertRaisesRegex(SystemExit, 'Commit and push'):
                published_revision(ROOT)

    def test_unpushed_commit_cannot_deploy(self):
        with patch('git_release_guard.subprocess.check_output', side_effect=['', 'a' * 40, 'site-prepublication', 'b' * 40 + '\trefs/heads/site-prepublication']):
            with self.assertRaisesRegex(SystemExit, 'differs from the GitHub'):
                published_revision(ROOT)

    def test_published_clean_commit_can_deploy(self):
        revision = 'a' * 40
        with patch('git_release_guard.subprocess.check_output', side_effect=['', revision, 'site-prepublication', revision + '\trefs/heads/site-prepublication']):
            self.assertEqual(published_revision(ROOT), revision)

    def test_article_metadata_matches_content_and_actual_date(self):
        for rel in ('articles/kak-ponyat-problemu.html', 'articles/kak-brosit-pit.html'):
            soup = BeautifulSoup((ROOT / 'site' / rel).read_text(encoding='utf-8'), 'html.parser')
            original = str(soup.main)
            enrich(soup, rel, 'eglitisonline.com', ROOT / 'site', date(2026, 10, 5))
            graph = json.loads(soup.select_one('script[type="application/ld+json"]').string)['@graph']
            article = next(node for node in graph if node['@type'] == 'Article')
            self.assertEqual(article['datePublished'], '2026-10-05')
            self.assertEqual(article['headline'], soup.h1.get_text(' ', strip=True))
            self.assertEqual(article['author']['url'], 'https://eglitisonline.com/about.html')
            # Only image dimensions/decoding can change in main; authored words cannot.
            after = BeautifulSoup(str(soup.main), 'html.parser')
            before = BeautifulSoup(original, 'html.parser')
            self.assertEqual(after.get_text(), before.get_text())


if __name__ == '__main__':
    unittest.main()
