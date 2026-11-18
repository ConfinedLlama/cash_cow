"""Synthetic reference prices; these assertions are not paper executions."""
from datetime import date, datetime, timedelta, timezone
from copy import deepcopy
import pytest

from cash_cow.paper.scorecard import SOURCE, evaluate, execution_counts, fetch, interval, reference, session_decisions
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
    result = evaluate(snapshot(), [], datetime(2026, 11, 5, 12, tzinfo=timezone.utc), calendar())
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
    with pytest.raises(ValueError): evaluate(snap, [], datetime(2026, 11, 5, 12, tzinfo=timezone.utc), calendar())


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
    p = {'client_order_id': 'fixture', 'symbol': 'SPY', 'side': 'buy', 'qty': '2', 'type': 'limit', 'time_in_force': 'day'}
    state = {'orders': {'fixture': {'payload': p}}}
    assert execution_counts(state)['broker_responses'] == 0
    state['orders']['fixture']['broker'] = dict(p, filled_qty='1', filled_avg_price='100', status='partially_filled')
    first = execution_counts(state)
    assert first['broker_responses'] == first['orders_with_fills'] == 1
    assert first['filled_buy_quantity'] == 1
    assert execution_counts(state) == first  # Polling does not add a fill.
    state['orders']['fixture']['broker']['filled_qty'] = '3'
    with pytest.raises(ValueError): execution_counts(state)


def calendar():
    rows = []
    day = date(2026, 11, 4)
    while len(rows) < 20:
        if day.weekday() < 5 and day != date(2026, 11, 26):
            rows.append(dict(DAY, date=str(day), close='13:00' if day == date(2026, 11, 27) else '16:00'))
        day += timedelta(days=1)
    return {'source': 'Alpaca GET /v2/calendar', 'start': '2026-11-04', 'end': '2026-12-02',
            'fetched_at': '2026-11-04T12:00:00Z', 'sessions': rows}


def test_day_missing_from_both_sources_remains_visible():
    snap = snapshot(); snap['sessions'] = []
    rows = evaluate(snap, [], datetime(2026, 11, 6, 12, tzinfo=timezone.utc), calendar())
    assert [r['session_date'] for r in rows] == ['2026-11-04', '2026-11-05']
    assert all(r['paper_accounting_return'] is None and r['spy_reference']['return'] is None for r in rows)


def test_interval_disagreement_and_nonelapsed_accounting_rejected():
    cal = calendar(); cal['sessions'][0]['close'] = '13:00'
    now = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match='interval disagrees'):
        evaluate(snapshot(), [], now, cal)
    with pytest.raises(ValueError, match='nonelapsed'):
        evaluate(snapshot(), [{'session_date': '2026-11-05', 'opening_nav': 2000, 'closing_nav': 2000}], now, calendar())


@pytest.mark.parametrize('opened,closed', [('09:30:01', '16:00'), ('09:30+01:00', '16:00'), ('09:30', '16:00:01')])
def test_calendar_clock_strings_are_exact(opened, closed):
    with pytest.raises(ValueError): interval(dict(DAY, open=opened, close=closed))


def execution_fixture():
    orders = {}
    for cid, side, filled, price in [('entry', 'buy', '2', '101'), ('exit', 'sell', '1', '99')]:
        p = {'client_order_id': cid, 'symbol': 'SPY', 'side': side, 'qty': '2', 'type': 'limit', 'time_in_force': 'day'}
        orders[cid] = {'payload': p, 'created_at': '2026-11-04T15:10:02Z',
                       'reference_quote': {'t': '2026-11-04T15:10:01Z', 'bp': 100, 'ap': 100},
                       'broker': dict(p, filled_qty=filled, filled_avg_price=price,
                                      status='filled' if filled == '2' else 'canceled')}
    return {'orders': orders}


def test_fill_quality_counts_partial_cancel_once_and_uses_signed_sides():
    state = execution_fixture();result = execution_counts(state)
    assert result['filled_notional_usd'] == 301
    assert result['gross_turnover_fraction_of_initial_capital'] == pytest.approx(301/2000)
    assert result['modeled_fill_cost_usd'] == pytest.approx(.8+.0002*301)
    assert result['signed_quote_shortfall_bps'] == pytest.approx(100)
    assert result['orders_with_usable_reference_quote'] == 2
    assert execution_counts(state) == result


def test_no_fills_or_missing_quotes_cannot_be_reported_as_zero_shortfall():
    assert execution_counts({'orders': {}})['signed_quote_shortfall_bps'] is None
    state = execution_fixture()
    state['orders']['entry']['reference_quote'] = None
    state['orders']['exit']['reference_quote']['t'] = '2026-11-04T15:00:00Z'
    result = execution_counts(state)
    assert result['orders_without_usable_reference_quote'] == 2
    assert result['signed_quote_shortfall_bps'] is None
    assert result['filled_notional_usd'] == 301


def test_inconsistent_fill_or_other_symbol_is_rejected():
    state = execution_fixture();state['orders']['exit']['broker']['status'] = 'filled'
    with pytest.raises(ValueError, match='Filled status'): execution_counts(state)
    state = execution_fixture();state['orders']['entry']['payload']['symbol'] = 'QQQ'
    with pytest.raises(ValueError, match='Invalid intent'): execution_counts(state)


def test_session_decisions_distinguish_absence_from_holds_and_polling():
    evidence = {'status': 'integrity_checks_passed', 'errors': {},
                'by_session': {'2026-11-05': {'completed': 2, 'HOLD': 1, 'BUY': 1, 'failed': 1}},
                'proposal_events': 200, 'preflight_attempts': 3}
    result = session_decisions(evidence, '2026-11-05')
    assert result['unique_records'] == 3
    assert result['record_statuses'] == {'pending': 0, 'failed': 1, 'completed': 2}
    assert result['completed_actions'] == {'BUY': 1, 'SELL': 0, 'HOLD': 1}
    missing = session_decisions(evidence, '2026-11-06')
    assert missing['unique_records'] == 0
    assert missing['completed_actions']['HOLD'] == 0


@pytest.mark.parametrize('change', ['failed_audit', 'missing_map', 'negative', 'boolean', 'inconsistent', 'unknown'])
def test_invalid_decision_evidence_does_not_become_zero_or_hold(change):
    evidence = {'status': 'integrity_checks_passed', 'errors': {},
                'by_session': {'2026-11-05': {'completed': 2, 'HOLD': 2}}}
    if change == 'failed_audit': evidence['errors'] = {'invalid_decision_record': 1}
    if change == 'missing_map': del evidence['by_session']
    if change == 'negative': evidence['by_session']['2026-11-05']['failed'] = -1
    if change == 'boolean': evidence['by_session']['2026-11-05']['pending'] = True
    if change == 'inconsistent': evidence['by_session']['2026-11-05']['HOLD'] = 1
    if change == 'unknown': evidence['by_session']['2026-11-05']['private-rationale'] = 1
    result = session_decisions(evidence, '2026-11-05')
    assert result['status'] == 'unavailable'
    assert result['unique_records'] is None and result['completed_actions'] is None
    assert 'private' not in str(result)
