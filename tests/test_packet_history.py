from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from cash_cow.packet_research.history import history_features


def inputs():
    start = datetime(2026,11,5,14,30,tzinfo=timezone.utc)
    rows = [{'t': (start+timedelta(minutes=i)).isoformat(),
             'o': 100+i, 'h': 102+i, 'l': 99+i, 'c': 101+i, 'v': 10+i}
            for i in range(35)]
    at = (start+timedelta(minutes=35,seconds=2)).isoformat()
    return {'feed':'iex','observed_at':at,'bars':rows}, {
        'as_of':at,'session_date':'2026-11-05','symbol':'SPY','feed':'iex',
        'features':{'bar':rows[-1]['t'],'close':rows[-1]['c']}}


def test_known_returns_aggregates_and_no_mutation():
    snapshot,context=inputs();before=deepcopy((snapshot,context))
    result=history_features(snapshot,context)
    assert result['close_returns']==pytest.approx({'5':135/130-1,'15':135/120-1,'30':135/105-1})
    first=result['five_minute_bars'][0]
    assert (first['open'],first['high'],first['low'],first['close'],first['volume'])==(105,111,104,110,85)
    assert len(result['five_minute_bars'])==6
    assert result['receipt_timing']=='unverified_legacy_tick_start'
    assert (snapshot,context)==before


@pytest.mark.parametrize('change', ['gap','duplicate','future_snapshot','stale_snapshot','future_bar',
                                  'nan','bool','bounds','wrong_feed','close','wrong_day','short'])
def test_invalid_history_is_rejected(change):
    s,c=inputs()
    if change=='gap':s['bars'].pop(4)
    elif change=='duplicate':s['bars'][5]=s['bars'][4]
    elif change=='future_snapshot':s['observed_at']='2026-11-05T15:05:03Z'
    elif change=='stale_snapshot':s['observed_at']='2026-11-05T15:00:00Z'
    elif change=='future_bar':s['bars'][-1]['t']='2026-11-05T15:05:00Z'
    elif change=='nan':s['bars'][0]['v']=float('nan')
    elif change=='bool':s['bars'][0]['v']=True
    elif change=='bounds':s['bars'][0]['h']=90
    elif change=='wrong_feed':s['feed']='sip'
    elif change=='close':c['features']['close']=1
    elif change=='wrong_day':c['session_date']='2026-11-06'
    elif change=='short':s['bars'].pop()
    with pytest.raises(ValueError):history_features(s,c)


def test_minutes_after_feature_bar_do_not_change_feature_values():
    s,c=inputs();baseline=history_features(s,c)
    row=dict(s['bars'][-1],t='2026-11-05T15:05:00Z',o=900,h=1000,l=800,c=950)
    s['bars'].append(row);s['observed_at']=c['as_of']='2026-11-05T15:06:01Z'
    result=history_features(s,c)
    assert result['close_returns']==baseline['close_returns']
    assert result['five_minute_bars']==baseline['five_minute_bars']
    assert result['snapshot_sha256']!=baseline['snapshot_sha256']


def test_timezone_offset_changes_do_not_shift_session_minutes():
    s,c=inputs();c['as_of']='2026-11-05T10:05:02-05:00'
    assert history_features(s,c)['close_returns']['5']==pytest.approx(135/130-1)


def test_snapshot_cannot_claim_a_minute_completed_after_its_own_observation():
    s,c=inputs();s['observed_at']='2026-11-05T15:04:59Z'
    with pytest.raises(ValueError,match='future_bar'):
        history_features(s,c)
