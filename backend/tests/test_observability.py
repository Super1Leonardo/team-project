from __future__ import annotations

import unittest

from backend.app.core.observability import RequestMetricsTracker


class RequestMetricsTrackerTests(unittest.TestCase):
    def test_snapshot_reports_rps_latency_and_errors(self) -> None:
        clock = _FakeClock(100.0)
        tracker = RequestMetricsTracker(window_seconds=10, clock=clock.now)

        tracker.request_started()
        clock.advance(1.0)
        tracker.request_finished(status_code=200, duration_ms=50.0)

        tracker.request_started()
        clock.advance(4.0)
        tracker.request_finished(status_code=503, duration_ms=150.0)

        snapshot = tracker.snapshot()

        self.assertEqual(snapshot.requests, 2)
        self.assertEqual(snapshot.errors, 1)
        self.assertEqual(snapshot.inflight, 0)
        self.assertAlmostEqual(snapshot.rps, 0.4, places=2)
        self.assertAlmostEqual(snapshot.rpm, 24.0, places=2)
        self.assertAlmostEqual(snapshot.error_rate_percent, 50.0, places=2)
        self.assertAlmostEqual(snapshot.avg_latency_ms, 100.0, places=2)
        self.assertAlmostEqual(snapshot.p95_latency_ms, 145.0, places=2)
        self.assertAlmostEqual(snapshot.uptime_seconds, 5.0, places=2)

    def test_snapshot_prunes_requests_outside_window(self) -> None:
        clock = _FakeClock(0.0)
        tracker = RequestMetricsTracker(window_seconds=10, clock=clock.now)

        tracker.request_started()
        tracker.request_finished(status_code=200, duration_ms=25.0)

        clock.advance(12.0)
        tracker.request_started()
        tracker.request_finished(status_code=200, duration_ms=40.0)

        snapshot = tracker.snapshot()

        self.assertEqual(snapshot.requests, 1)
        self.assertEqual(snapshot.errors, 0)
        self.assertAlmostEqual(snapshot.avg_latency_ms, 40.0, places=2)
        self.assertAlmostEqual(snapshot.p95_latency_ms, 40.0, places=2)

    def test_snapshot_tracks_inflight_requests(self) -> None:
        clock = _FakeClock(10.0)
        tracker = RequestMetricsTracker(window_seconds=60, clock=clock.now)

        tracker.request_started()

        snapshot = tracker.snapshot()

        self.assertEqual(snapshot.requests, 0)
        self.assertEqual(snapshot.inflight, 1)


class _FakeClock:
    def __init__(self, value: float) -> None:
        self.value = value

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


if __name__ == "__main__":
    unittest.main()

