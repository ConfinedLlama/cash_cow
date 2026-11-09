from copy import deepcopy
import hashlib
import json

import pytest

from cash_cow.packet_research.packet import build_packet, load_spec
from test_packet_history import inputs
from test_packet_releases import release


def test_baseline_packet_is_exact_and_requires_no_candidate_data():
    _,context=inputs();out=build_packet(context,None,None,'baseline')
    assert out['packet']==context and out['execution_enabled'] is False
    assert set(out['source_sha256'])=={'baseline','specification'}
    encoded=json.dumps(out['packet'],sort_keys=True,allow_nan=False,ensure_ascii=False).encode('utf-8')
    assert out['packet_sha256']==hashlib.sha256(encoded).hexdigest()


def test_arms_preserve_original_fields_and_inputs():
    snapshot,context=inputs();context['news']=[{'headline':'untrusted context'}]
    records=[release()];before=deepcopy((snapshot,context,records))
    history=build_packet(context,snapshot,records,'history')
    both=build_packet(context,snapshot,records,'history_and_releases')
    assert all(both['packet'][k]==v for k,v in context.items())
    assert 'official_releases' not in history['packet']
    assert both['packet']['official_releases']['values']==[]  # release is next day
    assert both['packet_sha256']!=history['packet_sha256']
    assert (snapshot,context,records)==before


def test_packet_budget_counts_utf8_bytes_and_never_truncates():
    _,context=inputs();context['news']=[{'headline':'界'*7000}]
    assert len(json.dumps(context,ensure_ascii=False))<20000
    with pytest.raises(ValueError,match='byte_limit'):build_packet(context,None,None,'baseline')
    assert len(context['news'][0]['headline'])==7000


def test_hashes_repeat_and_change_when_input_changes():
    snapshot,context=inputs()
    one=build_packet(context,snapshot,[],'history')
    assert one==build_packet(context,snapshot,[],'history')
    context['position_qty']=1
    assert one['source_sha256']['baseline']!=build_packet(context,snapshot,[],'history')['source_sha256']['baseline']


@pytest.mark.parametrize('change', ['extra','symbol','feed','nan','arm'])
def test_invalid_packet_is_not_silently_repaired(change):
    snapshot,context=inputs();arm='history'
    if change=='extra':context['price_history']={}
    elif change=='symbol':context['symbol']='BTC/USD'
    elif change=='feed':context['feed']='sip'
    elif change=='nan':context['position_qty']=float('nan')
    else:arm='buy_more'
    with pytest.raises(ValueError):build_packet(context,snapshot,[],arm)


def test_registered_spec_has_no_execution_path():
    spec=load_spec()
    assert spec['status']=='offline_only' and spec['execution_enabled'] is False
    assert spec['arms']==['baseline','history','history_and_releases']
