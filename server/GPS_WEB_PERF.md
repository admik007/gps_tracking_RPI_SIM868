# GPS web: performance baseline

This branch intentionally changes **only instrumentation** in `server/web/index.php`.
SQL queries, sampling step, calendar, address behavior and output are unchanged.
The profiling table appears only with `perf=1` on the TEST deployment.

## Test deployment

```bash
cd /opt/gps_tracking_RPI_SIM868
git fetch origin
git -C /opt/gps_tracking_calendar_test switch --detach origin/feature/gps-web-performance-profiling
php -l /opt/gps_tracking_calendar_test/server/web/index.php
```

Visit `https://gps.ztk-comp.sk/calendar-test/?year=2026&month=10&day=25&devicerpi=bd6718189a7ba68a&perf=1`

For comparison repeat on a small day (`2026-05-02`) and a busy
archive day (`2021`). Use **the same date and vehicle** for subsequent
comparisons and request the page 2-3 times to account for I/O caches.
Note that the URL displays time only to the requester; `perf=1` is
not an access-control mechanism, so keep this on the test environment.

## Profiling fields

- `count_query`: SQL COUNT of GPS points for selected device/day
- `gps_query`: sampled GPS SELECT with BTS LEFT JOIN (buffered mysqli time)
- `devices_query`: gps_devices SELECT
- `calendar_query`: monthly GPS activity grouping query
- `calendar_html`: PHP generation of two-line calendar HTML
- `address_lookups`: wall time of uncached address lookup blocks
  (including SQL and missing-coordinate file log writes)
- `gps_rows_render_and_addresses`: complete GPS rows loop, including addresses
- `gps_row_processing_excluding_lookups`: rows loop less uncached lookup blocks
- `total_request`: request time from profiler initialization to profile output

Counters include sampled points, original points, cache hits, number of
address SQL queries, and missing-coordinate log writes. Timings in milliseconds.

## Interpretation

The loop may dominate because each distinct truncated lat/lon performs
a separate `gps_address` lookup (N+1). Calendar grouping may dominate
large 2021 months due to grouping on converted timestamps.

**No SQL modification or index creation in this branch.** Inspect evidence
first, then prepare optimization branch and measure the same test cases
with an identical environment.

## Limitations

`gps_query` times mysqli's buffered SELECT call but not all downstream
result fetching/rendering; those are part of the rows-loop timings.
The measured total excludes a small initial HTML header emitted before
profiler initialization.
