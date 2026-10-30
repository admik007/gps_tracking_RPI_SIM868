-- Run once in mix_ztk_comp_sk before deploying mqtt_gps_tracking.py.
-- Persistent dedup across gps_tracking and gps_tracking_archive without schema changes.
-- Keys are written transactionally with gps_tracking inserts.
CREATE TABLE IF NOT EXISTS gps_received_keys (
    point_key BINARY(32) NOT NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (point_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- Verify:
-- SHOW CREATE TABLE gps_received_keys\G
-- SELECT COUNT(*) FROM gps_received_keys;
--
-- Important: this registry starts empty and protects NEW MQTT inserts.
-- Existing records in gps_tracking / gps_tracking_archive are not backfilled.
-- Never TRUNCATE this table during routine monthly archiving.
