# Pre-session readiness incident - November 23, 2026

## Observed change

At 08:03:43 UTC, the installed and loaded paper_ai_v1 service passed local readiness with AC power, 76% battery, an open lid and its owned idle-sleep assertion.
The combined preflight at 08:04:01 UTC passed its market-closed checks.
By 12:35:12 UTC, the same worker PID 66917 was on battery at 53%, with the lid open and the idle-sleep assertion still present.
Its recorded start and process-manifest hash were unchanged.
At 12:37:31 UTC, preflight required attention for power and news health; heartbeat age was 20.74 seconds and news success age was 614.13 seconds.
These are point-in-time observations, not continuous uptime measurements.

## Investigation

The sanitized macOS power-log audit covers 08:00 through 12:36:30 UTC.
It records clamshell sleep at 08:04:06 UTC and 11:21:59 UTC, equivalent to 16:04:06 and 19:21:59 Singapore.
It also records maintenance/sleep-service transitions and DarkWake periods, with a full Wake at 12:34:10 UTC.
DarkWake does not establish usable network, model access or uninterrupted runner execution.
The retained log hash is f861a8ce083fd9ec6985286801fa092784343b31d34b50dd12d06f072a89964b.
No exact sleep duration or sole causal explanation is inferred from these transitions.

The collector status observed at 12:35 UTC retained last_success 12:27:17.027677 UTC, a coverage-gap flag, no error and no truncation.
Its successful request covered only 12:12:17 through 12:27:17 UTC and added zero revisions.
Code inspection confirms that a gap over fifteen minutes between successful collections is flagged, with bounded overlapping windows rather than retrospective observation backdating.
The latest archive integrity audit passed, which does not resolve this continuity gap.
The subsequent age over ten minutes separately fails the current news-freshness requirement.
Do not clear the flag manually or treat old stories as first observed during downtime.

Read-only broker reconciliation earlier today found no positions, open orders, pending intents or cash difference, with USD 2,000 sleeve cash.
No unknown order status or exposure was detected at that snapshot.
The pre-session interruption is not yet a missed November 23 regular session: the broker calendar still places its open at 14:30 UTC, or 22:30 Singapore.
The original thirteen incomplete sessions remain preserved.

## Response and follow-up

The user was notified that AC power must be restored and the lid kept open through November 24 at 05:15 Singapore.
Maintenance did not restart the service, alter the frozen strategy, invoke a new model request, reset state, or submit an order.
The next successful scheduled collector poll can establish current health; it cannot reconstruct missed observations.
Recheck readiness and news status before the open, then assess actual attendance and broker fills afterward.
The daily report records any later recovery separately from this incident evidence.
