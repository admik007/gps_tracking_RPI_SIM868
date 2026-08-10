#!/bin/bash
DATEN=$(date -d "$(date +%Y-%m-01)" +%Y-%m)
SQL_DATE="${DATEN}-01 00:00:00"

echo "
START TRANSACTION;
INSERT INTO gps_tracking_archive SELECT * FROM gps_tracking WHERE time < '${SQL_DATE}' ORDER BY id DESC;
DELETE FROM gps_tracking WHERE time < '${SQL_DATE}';
COMMIT;
" | mysql --defaults-extra-file=/root/.mysql/mysqldump.cnf DATABASE
