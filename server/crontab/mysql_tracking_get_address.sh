#!/bin/bash
cd /path/to/html/where/is/page

MySQL_table3="gps_miesto";
FILE="get_url.txt";

cat ${FILE} | sort | uniq > ${FILE}.new
cat ${FILE}.new > ${FILE}
rm ${FILE}.new



for i in `cat ${FILE}`; do 
 DATA=`curl -silent $i | egrep "formatted|lat1|lon1" | sed 's/>/;/g';`
 ADDRESS=`echo ${DATA} | cut -d ';' -f2 | cut -d '<' -f1 | cstocs utf8 ascii`
 LAT=`echo $i | cut -d '=' -f4 | cut -d '&' -f1`
 LON=`echo $i | cut -d '=' -f5 | cut -d '&' -f1`
 
 if [ ! -z "${LAT}" ] && [ ! -z "${LON}" ]; then
  if [ ! -z "${ADDRESS}" ]; then 
   echo "INSERT INTO $MySQL_table3 VALUES('0','$LAT','$LON','$ADDRESS','OK');"
   echo "INSERT INTO $MySQL_table3 VALUES('0','$LAT','$LON','$ADDRESS','OK');" | mysql  --defaults-extra-file=/root/.mysql/mysqldump.cnf DATABASE
  else
   echo "INSERT INTO $MySQL_table3 VALUES('0','$LAT','$LON','no data','OK');"
   echo "INSERT INTO $MySQL_table3 VALUES('0','$LAT','$LON','no data','OK');" | mysql  --defaults-extra-file=/root/.mysql/mysqldump.cnf DATABASE
  fi
 fi
 sleep 0.1
done
> ${FILE}
