"""Synthetic reference prices; these assertions are not paper executions."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import pytest

from cash_cow.paper.scorecard import SOURCE, evaluate, execution_counts, fetch, interval, reference
from cash_cow.paper.client import iso

DAY = {'date': '2026-11-04', 'open': '09:30', 'close': '16:00'}


def bars(day=DAY):
    opening, closing = interval(day)
    return [{'t': iso(at), 'o': price, 'h': price, 'l': price, 'c': price, 'v': 10}
            for at, price in [(opening, 100), (closing-timedelta(minutes=1), 101)]]


def snapshot():
    at = '2026-11-05T12:00:00+00:00'
    return {'version': 1, 'source': SOURCE, 'requested_at': at,
            'sessions': [{'calendar': DAY, 'bars': bars(), 'received_at': at}]}


def test_independent_day_whole_shares_and_both_cost_sides():
    result = reference(DAY, bars())
    assert result['quantity'] == 18  # 95% of 2000 less USD1 reserve
    assert result['modeled_cost_usd'] == pytest.approx(.8 + .0002*18*201)
    assert result['return'] == pytest.approx((18-.8-.0002*18*201)/2000)


def test_missing_open_is_not_substituted_or_reported_as_zero():
    result = reference(DAY, bars()[1:])
    assert result['return'] is None
    assert result['status'] == 'missing_boundary_minutes'


@pytest.mark.parametrize('change', ['duplicate', 'nan', 'bool', 'outside', 'bad_range', 'zero_volume'])
def test_malformed_data_is_rejected(change):
    data = bars()
    if change == 'duplicate': data.append(data[0])
    if change == 'nan': data[0]['o'] = float('nan')
    if change == 'bool': data[0]['c'] = True
    if change == 'outside': data[0]['t'] = '2026-11-04T14:29:00+00:00'
    if change == 'bad_range': data[0]['h'] = 99
    if change == 'zero_volume': data[0]['v'] = 0
    with pytest.raises(ValueError): reference(DAY, data)


def test_missing_accounting_session_remains_in_denominator():
    result = evaluate(snapshot(), [], datetime(2026, 11, 6, tzinfo=timezone.utc))
    assert len(result) == 1
    assert result[0]['paper_accounting_return'] is None
    assert result[0]['spy_reference']['return'] is not None


@pytest.mark.parametrize('change', ['future', 'duplicate', 'source', 'before_close', 'before_trial'])
def test_snapshot_provenance_and_cutoffs(change):
    snap = snapshot()
    if change == 'future': snap['sessions'][0]['received_at'] = '2026-12-01T00:00:00Z'
    if change == 'duplicate': snap['sessions'].append(deepcopy(snap['sessions'][0]))
    if change == 'source': snap['source'] = 'different feed'
    if change == 'before_close': snap['requested_at'] = '2026-11-04T20:00:00Z'
    if change == 'before_trial': snap['sessions'][0]['calendar'] = dict(DAY, date='2026-11-03')
    with pytest.raises(ValueError): evaluate(snap, [], datetime(2026, 11, 6, tzinfo=timezone.utc))


def test_short_day_uses_its_calendar_close():
    day = dict(DAY, date='2026-11-27', close='13:00')
    assert reference(day, bars(day))['return'] is not None


def test_fetch_never_calls_orders_and_rejects_pagination():
    class Client:
        def request(self, method, path, **kwargs):
            assert method == 'GET'
            if path == '/v2/calendar':
                assert kwargs['params']['start'] == '2026-11-04'
                assert kwargs['params']['end'] == '2026-12-02'
                return [DAY]
            assert path == '/v2/stocks/bars' and kwargs['data']
            return {'bars': {'SPY': bars()}, 'next_page_token': 'unexpected'}
    with pytest.raises(ValueError, match='paginated'):
        fetch(Client(), datetime(2026, 12, 3, tzinfo=timezone.utc))


def test_intent_acknowledgement_and_partial_fill_are_distinct():
    p = {'client_order_id': 'fixture', 'symbol': 'SPY', 'side': 'buy', 'qty': '2'}
    state = {'orders': {'fixture': {'payload': p}}}
    assert execution_counts(state)['broker_responses'] == 0
    state['orders']['fixture']['broker'] = dict(p, filled_qty='1', filled_avg_price='100')
    first = execution_counts(state)
    assert first['broker_responses'] == first['orders_with_fills'] == 1
    assert first['filled_buy_quantity'] == 1
    assert execution_counts(state) == first  # Polling does not add a fill.
    state['orders']['fixture']['broker']['filled_qty'] = '3'
    with pytest.raises(ValueError): execution_counts(state)
