# MQTT GPS deduplication – deployment / rollback

## Why separate table?

Monthly archive script `server/mysql_tracking_move_old_month.sh` uses
`INSERT INTO gps_tracking_archive SELECT * FROM gps_tracking`.
Adding a column to only one GPS table would break the monthly archive.
Instead, the new `gps_received_keys` registry stores SHA-256 identities persistently
regardless of which month the GPS row is archived in. Neither GPS table changes.

## 1. Before deployment

- Back up the currently working `server/mqtt_gps_tracking.py`.
- Execute `server/mysql/gps_received_keys.sql` in database `mix_ztk_comp_sk`.
- Make sure the MQTT MySQL user can INSERT and SELECT against the registry:
  `SHOW GRANTS FOR CURRENT_USER();` when connected with that user.
- Check Python with `python3 -m py_compile server/mqtt_gps_tracking.py`.
- On the host, run `git fetch origin`, test the feature branch in a separate
  worktree, and do NOT merge into main until verified.

## 2. Behavior

Each valid UTC GPS timestamp is normalized to microseconds and UTC. A SHA-256
key is calculated from device ID, normalized GPS time, all original GPS
coordinates/measurements, and remaining persisted payload diagnostics. SQL ID
and **server receipt** year/month/day/hour/minute/second are excluded.

The INSERT of the key and the GPS row share the same transaction. Duplicate
keys are counted as duplicate messages and GPS INSERT is skipped. Batch
records are isolated with SQL SAVEPOINTs. An invalid or missing GPS timestamp
is logged and stored without registering a dedup key, avoiding accidental
loss of otherwise distinct records.

Output includes `stored=N, duplicate=N, errors=N, received=N`.
Errors require investigation: malformed records are skipped and not retried
by this service; upstream historical re-delivery may be needed.

This registry starts **empty**. It prevents duplicate *newly registered*
messages from the point of deployment; it does not recognize points that
already existed before deployment unless the registry is separately seeded.
Data from a prior firmware variant with different diagnostics can be stored
as a distinct measurement, matching our conservative historical cleanup.

## 3. Functional test

Publish one sample GPS JSON message to a TEST device/topic two times with the
same timestamp and payload, then confirm first stored and second duplicate.
Repeat after restarting the service; confirm registry persists. Check a new
timestamp with the same coordinates is stored normally. Check a batch that
contains repeated points and a malformed record, and inspect warnings.
Use a separate test MySQL database/service if possible, not production.

## 4. Rollback

Stop the service, restore the previous `mqtt_gps_tracking.py`, and restart.
Leave `gps_received_keys` intact so previously registered identities are
not lost on redeployment. No archive schema migration or archive script
changes are required.

## 5. November archive

Existing monthly archive script is unaffected because `gps_tracking` and
`gps_tracking_archive` retain their identical columns. Do NOT drop registry
after archive runs; dedup identities must persist across months.
