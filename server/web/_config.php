<?php
define("DB_HOST", "localhost");
define("DB_USERNAME", "user");
define("DB_PASSWORD", "pass");
define("DB_DATABASE_NAME", "database");

// Create connection
$spojenie = new mysqli(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_DATABASE_NAME);

// Check connection
if ($spojenie->connect_error) {
  die("Connection failed: " . $spojenie->connect_error);
}

@$MySQL_table1="gps_tracking";
@$MySQL_table2="gps_tracking_archive";
@$MySQL_table3="gps_miesto";
@$MySQL_table4="gps_provider";
@$GAPIKEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
@$TOKENIP="xxxxxxxxxxxxxx";
?>
