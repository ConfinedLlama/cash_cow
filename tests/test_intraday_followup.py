import numpy as np
import pandas as pd
from cash_cow.intraday.followup import rest_of_day_decisions

def test_rest_of_day_uses_only_observations_available_at_1530():
    idx=pd.date_range('2022-08-01 09:30',periods=390,freq='min',tz='America/New_York')
    f=pd.DataFrame({'close':101.,'previous_close':100.,'day':pd.Timestamp('2022-08-01')},index=idx)
    a=rest_of_day_decisions(f)
    assert a.dropna().index.tolist()==[idx[359]]
    assert a.iloc[359]==1
    f.loc[idx[360]:,'close']=10
    pd.testing.assert_series_equal(a,rest_of_day_decisions(f))
    f.loc[idx[359],'close']=99
    assert rest_of_day_decisions(f).iloc[359]==-1

def test_rest_of_day_skips_short_session():
    idx=pd.date_range('2022-11-25 09:30',periods=210,freq='min',tz='America/New_York')
    f=pd.DataFrame({'close':101.,'previous_close':100.,'day':pd.Timestamp('2022-11-25')},index=idx)
    assert rest_of_day_decisions(f).isna().all()
