import json
from pathlib import Path
import plistlib
import subprocess
from types import SimpleNamespace

import pytest

from cash_cow.paper.readiness import assess, inspect


def inputs(root=Path('/fixture')):
    args = ['/usr/bin/caffeinate', '-i', str(root/'.venv/bin/python'),
            '-u', '-m', 'cash_cow.paper', 'run', '--config', 'paper_ai_v1']
    return dict(root=root, config='paper_ai_v1',
                plist={'Label': 'com.cashcow.paper', 'ProgramArguments': args, 'WorkingDirectory': str(root)},
                loaded='state = running\narguments = {\n'+'\n'.join(args)+'\n}\npid = 42\n',
                process='/framework/Python -u -m cash_cow.paper run --config paper_ai_v1',
                assertions="pid 43(caffeinate): PreventUserIdleSystemSleep named: x\n Details: behalf of Python (pid 42)\n",
                lid='  |   "AppleClamshellState" = No\n',
                battery="Now drawing from 'AC Power'\n 95%; charging;")


def test_healthy_is_only_a_local_point_in_time_check():
    result = assess(**inputs())
    assert result['status'] == 'local_checks_passed'
    assert result['worker_idle_sleep_assertion']
    assert 'No trading permission' in result['limits']


@pytest.mark.parametrize('field,value,issue', [
    ('battery', "Now drawing from 'Battery Power'\n 27%; discharging;", 'external_power_not_verified'),
    ('battery', 'private-unknown-format', 'external_power_not_verified'),
    ('loaded', 'state = waiting\nprivate-secret', 'service_not_running'),
    ('process', '/python -u -m cash_cow.paper run --config paper_v1', 'worker_process_unverified'),
    ('process', '/python -u -m cash_cow.paper run --config paper_ai_v1 --other', 'worker_process_unverified'),
    ('assertions', 'pid 43(other): PreventUserIdleSystemSleep named: x (pid 42)', 'worker_idle_sleep_assertion_missing'),
    ('assertions', 'pid 43(caffeinate): PreventUserIdleSystemSleep named: x (pid 999)', 'worker_idle_sleep_assertion_missing'),
    ('plist', [], 'installed_service_mismatch'),
    ('stop', True, 'stop_requested'),
])
def test_failures_are_actionable_and_sanitized(field, value, issue):
    args = inputs(); args[field] = value
    result = assess(**args)
    assert issue in result['issues']
    assert result['status'] == 'review_required'
    assert 'private-' not in json.dumps(result)


def test_assertion_must_belong_to_the_worker_not_another_process():
    args = inputs()
    args['assertions'] = ('pid 43(caffeinate): PreventUserIdleSystemSleep named: x (pid 99)\n'
                          'pid 44(other): PreventUserIdleSystemSleep named: x (pid 42)\n')
    assert not assess(**args)['worker_idle_sleep_assertion']


def test_loaded_definition_must_match_even_if_disk_plist_matches():
    args = inputs(); args['loaded'] = args['loaded'].replace('paper_ai_v1', 'paper_v1')
    assert 'loaded_service_mismatch' in assess(**args)['issues']


def test_command_failures_do_not_echo_output_or_mutate_files(tmp_path):
    commands = []
    def run(args, **kwargs):
        commands.append(args)
        raise subprocess.TimeoutExpired(args, 10, output='private-secret')
    before = list(tmp_path.rglob('*'))
    result = inspect(tmp_path, home=tmp_path, run=run)
    assert {'service_unavailable', 'assertions_unavailable', 'power_unavailable'} <= set(result['issues'])
    assert 'private-secret' not in json.dumps(result)
    assert list(tmp_path.rglob('*')) == before
    assert all(x[0] in ('/bin/launchctl', '/usr/bin/pmset', '/usr/sbin/ioreg') for x in commands)


def test_inspection_reads_only_fixed_commands(tmp_path):
    data = inputs(tmp_path); directory = tmp_path/'Library/LaunchAgents'; directory.mkdir(parents=True)
    manifest = tmp_path/'data/telemetry/paper_ai_v1/process.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'pid': 42, 'started_at': '2026-11-19T01:00:00+00:00'}))
    (directory/'com.cashcow.paper.plist').write_bytes(plistlib.dumps(data['plist']))
    outputs = iter([data['loaded'], data['process'], data['assertions'], data['battery'], data['lid']])
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=next(outputs))
    result = inspect(data['root'], home=tmp_path, run=run)
    assert result['status'] == 'local_checks_passed'
    assert calls[1] == ['/bin/ps', '-p', '42', '-o', 'command=']
    assert len(calls) == 5
    assert result['worker_recorded_started_at'] == '2026-11-19T01:00:00+00:00'
    assert len(result['process_manifest_sha256']) == 64


@pytest.mark.parametrize('snapshot,state,issue', [
    ('  "AppleClamshellState" = Yes\n', 'closed', 'lid_closed'),
    ('', 'unknown', 'lid_state_not_verified'),
    ('"AppleClamshellState" = private-secret', 'unknown', 'lid_state_not_verified'),
    ('"AppleClamshellState" = No\n"AppleClamshellState" = Yes', 'unknown', 'lid_state_not_verified'),
    ('  | "AppleClamshellState" = No\n  | "AppleClamshellState" = malformed', 'unknown', 'lid_state_not_verified'),
    ('"AppleClamshellState" = Nope', 'unknown', 'lid_state_not_verified'),
])
def test_lid_must_be_verified_open_even_on_ac_with_owned_assertion(snapshot, state, issue):
    args = inputs(); args['lid'] = snapshot
    result = assess(**args)
    assert result['lid_state'] == state
    assert issue in result['issues']
    assert result['status'] == 'review_required'
    assert 'private-secret' not in json.dumps(result)


@pytest.mark.parametrize('manifest,issue', [
    ({'pid': 99, 'started_at': '2026-11-19T01:00:00+00:00'}, 'process_manifest_pid_mismatch'),
    ({'pid': 42, 'started_at': '2099-11-19T01:00:00+00:00'}, 'process_manifest_invalid'),
    ({'pid': True, 'started_at': '2026-11-19T01:00:00+00:00'}, 'process_manifest_invalid'),
    ({'pid': 42, 'started_at': '2026-11-19T01:00:00'}, 'process_manifest_invalid'),
    (['private-secret'], 'process_manifest_invalid'),
    (None, 'process_manifest_unavailable'),
])
def test_inspection_rejects_stale_or_unverifiable_process_manifest(tmp_path, manifest, issue):
    # Exercise the public inspection path with real files and OS-command fixtures.
    # A healthy launchd process must not mask stale or corrupt telemetry ownership.
    data = inputs(tmp_path)
    service = tmp_path/'Library/LaunchAgents/com.cashcow.paper.plist'
    service.parent.mkdir(parents=True)
    service.write_bytes(plistlib.dumps(data['plist']))
    process = tmp_path/'data/telemetry/paper_ai_v1/process.json'
    process.parent.mkdir(parents=True)
    if manifest is not None:
        process.write_text(json.dumps(manifest))
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    outputs = iter([data['loaded'], data['process'], data['assertions'], data['battery'], data['lid']])
    result = inspect(tmp_path, home=tmp_path, run=lambda *a, **kw: SimpleNamespace(returncode=0, stdout=next(outputs)))
    assert result['status'] == 'review_required'
    assert issue in result['issues']
    assert result.get('worker_recorded_started_at') is None
    assert 'private-secret' not in json.dumps(result)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
