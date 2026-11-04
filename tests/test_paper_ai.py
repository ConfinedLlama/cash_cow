"""Deterministic fixtures for proposal gating and spending; no model API calls."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from cash_cow.paper.ai import ResponsesAdvisor, DecisionProvider, news_context, validate_proposal, require_model_preflight, model_fingerprint
from cash_cow.paper.runner import Runner
from cash_cow.paper.client import iso
from test_paper import FakeAPI, CONFIG

AI_CONFIG = json.loads((Path(__file__).parents[1]/'configs/paper_ai_v1.json').read_text())


def active_config():
    cfg = deepcopy(AI_CONFIG)
    cfg['ai'].update(enabled=True, daily_budget_usd=2)
    return cfg


def proposal(action='BUY'):
    return {'action':action, 'confidence':.7, 'rationale':'Synthetic test only', 'news_ids':[]}


def context(api):
    return {'as_of':iso(api.now),'session_date':'2026-11-03','position_qty':0,'news':[]}


@pytest.mark.parametrize('bad', [
    dict(proposal(), qty=10000), dict(proposal(), action='SHORT'),
    dict(proposal(), confidence=float('nan')), dict(proposal(), confidence=True),
    dict(proposal(), news_ids=['invented']), dict(proposal(), rationale=''),
])
def test_model_cannot_invent_fields_actions_or_citations(bad):
    with pytest.raises(ValueError):
        validate_proposal(bad, {'news':[]})


def test_daily_budget_reserved_before_call_and_no_ambiguous_retry(tmp_path):
    session = Mock()
    session.post.side_effect = requests.Timeout('secret-value')
    advisor = ResponsesAdvisor('test-key', active_config(), tmp_path, session=session)
    with pytest.raises(ValueError) as error:
        advisor.evaluate(context(FakeAPI()), 'attempt1')
    assert 'secret-value' not in str(error.value)
    ledger=json.loads((tmp_path/'ai_budget.json').read_text())
    assert ledger['2026-11-03']['attempt1']['reserved_usd'] > 0
    with pytest.raises(ValueError, match='Previously attempted'):
        advisor.evaluate(context(FakeAPI()), 'attempt1')
    assert session.post.call_count == 1


def test_budget_exhaustion_prevents_network_call(tmp_path):
    cfg=active_config();cfg['ai']['daily_budget_usd']=.00001
    session=Mock()
    with pytest.raises(ValueError, match='budget exhausted'):
        ResponsesAdvisor('test', cfg, tmp_path, session=session).evaluate(context(FakeAPI()), 'a')
    session.post.assert_not_called()


def test_structured_output_parsed_and_tools_absent(tmp_path):
    session=Mock(); session.post.return_value.status_code=200
    session.post.return_value.json.return_value={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(proposal())}]}]}
    result=ResponsesAdvisor('test', active_config(), tmp_path, session=session).evaluate(context(FakeAPI()), 'a')
    assert result['action']=='BUY'
    args,kwargs=session.post.call_args
    assert args[0]=='https://api.openai.com/v1/responses'
    assert kwargs['allow_redirects'] is False
    assert kwargs['json']['store'] is False
    assert 'tools' not in kwargs['json']
    assert kwargs['json']['text']['format']['strict'] is True


def test_refusal_is_not_a_proposal(tmp_path):
    session=Mock();session.post.return_value.status_code=200
    session.post.return_value.json.return_value={'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'fixture'}]}]}
    with pytest.raises(ValueError, match='refused'):
        ResponsesAdvisor('test', active_config(), tmp_path, session=session).evaluate(context(FakeAPI()), 'a')


def test_news_first_seen_prevents_hindsight(tmp_path):
    api=FakeAPI();folder=tmp_path/'news';folder.mkdir()
    (folder/'status.json').write_text(json.dumps({'last_success':iso(api.now),'error':None}))
    base={'first_observed_at':iso(api.now),'metadata':{'id':1,'headline':'old','created_at':iso(api.now-timedelta(hours=1)),'updated_at':iso(api.now)}}
    (folder/'one.json').write_text(json.dumps(base))
    revised=deepcopy(base);revised['first_observed_at']=iso(api.now+timedelta(minutes=1));revised['metadata']['headline']='future revision'
    (folder/'two.json').write_text(json.dumps(revised))
    health,news=news_context(tmp_path,api.now)
    assert health['fresh']
    assert news[0]['headline']=='old'


def test_old_proposal_never_creates_trade(tmp_path):
    api=FakeAPI();cfg=active_config()
    provider=DecisionProvider(Mock(),cfg,tmp_path,tmp_path,now=lambda:api.now)
    observed={'bar':iso(api.now-timedelta(minutes=1))}
    import hashlib
    slot=hashlib.sha256(f"{cfg['version']}:{observed['bar']}:0".encode()).hexdigest()[:24]
    path=tmp_path/'ai_decisions'/f'{slot}.json';path.parent.mkdir()
    c=context(api);c['as_of']=iso(api.now-timedelta(minutes=3))
    path.write_text(json.dumps({'status':'completed','context':c,'proposal':proposal()}))
    assert provider.decide(observed,{},0,2000,'2026-11-03') is None
    provider.close()


def test_ai_pending_never_blocks_time_exit(tmp_path):
    api=FakeAPI();provider=Mock()
    provider.decide.return_value=dict(proposal(),decision_id='synthetic',as_of=iso(api.now))
    runner=Runner(api,active_config(),tmp_path,now=lambda:api.now,decision_provider=provider)
    assert runner.tick()['kind']=='order_submitted'
    entry=api.submissions[-1];api.fill(entry['client_order_id'],float(entry['qty']))
    provider.decide.return_value=None
    assert runner.tick()['kind']=='ai_waiting_or_unavailable'
    api.now=api.now.replace(hour=15,minute=50)
    count=provider.decide.call_count
    assert runner.tick()['kind']=='order_submitted'
    assert api.submissions[-1]['side']=='sell'
    assert provider.decide.call_count==count


def test_hold_proposal_does_not_follow_quantitative_buy_signal(tmp_path):
    api=FakeAPI();provider=Mock()
    provider.decide.return_value=dict(proposal('HOLD'),decision_id='synthetic',as_of=iso(api.now))
    runner=Runner(api,active_config(),tmp_path,now=lambda:api.now,decision_provider=provider)
    assert runner.tick()['kind']=='no_entry'
    assert not api.submissions


def test_disabled_ai_does_not_fall_back_to_quant_strategy(tmp_path):
    with pytest.raises(ValueError,match='not enabled'):
        Runner(FakeAPI(),AI_CONFIG,tmp_path)


def test_activation_requires_matching_successful_model_preflight(tmp_path):
    cfg=active_config()
    with pytest.raises(ValueError):
        require_model_preflight(cfg,tmp_path)
    (tmp_path/'model_preflight.json').write_text(json.dumps({'status':'passed','fingerprint':model_fingerprint(cfg)}))
    require_model_preflight(cfg,tmp_path)
    cfg['ai']['daily_budget_usd']=5
    with pytest.raises(ValueError):
        require_model_preflight(cfg,tmp_path)
