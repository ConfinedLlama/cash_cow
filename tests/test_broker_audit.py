"""Synthetic broker snapshots only; no API requests or trading outcomes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from cash_cow.paper.broker_audit import assess, audit


def fixture():
    config = json.loads((Path(__file__).resolve().parents[1]/'configs/paper_v1.json').read_text())
    account = {'id': 'PRIVATE_ACCOUNT', 'status': 'ACTIVE', 'trading_blocked': False, 'cash': '100000'}
    state = {'orders': {}, 'account_fingerprint': hashlib.sha256(account['id'].encode()).hexdigest(),
             'initial_broker_cash': 100000, 'halt': None}
    return state, config, account


def test_flat_reconciliation_is_private_and_read_only():
    state, cfg, account = fixture();before = deepcopy((state, cfg, account))
    result = assess(state, cfg, account, [], [])
    assert result['status'] == 'reconciliation_checks_passed'
    assert result['cash_difference_usd'] == 0 and result['sleeve_cash_usd'] == 2000
    assert 'PRIVATE' not in json.dumps(result)
    assert before == (state, cfg, account)


@pytest.mark.parametrize('change,issue', [('cash','cash_ledger_mismatch'),('account','account_identity_mismatch'),
    ('blocked','account_inactive_or_blocked'),('short','unexpected_short_position'),
    ('unowned','unowned_open_order'),('nan','invalid_reconciliation_input'),
    ('orders','invalid_reconciliation_input'),('boolean','invalid_reconciliation_input')])
def test_failures_cannot_be_mistaken_for_flat_success(change, issue):
    state,cfg,a = fixture();positions=[];orders=[]
    if change=='cash':a['cash']='99999'
    elif change=='account':a['id']='OTHER_PRIVATE_ACCOUNT'
    elif change=='blocked':a['trading_blocked']=True
    elif change=='short':positions=[{'symbol':'SPY','qty':'-1','side':'short'}]
    elif change=='unowned':orders=[{'client_order_id':'PRIVATE_OTHER'}]
    elif change=='nan':a['cash']='NaN'
    elif change=='orders':state['orders']=[]
    elif change=='boolean':a['cash']=True
    result=assess(state,cfg,a,positions,orders)
    assert result['status']=='review_required' and issue in result['issues']
    assert 'PRIVATE' not in json.dumps(result)


def test_realistic_filled_intent_and_cost_stress():
    state,cfg,a=fixture()
    payload={'client_order_id':'PRIVATE_ORDER','symbol':'SPY','side':'buy','type':'limit','time_in_force':'day','qty':'2'}
    state['orders']['PRIVATE_ORDER']={'payload':payload,'broker':dict(payload,status='filled',filled_qty='2',filled_avg_price='600')}
    a['cash']='98800'
    result=assess(state,cfg,a,[{'symbol':'SPY','qty':'2','side':'long'}],[])
    assert result['status']=='reconciliation_checks_passed'
    assert result['sleeve_cash_usd']==800 and result['modeled_cost_usd']==pytest.approx(.64)
    state['orders']['PRIVATE_ORDER']['broker']['side']='sell'
    assert 'invalid_reconciliation_input' in assess(state,cfg,a,[],[])['issues']


def test_unresolved_intent_is_not_retried_or_reported_success():
    state,cfg,a=fixture()
    state['orders']['PRIVATE_ORDER']={'payload':{'client_order_id':'PRIVATE_ORDER','symbol':'SPY','side':'buy','type':'limit','time_in_force':'day','qty':'1'}}
    result=assess(state,cfg,a,[],[])
    assert result['pending_intents']==1 and 'unresolved_order_intents' in result['issues']


def test_wrapper_uses_reads_only_and_detects_concurrent_state_change(tmp_path):
    state,cfg,a=fixture()
    import cash_cow.paper.broker_audit as module
    source=Path(module.__file__).with_name('strategy.py').read_bytes()
    state['fingerprint']=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()+source).hexdigest()
    path=tmp_path/'state.json';path.write_text(json.dumps(state));before=path.read_bytes()
    class Client:
        def account(self):return a
        def positions(self):return []
        def open_orders(self):return []
    assert audit(tmp_path,cfg,Client())['status']=='reconciliation_checks_passed'
    assert path.read_bytes()==before
    class Changing(Client):
        def positions(self):
            state['initial_broker_cash']=99999;path.write_text(json.dumps(state));return []
    assert 'reconciliation_state_changed_during_audit' in audit(tmp_path,cfg,Changing())['issues']


def test_transport_errors_hide_payloads(tmp_path):
    state,cfg,_=fixture();(tmp_path/'state.json').write_text(json.dumps(state))
    from cash_cow.paper.client import TransportError
    class Client:
        def account(self):raise TransportError('PRIVATE_RESPONSE_OR_SECRET')
    result=audit(tmp_path,cfg,Client())
    assert result['issues']==['reconciliation_unavailable'] and 'PRIVATE' not in json.dumps(result)
