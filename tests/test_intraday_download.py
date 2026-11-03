import json
from pathlib import Path
import pandas as pd
import pytest
from cash_cow.intraday import data

class Response:
    status_code=200
    def __init__(self,payload):self.payload=payload
    def json(self):return self.payload

def test_alpaca_pagination_explicit_feed_and_verified_resume(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'RAW',tmp_path)
    monkeypatch.setattr(data,'read_keys',lambda:{'APCA-API-KEY-ID':'test-key','APCA-API-SECRET-KEY':'test-secret'})
    monkeypatch.setattr(data.time,'sleep',lambda _:None)
    calls=[]
    def get(url,headers,params,timeout):
        calls.append((url,dict(params)))
        assert headers['APCA-API-KEY-ID']=='test-key'
        second=params.get('page_token')=='second'
        bar={'t':'2016-01-04T14:31:00Z' if second else '2016-01-04T14:30:00Z','o':200,'h':201,'l':199,'c':200,'v':1000}
        return Response({'bars':{'SPY':[bar]},'next_page_token':None if second or params['timeframe']=='1Day' else 'second'})
    monkeypatch.setattr(data.requests,'get',get)
    data.download_alpaca('2016-01-01','2025-01-01')
    assert len(calls)==3
    assert all(p['feed']=='sip' and p['adjustment']=='raw' for _,p in calls)
    assert all(u=='https://data.alpaca.markets/v2/stocks/bars' for u,_ in calls)
    f=pd.read_csv(tmp_path/'alpaca_SPY_1Min_2016-01-01_2025-01-01.csv.gz')
    assert len(f)==2
    data.download_alpaca('2016-01-01','2025-01-01')
    assert len(calls)==3  # verified cache, no redundant request
    path=tmp_path/'alpaca_SPY_1Min_2016-01-01_2025-01-01.csv.gz';path.write_bytes(b'corrupt')
    with pytest.raises(FileExistsError,match='unverified'):data.download_alpaca('2016-01-01','2025-01-01')

def test_missing_credentials_and_reserved_history_fail_before_network(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'ROOT',tmp_path)
    for key in ['APCA_API_KEY_ID','APCA_API_SECRET_KEY']:monkeypatch.delenv(key,raising=False)
    with pytest.raises(ValueError,match='Missing local'):data.read_keys()
    with pytest.raises(ValueError,match='reserved'):data.download_alpaca('2024-01-01','2026-01-01')

def test_rate_limit_retry_is_bounded(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'RAW',tmp_path);monkeypatch.setattr(data,'read_keys',lambda:{})
    monkeypatch.setattr(data.time,'sleep',lambda _:None)
    calls=[]
    def get(*args,**kwargs):
        calls.append(1);r=Response({});r.status_code=429;return r
    monkeypatch.setattr(data.requests,'get',get)
    with pytest.raises(RuntimeError,match='five attempts'):data.download_alpaca('2016-01-01','2025-01-01')
    assert len(calls)==5
