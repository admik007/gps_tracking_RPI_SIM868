# Automatic BTS registration from GPS MQTT

Adds only previously unseen **GSM** cells to the single active `bts_tracking`
table after a **new** GPS measurement is inserted. No new BTS table is needed.

## Required schema

This feature requires the normalized `bts_tracking` migrated on 2026-10-30:
- `UNIQUE KEY idx_bts_identity (technology,mcc,mnc,cellid)`
- `mcc,mnc VARCHAR(3)`, `cellid BIGINT`
- `lat,lon,alt,time,device,bsic,lac,address`
- `location_type`, `technology`, `first_seen`, `last_seen`,
  `observations`, `source`.

The user's migration has already swapped `bts_tracking_new` into
`bts_tracking`. Do **not** deploy this branch against the legacy schema.

## Semantics

- Accept only MCC of exactly 3 decimal digits, MNC of 2 or 3 digits and
  positive signed BIGINT CellID. Missing/zero network IDs are ignored.
- Preserve leading zero in MNC (e.g. `02`).
- Insert new cells with technology `GSM`, address `no info`,
  source `gps_tracker` and observations `1`.
- With a valid GPS fix and plausible coordinates, store that position
  with `location_type=observation`: **it is not the tower's location**.
- Otherwise use empty coordinates and `location_type=unknown`.
- `first_seen` and `last_seen` use the GPS measurement timestamp in UTC
  if parseable, otherwise UTC receipt time.
- Existing cell with `location_type=unknown` and a newly received valid GPS
  fix is updated **once** to `observation`; only `lat`, `lon`, `alt`, and
  `location_type` change. The reported coordinates are the reception
  position, not the physical BTS location. Logs `BTS LOCATED: ...`.
- Existing `observation` and `tower` records are untouched, including
  their addresses and coordinates. A later valid fix does not move the point.
- Retransmissions previously registered in `gps_received_keys` do not
  attempt a BTS insert. An older GPS row received before this feature was
  introduced can still register a new BTS if resent as a newly stored row.
- BTS changes are best effort with an inner SQL SAVEPOINT. A BTS SQL failure
  is logged and does not discard the valid GPS measurement. This means a
  BTS failure is **not automatically retried** for that measurement.

## Deploy/test checklist

1. Confirm old BTS writers are stopped or adapted to normalized schema.
2. Confirm schema and grants for the exact MySQL user in
   `server/mqtt_db_connect.conf` (do not display the password):
   `SHOW GRANTS FOR CURRENT_USER();` when logged in as that user.
   The user needs `INSERT` and the upsert's `UPDATE` permission on
   `bts_tracking`, as well as existing GPS permissions.
3. Update the TEST worktree from
   `feature/mqtt-auto-register-bts`; `python3 -m py_compile
   server/mqtt_gps_tracking.py`.
4. Run a separate test process with isolated MQTT topic/database or controlled
   dedicated test CellID. **Do not run two concurrent production subscribers
   on the same topic.** Prefer a cloned temporary database / topics and
   test one new cell, a duplicate GPS measurement, and an existing tower.
5. Verify new cell insertion:
   ```sql
   SELECT mcc,mnc,cellid,address,location_type,source,first_seen,
          last_seen,observations,lat,lon
   FROM bts_tracking
   WHERE technology='GSM' AND mcc='231' AND mnc='02' AND cellid=59651;
   ```
   This example is a real-world-looking identity, **not necessarily a new
   cell**. Use a dedicated test identity in isolated DB.
6. Verify original GPS logs still say
   `MYSQL: stored=1, duplicate=0, errors=0, received=1` on new point.
   New BTS logs only `BTS NEW: ...` when inserted; never on duplicate.
7. Register a new cell while GPS is invalid: it should be `unknown`.
   On the next new valid GPS measurement for that cell, expect `BTS LOCATED`
   and `observation` coordinates. Additional fixes must not move the position.
8. Confirm known tower address/coordinates unchanged by repeated observations.
8. Only after acceptance merge PR and restart
   `mqtt_gps_mysql.service` (existing systemd service name).

### Rollback

Deploy previous Python script and restart the service. BTS records already
added are not removed by code rollback; they can be reviewed by
`source = 'gps_tracker'`. Do not drop historical BTS tables.

### Future work

- Rework the BTS web to distinguish tower vs reception observation.
- Normalize future LTE/NR cell identities separately; this branch treats
  SIM868 traffic as GSM only.
- Consider updating last_seen/observation counts with a separate, explicitly
  scoped policy once replay and older BTS devices are accounted for.
