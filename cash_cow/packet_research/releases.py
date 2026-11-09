"""Select manually verified official-release vintages as known at a cutoff.

No fetching or extraction is implied. URLs/hashes are provenance assertions to
verify against saved source bytes, not proof of official authorship by themselves.
"""
from datetime import datetime, timedelta
import math
import re
from zoneinfo import ZoneInfo

from cash_cow.paper.client import timestamp
from .history import digest

METRICS = {
    'payroll_change': ('empsit', 'thousand_persons'),
    'unemployment_rate': ('empsit', 'percent'),
    'cpi_mom': ('cpi', 'percent'),
    'ppi_mom': ('ppi', 'percent'),
}
FIELDS = {'release_id', 'metric', 'period', 'unit', 'value', 'source_url',
          'source_sha256', 'published_at', 'first_observed_at', 'vintage_at'}


def select_releases(records, as_of):
    cutoff = timestamp(as_of)
    if not isinstance(records, list):
        raise ValueError('invalid_release_collection')
    selected, seen = {}, {}
    excluded_future = excluded_old = 0
    for record in records:
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ValueError('invalid_release_fields')
        if (not isinstance(record['release_id'], str)
                or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', record['release_id'])
                or not isinstance(record['metric'], str) or record['metric'] not in METRICS):
            raise ValueError('invalid_release_identity')
        family, unit = METRICS[record['metric']]
        if record['unit'] != unit:
            raise ValueError('invalid_release_unit')
        value = record['value']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('invalid_release_value')
        if record['metric'] == 'unemployment_rate' and not 0 <= value <= 100:
            raise ValueError('invalid_release_value')
        period = record['period']
        if not isinstance(period, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
            raise ValueError('invalid_release_period')
        published, observed, vintage = [timestamp(record[k]) for k in
                                        ('published_at', 'first_observed_at', 'vintage_at')]
        if not published <= vintage <= observed:
            raise ValueError('invalid_release_timestamps')
        pub_day = published.astimezone(ZoneInfo('America/New_York')).date()
        if period > pub_day.strftime('%Y-%m'):
            raise ValueError('future_release_period')
        expected = f'https://www.bls.gov/news.release/archives/{family}_{pub_day:%m%d%Y}.htm'
        if record['source_url'] != expected:
            raise ValueError('unsupported_release_source')
        if not isinstance(record['source_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', record['source_sha256']):
            raise ValueError('invalid_source_hash')
        key = (record['metric'], period)
        vintage_key = (*key, vintage)
        hashed = digest(record)
        if vintage_key in seen:
            if seen[vintage_key] != hashed:
                raise ValueError('conflicting_release_vintage')
            continue
        seen[vintage_key] = hashed
        if observed > cutoff:
            excluded_future += 1
            continue
        if cutoff-published > timedelta(days=7):
            excluded_old += 1
            continue
        if key not in selected or vintage > timestamp(selected[key]['vintage_at']):
            selected[key] = dict(record)
    return {'values': [selected[key] for key in sorted(selected)],
            'excluded_not_yet_observed': excluded_future, 'excluded_stale': excluded_old,
            'availability': 'available' if selected else 'unavailable',
            'limits': 'Manually verified source assertions; no automatic retrieval, consensus surprise, directional signal or source authenticity guarantee.'}
