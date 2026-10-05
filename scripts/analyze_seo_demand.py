"""Recompute the bounded Google Trends evidence; these are indices, not volumes."""

import csv
import json
from pathlib import Path
from statistics import mean


def analyze():
    evidence = Path(__file__).resolve().parents[1] / 'seo/evidence'
    timeline = list(csv.reader((evidence / 'google-trends-timeline-2026-10-05.csv').read_text(encoding='utf-8-sig').splitlines()))
    rows = [row for row in timeline if len(row) == 3 and row[0][:4].isdigit()]
    related = list(csv.reader((evidence / 'google-trends-related-2026-10-05.csv').read_text(encoding='utf-8-sig').splitlines()))
    first = next(i for i, row in enumerate(related) if row == ['TOP']) + 1
    last = next(i for i, row in enumerate(related) if row == ['RISING'])
    top = [{'query': row[0], 'index': int(row[1])} for row in related[first:last] if len(row) == 2]
    assert len(rows) >= 50 and top[0]['index'] == 100
    return {
        'country': 'RU', 'category': 'all', 'search': 'web', 'units': 'relative_index_0_100',
        'downloaded_on': '2026-10-05', 'window': '2025-10-05/2026-10-05',
        'first_week': rows[0][0], 'last_week': rows[-1][0], 'weeks': len(rows),
        'average_indices': {'алкогольная зависимость': round(mean(int(r[1]) for r in rows), 2),
                            'как бросить пить': round(mean(int(r[2]) for r in rows), 2)},
        'top_related_to_quit_drinking': top,
        'limitations': ['Google Trends is sampled and normalized; repeated exports can vary.',
                        'The last week is incomplete; zero may indicate insufficient data.',
                        'This is a seed-specific list, not all alcohol-related searches.',
                        'No monthly search volumes or expected leads are established.'],
    }


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
