"""Read-only paper reconciliation with sanitized output; never repairs state.

All network calls are GETs through the fixed paper client. This is a sequential
snapshot, not a broker transaction or permission to trade.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .client import APIError, PaperClient, TransportError
from .runner import TERMINAL, totals, validate_config

CORE_FIELDS = ('fingerprint', 'account_fingerprint', 'initial_broker_cash', 'orders', 'halt')


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError('invalid_number')
    result = float(value)
    if not math.isfinite(result):raise ValueError('invalid_number')
    return result


def assess(state, config, account, positions, open_orders):
    """Validate snapshots without returning identifiers or raw broker fields."""
    result = {'status': 'review_required', 'issues': [], 'identity_matches': None,
              'position_count': None, 'open_order_count': None, 'pending_intents': None,
              'cash_difference_usd': None, 'sleeve_cash_usd': None,
              'ledger_quantity': None, 'modeled_cost_usd': None}
    issues = result['issues']
    try:
        validate_config(config)
        if config['symbol'] != 'SPY' or config['mode'] != 'paper':raise ValueError('config')
        if not isinstance(state, dict) or not isinstance(state['orders'], dict):raise ValueError('state')
        if not isinstance(account['id'], str) or not account['id']:raise ValueError('account')
        result['identity_matches'] = hashlib.sha256(account['id'].encode()).hexdigest() == state['account_fingerprint']
        if not result['identity_matches']:issues.append('account_identity_mismatch')
        if account['status'] != 'ACTIVE' or account['trading_blocked'] is not False:
            issues.append('account_inactive_or_blocked')
        if state.get('halt'):issues.append('journal_halted')
        if not isinstance(positions, list) or not isinstance(open_orders, list):raise ValueError('inventories')
        result['position_count'], result['open_order_count'] = len(positions), len(open_orders)
        if len(open_orders) >= 500:issues.append('open_inventory_may_be_truncated')
        pending = 0
        for cid, order in state['orders'].items():
            payload = order['payload']
            if (payload['client_order_id'] != cid or payload['symbol'] != 'SPY'
                    or payload['side'] not in {'buy', 'sell'} or payload['type'] not in {'market', 'limit'}
                    or payload['time_in_force'] != 'day' or finite(payload['qty']) <= 0):
                raise ValueError('invalid_intent')
            broker = order.get('broker')
            if broker is None:
                pending += 1;continue
            if not isinstance(broker, dict):raise ValueError('invalid_order')
            if any(broker.get(k) != payload[k] for k in ('client_order_id', 'symbol', 'side', 'type', 'time_in_force')):
                raise ValueError('intent_response_mismatch')
            requested, filled = finite(broker['qty']), finite(broker['filled_qty'])
            if requested != finite(payload['qty']) or not 0 <= filled <= requested:
                raise ValueError('invalid_fill')
            if filled and finite(broker['filled_avg_price']) <= 0:raise ValueError('invalid_price')
            if broker['status'] == 'filled' and filled != requested:raise ValueError('incomplete_fill')
            if not isinstance(broker['status'], str):raise ValueError('invalid_status')
            if broker['status'] not in TERMINAL:pending += 1
        result['pending_intents'] = pending
        if pending:issues.append('unresolved_order_intents')
        cash, qty, cost = totals(state, config['capital'])
        actual = 0.0
        if len(positions) > 1:issues.append('unexpected_position_inventory')
        for position in positions:
            if position['symbol'] != 'SPY':issues.append('unowned_position')
            amount = finite(position['qty'])
            if amount < 0 or position.get('side') != 'long':issues.append('unexpected_short_position')
            actual += amount
        if abs(actual-qty) > 1e-6:issues.append('position_ledger_mismatch')
        for order in open_orders:
            cid = order['client_order_id']
            if cid not in state['orders']:
                issues.append('unowned_open_order');continue
            if order != state['orders'][cid].get('broker'):
                # Conservative: changed fills/status require a fresh audit after
                # the runner reconciles; this tool never accepts broker updates.
                issues.append('open_order_snapshot_mismatch')
        if open_orders:issues.append('open_orders_require_review')
        initial = finite(state['initial_broker_cash'])
        if initial < config['capital']:raise ValueError('invalid_initial_cash')
        difference = finite(account['cash'])-(initial+cash-config['capital'])
        if not all(math.isfinite(v) for v in (cash, qty, cost, difference)):
            raise ValueError('nonfinite_reconciliation')
        if abs(difference) > .02:issues.append('cash_ledger_mismatch')
        result.update(cash_difference_usd=difference, sleeve_cash_usd=cash,
                      ledger_quantity=qty, modeled_cost_usd=cost)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        issues.append('invalid_reconciliation_input')
    result['issues'] = sorted(set(issues))
    result['status'] = 'review_required' if issues else 'reconciliation_checks_passed'
    return result


def audit(directory, config, client=None):
    directory = Path(directory)
    now = datetime.now(timezone.utc)
    try:
        raw = (directory/'state.json').read_bytes();state = json.loads(raw)
        strategy = Path(__file__).with_name('strategy.py').read_bytes()
        if config.get('ai'):strategy += Path(__file__).with_name('ai.py').read_bytes()
        frozen = hashlib.sha256(json.dumps(config, sort_keys=True).encode()+strategy).hexdigest()
        client = client or PaperClient()
        account, positions, orders = client.account(), client.positions(), client.open_orders()
        result = assess(state, config, account, positions, orders)
        if state.get('fingerprint') != frozen:result['issues'].append('frozen_configuration_mismatch')
        after = json.loads((directory/'state.json').read_bytes())
        if any(state.get(k) != after.get(k) for k in CORE_FIELDS):
            result['issues'].append('reconciliation_state_changed_during_audit')
        if result['issues']:result['status'] = 'review_required'
        result['state_sha256'] = hashlib.sha256(raw).hexdigest()
        result['configuration_sha256'] = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, AttributeError, APIError, TransportError):
        result = {'status': 'review_required', 'issues': ['reconciliation_unavailable']}
    result['started_at'] = now.isoformat()
    result['as_of'] = datetime.now(timezone.utc).isoformat()
    result['limits'] = 'Sequential read-only paper snapshots; concurrent broker changes remain possible. No state repair, order submission, funded trading or complete-session/performance certification. Modeled costs are not broker fees.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', choices=('paper_ai_v1', 'paper_v1'), default='paper_ai_v1')
    args = parser.parse_args();root = Path(__file__).resolve().parents[2]
    try:
        config = json.loads((root/'configs'/f'{args.config}.json').read_bytes())
        result = audit(root/'data/telemetry'/args.config, config)
    except (OSError, ValueError):
        result = {'status': 'review_required', 'issues': ['configuration_unavailable']}
    print(json.dumps(result, indent=2))
    return 2 if result['status'] == 'review_required' else 0


if __name__ == '__main__':
    raise SystemExit(main())
