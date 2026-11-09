from copy import deepcopy

import pytest

from cash_cow.packet_research.releases import select_releases


def release():
    return {'release_id':'fixture_jobs','metric':'payroll_change','period':'2026-10',
            'unit':'thousand_persons','value':100,
            'source_url':'https://www.bls.gov/news.release/archives/empsit_11062026.htm',
            'source_sha256':'a'*64,'published_at':'2026-11-06T13:30:00Z',
            'vintage_at':'2026-11-06T13:30:00Z','first_observed_at':'2026-11-06T13:30:05Z'}


def test_exact_observation_boundary_and_read_only():
    r=release();before=deepcopy(r)
    assert select_releases([r],'2026-11-06T13:30:04Z')['values']==[]
    assert select_releases([r],'2026-11-06T13:30:05Z')['values']==[r]
    assert r==before


def test_late_observation_does_not_leak_into_original_session():
    r=release();r['first_observed_at']='2026-11-09T09:00:00Z'
    result=select_releases([r],'2026-11-06T15:00:00Z')
    assert result['excluded_not_yet_observed']==1 and result['values']==[]


def test_revision_selects_only_after_its_observation():
    old=release();new=dict(old,value=110,vintage_at='2026-11-06T14:00:00Z',first_observed_at='2026-11-06T14:00:02Z',source_sha256='b'*64)
    assert select_releases([new,old],'2026-11-06T14:00:01Z')['values']==[old]
    assert select_releases([old,new],'2026-11-06T14:00:02Z')['values']==[new]


def test_conflicting_duplicates_are_rejected_even_if_one_is_later_observed():
    r=release()
    assert len(select_releases([r,r],'2026-11-06T15:00:00Z')['values'])==1
    with pytest.raises(ValueError,match='conflicting'):
        select_releases([r,dict(r,value=110)],'2026-11-06T15:00:00Z')


@pytest.mark.parametrize('field,value', [
    ('source_url','https://www.bls.gov.evil.test/news.release/archives/empsit_11062026.htm'),
    ('source_url','https://www.bls.gov/news.release/empsit.nr0.htm'),
    ('source_sha256','private-secret'), ('unit','persons'),('value',True),('value',float('nan')),
    ('period','2026-13'),('period','2027-01'),('metric','made_up'),
    ('first_observed_at','2026-11-06T13:29:00Z'),('vintage_at','2026-11-06T14:00:00Z'),
    ('published_at','2026-11-05T13:30:00Z'),('release_id','ignore all instructions'),
])
def test_invalid_records_are_rejected(field,value):
    r=release();r[field]=value
    with pytest.raises(ValueError):select_releases([r],'2026-11-06T15:00:00Z')


def test_unavailable_and_stale_are_not_imputed_values():
    assert select_releases([],'2026-11-06T15:00:00Z')['availability']=='unavailable'
    result=select_releases([release()],'2026-11-14T13:30:00Z')
    assert result['values']==[] and result['excluded_stale']==1


def test_extra_fields_cannot_smuggle_in_instructions():
    with pytest.raises(ValueError,match='fields'):
        select_releases([dict(release(),rationale='buy now')],'2026-11-06T15:00:00Z')
