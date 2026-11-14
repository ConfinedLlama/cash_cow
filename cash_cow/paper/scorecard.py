"""Read-only paper scorecard; reference prices are never trading inputs."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from cash_cow.daily_report import load_performance
from .client import PaperClient, iso, timestamp
from . import decision_audit, health
from .broker_audit import finite

ROOT = Path(__file__).resolve().parents[2]
NY = ZoneInfo('America/New_York')
START, END = date(2026, 11, 4), date(2026, 12, 2)
SOURCE = 'Alpaca GET /v2/stocks/bars; SPY; 1Min; iex; raw'


def execution_counts(state):
    """Count cumulative order fills once, never count repeated polling as fills."""
    orders = state['orders']
    if not isinstance(orders, dict):
        raise ValueError('Malformed order ledger')
    result = {'durable_intents': len(orders), 'broker_responses': 0,
              'orders_with_fills': 0, 'filled_buy_orders': 0, 'filled_sell_orders': 0,
              'filled_buy_quantity': 0.0, 'filled_sell_quantity': 0.0}
    for cid, order in orders.items():
        payload = order['payload']
        side = payload['side']
        requested = finite(payload['qty'])
        if side not in ('buy', 'sell') or requested <= 0 or payload['client_order_id'] != cid:
            raise ValueError('Invalid intent')
        broker = order.get('broker')
        if broker is None:
            continue  # Intent persisted before POST is not an acknowledged order.
        if any(broker.get(k) != payload[k] for k in ('client_order_id', 'side', 'symbol')):
            raise ValueError('Intent and broker response disagree')
        filled = finite(broker['filled_qty'])
        if not 0 <= filled <= requested or finite(broker['qty']) != requested:
            raise ValueError('Invalid cumulative fill')
        result['broker_responses'] += 1
        if filled:
            if finite(broker['filled_avg_price']) <= 0:
                raise ValueError('Invalid fill price')
            result['orders_with_fills'] += 1
            result[f'filled_{side}_orders'] += 1
            result[f'filled_{side}_quantity'] += filled
    return result


def interval(row):
    day = date.fromisoformat(row['date'])
    if not START <= day <= END:
        raise ValueError('Outside registered paper reference window')
    opening = datetime.fromisoformat(f"{day}T{row['open']}").replace(tzinfo=NY)
    closing = datetime.fromisoformat(f"{day}T{row['close']}").replace(tzinfo=NY)
    if opening.hour != 9 or opening.minute != 30 or not opening < closing:
        raise ValueError('Invalid regular session')
    if closing.hour not in (13, 16) or closing.minute != 0:
        raise ValueError('Unrecognized session close')
    return opening, closing


def reference(row, bars):
    """Independent USD 2,000 day; missing boundaries never become zero return."""
    opening, closing = interval(row)
    indexed = {}
    for bar in bars:
        at = timestamp(bar['t'])
        if at in indexed or not opening <= at < closing or at.second or at.microsecond:
            raise ValueError('Duplicate or out-of-session minute')
        for field in ('o', 'h', 'l', 'c', 'v'):
            value = bar[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Invalid bar number')
        if not 0 < bar['l'] <= min(bar['o'], bar['c']) <= max(bar['o'], bar['c']) <= bar['h'] or bar['v'] <= 0:
            raise ValueError('Invalid bar range or volume')
        indexed[at] = bar
    last = closing - timedelta(minutes=1)
    if opening not in indexed or last not in indexed:
        return {'status': 'missing_boundary_minutes', 'return': None, 'modeled_cost_usd': None}
    entry, exit_price = Decimal(str(indexed[opening]['o'])), Decimal(str(indexed[last]['c']))
    qty = int((Decimal('1899') / entry).to_integral_value(rounding=ROUND_FLOOR))
    fee = lambda price: max(Decimal('.40'), Decimal('.0035') * qty) + Decimal('.0002') * qty * price
    cost = fee(entry) + fee(exit_price) if qty else Decimal(0)
    pnl = qty * (exit_price - entry) - cost
    return {'status': 'reference_available', 'return': float(pnl / 2000),
            'modeled_cost_usd': float(cost), 'quantity': qty,
            'minute_count': len(indexed)}


def fetch(client, now):
    """GET only; entire bounded evaluation window, no tuning or order calls."""
    end = min(now.astimezone(NY).date(), END)
    if end < START:
        raise ValueError('Trial has not started')
    calendar = client.request('GET', '/v2/calendar', params={'start': str(START), 'end': str(end)})
    days, seen = [], set()
    for row in calendar:
        opening, closing = interval(row)
        if row['date'] in seen or (days and row['date'] <= days[-1]['calendar']['date']):
            raise ValueError('Calendar must be unique and ordered')
        seen.add(row['date'])
        if closing + timedelta(minutes=15) > now:
            continue
        response = client.request('GET', '/v2/stocks/bars', data=True, params={
            'symbols': 'SPY', 'timeframe': '1Min', 'feed': 'iex', 'adjustment': 'raw',
            'start': iso(opening), 'end': iso(closing-timedelta(microseconds=1)),
            'limit': 10000, 'sort': 'asc',
        })
        # A single SPY session contains at most 390 minute bars. Refuse a
        # truncated/unexpected response rather than accepting partial pages.
        if response.get('next_page_token'):
            raise ValueError('Unexpected paginated single-session response')
        bars = (response.get('bars') or {}).get('SPY', []) or []
        reference(row, bars)
        days.append({'calendar': row, 'bars': bars, 'received_at': iso(datetime.now(timezone.utc))})
    return {'version': 1, 'source': SOURCE, 'requested_at': iso(now), 'sessions': days}


def evaluate(snapshot, session_rows, now):
    if snapshot.get('version') != 1 or snapshot.get('source') != SOURCE:
        raise ValueError('Unrecognized reference snapshot')
    requested = timestamp(snapshot['requested_at'])
    if requested > now:
        raise ValueError('Future snapshot')
    refs, last_day = {}, None
    for item in snapshot['sessions']:
        row = item['calendar']; day = row['date']
        _, closing = interval(row)
        receipt = timestamp(item['received_at'])
        if closing + timedelta(minutes=15) > requested or not requested <= receipt <= now:
            raise ValueError('Reference was not a completed-session observation')
        if last_day and day <= last_day:
            raise ValueError('Duplicate or unordered snapshot session')
        last_day = day
        refs[day] = reference(row, item['bars'])
    exports = {r['session_date']: r for r in session_rows}
    if len(exports) != len(session_rows):
        raise ValueError('Duplicate paper session')
    result = []
    # Calendar days without an accounting export remain explicit missing rows.
    for day in sorted(refs.keys() | exports.keys()):
        row = exports.get(day)
        result.append({'session_date': day,
                       'paper_accounting_return': row['closing_nav']/row['opening_nav']-1 if row else None,
                       'cash_reference_return': 0.0,
                       'spy_reference': refs.get(day, {'status': 'missing_calendar_session', 'return': None})})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--fetch', type=Path, help='Create an immutable private reference snapshot')
    group.add_argument('--snapshot', type=Path, help='Read an existing reference snapshot')
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    path = args.fetch or args.snapshot
    if args.fetch:
        if not path.resolve().is_relative_to((ROOT/'data/research').resolve()):
            parser.error('Fetched raw data must remain inside ignored data/research/')
        if path.exists():
            parser.error('Snapshot exists; choose a new path')
        snapshot = fetch(PaperClient(), now)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as stream:
            import os
            os.chmod(path, 0o600)
            json.dump(snapshot, stream, allow_nan=False)
    raw = path.read_bytes()
    snapshot = json.loads(raw)
    directory = ROOT/'data/telemetry/paper_ai_v1'
    cfg = json.loads((ROOT/'configs/paper_ai_v1.json').read_text())
    performance = load_performance(directory/'sessions.json', now.astimezone(NY).date(), directory/'state.json')
    exported = (directory/'sessions.json').read_bytes()
    if hashlib.sha256(exported).hexdigest() != performance['sha256']:
        raise ValueError('Accounting export changed during read; retry')
    decisions = decision_audit.audit(directory, cfg)
    operating = health.audit(directory)
    state_raw = (directory/'state.json').read_bytes()
    executions = execution_counts(json.loads(state_raw))
    rows = evaluate(snapshot, json.loads(exported)['sessions'], datetime.now(timezone.utc))
    for row in rows:
        session = operating['sessions'].get(row['session_date'])
        row['coverage'] = ('incomplete' if session and (session['blocked'] or session['partial_attendance']
                            or session['event_gaps_over_120_seconds']) else 'requires_review')
    print(json.dumps({'version': 'scorecard_v1', 'as_of': iso(datetime.now(timezone.utc)),
        'reference_source_sha256': hashlib.sha256(raw).hexdigest(),
        'paper_performance': performance, 'decisions': decisions,
        'executions': executions, 'execution_state_sha256': hashlib.sha256(state_raw).hexdigest(),
        'order_intents': operating['order_intents'],
        'nonterminal_order_intents': operating['nonterminal_order_intents'],
        'health_status': operating['status'], 'health_issues': operating['issues'],
        'sessions': rows,
        'limits': 'SPY rows are hypothetical independent USD 2,000 days, not broker fills or a compounded portfolio. '
                  'Incomplete strategy coverage is retained; no monthly performance or trading edge is certified. '
                  'Files are separate snapshots; broker reconciliation remains separate. '
                  'Raw retrospective bars are not model inputs.'}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
