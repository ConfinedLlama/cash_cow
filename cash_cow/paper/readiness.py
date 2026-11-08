"""Read-only macOS operating checks; not trading permission or an uptime guarantee.

No broker/model calls, writes, service restarts or power-setting changes.
Raw service output can contain environment values and must never be printed.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys

LABEL = 'com.cashcow.paper'


def assess(root, config, plist, loaded, process, assertions, battery, stop=False):
    """Inspect supplied command snapshots; emit only fixed labels and numbers."""
    expected = ['/usr/bin/caffeinate', '-i', str(Path(root)/'.venv/bin/python'),
                '-u', '-m', 'cash_cow.paper', 'run', '--config', config]
    issues = []
    if (not isinstance(plist, dict) or plist.get('Label') != LABEL
            or plist.get('ProgramArguments') != expected
            or plist.get('WorkingDirectory') != str(root)):
        issues.append('installed_service_mismatch')
    block = re.search(r'^\s*arguments = \{\n(.*?)^\s*\}', loaded, re.M | re.S)
    args = [line.strip() for line in block[1].splitlines()] if block else []
    if args != expected:
        issues.append('loaded_service_mismatch')
    if not re.search(r'^\s*state = running\s*$', loaded, re.M):
        issues.append('service_not_running')
    match = re.search(r'^\s*pid = ([1-9][0-9]*)\s*$', loaded, re.M)
    pid = int(match[1]) if match else None
    # The venv interpreter resolves to the framework Python on macOS. Match its
    # complete argument suffix, not an arbitrary occurrence of the config name.
    suffix = f' -u -m cash_cow.paper run --config {config}'
    if pid is None or not process.strip().endswith(suffix):
        issues.append('worker_process_unverified')
    owned_assertion = False
    for section in re.split(r'(?=^\s*pid \d+\()', assertions, flags=re.M):
        if (re.match(r'\s*pid \d+\(caffeinate\):', section)
                and 'PreventUserIdleSystemSleep named:' in section
                and pid is not None and f'(pid {pid})' in section):
            owned_assertion = True
    if not owned_assertion:
        issues.append('worker_idle_sleep_assertion_missing')
    source = ('ac' if "Now drawing from 'AC Power'" in battery else
              'battery' if "Now drawing from 'Battery Power'" in battery else 'unknown')
    pct = re.search(r'\b(\d{1,3})%;', battery)
    percent = int(pct[1]) if pct and 0 <= int(pct[1]) <= 100 else None
    if source != 'ac':
        issues.append('external_power_not_verified')
    if stop:
        issues.append('stop_requested')
    return {'status': 'review_required' if issues else 'local_checks_passed',
            'issues': issues, 'worker_pid': pid, 'power_source': source,
            'battery_percent': percent, 'worker_idle_sleep_assertion': owned_assertion,
            'limits': 'Point-in-time local checks only. Lid closure, forced sleep, shutdown and network failure remain possible. Broker reconciliation, telemetry freshness, loaded code identity and session coverage require separate checks. No trading permission or future uptime guarantee.'}


def inspect(root, config='paper_ai_v1', home=None, run=None):
    root, home = Path(root), Path.home() if home is None else Path(home)
    run = run or subprocess.run
    failures = []

    def command(label, args):
        try:
            result = run(args, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode != 0:
                raise ValueError('Command failed')
            return result.stdout
        except (OSError, ValueError, subprocess.SubprocessError):
            failures.append(label + '_unavailable')
            return ''

    try:
        plist = plistlib.loads((home/'Library/LaunchAgents'/f'{LABEL}.plist').read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException):
        plist = None
    loaded = command('service', ['/bin/launchctl', 'print', f'gui/{os.getuid()}/{LABEL}'])
    match = re.search(r'^\s*pid = ([1-9][0-9]*)\s*$', loaded, re.M)
    process = command('process', ['/bin/ps', '-p', match[1], '-o', 'command=']) if match else ''
    result = assess(root, config, plist, loaded, process,
                    command('assertions', ['/usr/bin/pmset', '-g', 'assertions']),
                    command('power', ['/usr/bin/pmset', '-g', 'batt']),
                    (root/'data/telemetry'/config/'STOP').exists())
    result['issues'].extend(failures)
    if failures:
        result['status'] = 'review_required'
    result['as_of'] = datetime.now(timezone.utc).isoformat()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', choices=('paper_v1', 'paper_ai_v1'), default='paper_ai_v1')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Local service inspection requires macOS')
    result = inspect(Path(__file__).resolve().parents[2], args.config)
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result['issues'] else 0)


if __name__ == '__main__':
    main()
