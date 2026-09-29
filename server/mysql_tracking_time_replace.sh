#!/bin/bash

echo "UPDATE gps_tracking set time = replace(time, 'Z', ''); UPDATE gps_tracking set time = replace(time, 'T', ' '); " | mysql  --defaults-extra-file=/root/.mysql/mysqldump.cnf DATABASE
