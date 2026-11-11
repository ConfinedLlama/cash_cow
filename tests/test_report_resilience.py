"""No broker connection. Failure injection exercises control-loop continuity."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import cash_cow.paper.__main__ as cli


def test_report_read_failure_does_not_stop_tick_or_cleanup(tmp_path, monkeypatch, capsys):
    runner = Mock()
    runner.tick.side_effect = [{'kind': 'market_closed'}, {'kind': 'stopped'}]
    reporter = Mock(side_effect=[OSError(11, 'private file detail'), tmp_path/'REPORT.md'])
    monkeypatch.setattr(cli, 'write_report', reporter)
    sleep = Mock();monkeypatch.setattr(cli.time, 'sleep', sleep)
    stop, provider = Mock(), Mock()
    cli.run_loop(runner, tmp_path, {'poll_seconds': 15}, news_stop=stop, provider=provider)
    assert runner.tick.call_count == reporter.call_count == 2
    runner.event.assert_not_called()  # Reporting cannot rewrite trading state.
    sleep.assert_called_once_with(60)
    stop.set.assert_called_once();provider.close.assert_called_once()
    err = capsys.readouterr().err
    assert json.loads(err)['status'] == 'refresh_failed'
    assert 'private' not in err


def test_report_failure_preserves_trade_error_path_and_once_semantics(tmp_path, monkeypatch):
    runner = Mock();runner.tick.side_effect = cli.TransportError('sanitized transport failure')
    runner.event.return_value = {'kind': 'needs_attention'}
    monkeypatch.setattr(cli, 'write_report', Mock(side_effect=ValueError('private report')))
    sleep = Mock();monkeypatch.setattr(cli.time, 'sleep', sleep)
    cli.run_loop(runner, tmp_path, {'poll_seconds': 15}, once=True)
    runner.event.assert_called_once_with('needs_attention', reason='sanitized transport failure', error_type='TransportError')
    assert runner.tick.call_count == 1
    sleep.assert_not_called()


def test_report_failure_does_not_mask_authoritative_journal_io_error(tmp_path, monkeypatch):
    runner = Mock();runner.tick.side_effect = OSError(11, 'journal unavailable')
    reporter = Mock();monkeypatch.setattr(cli, 'write_report', reporter)
    with pytest.raises(OSError):
        cli.run_loop(runner, tmp_path, {'poll_seconds': 15}, once=True)
    reporter.assert_not_called()


def test_atomic_report_preserves_old_bytes_when_publication_fails(tmp_path, monkeypatch):
    target = tmp_path/'REPORT.md';target.write_text('previous complete report')
    monkeypatch.setattr(cli.os, 'replace', Mock(side_effect=OSError('synthetic publication failure')))
    with pytest.raises(OSError):cli.atomic_report(target, 'next report')
    assert target.read_text() == 'previous complete report'
    assert list(tmp_path.iterdir()) == [target]


def test_successful_report_is_complete_private_and_leaves_no_temp(tmp_path):
    target = tmp_path/'REPORT.md';target.write_text('old')
    cli.atomic_report(target, 'new complete report')
    assert target.read_text() == 'new complete report'
    assert target.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [target]


def test_broken_diagnostic_sink_does_not_stop_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, 'write_report', Mock(side_effect=OSError(11, 'private report')))
    monkeypatch.setattr(cli.sys, 'stderr', Mock(write=Mock(side_effect=OSError('sink unavailable'))))
    assert cli.refresh_report(tmp_path, {}) is False
