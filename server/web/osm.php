<?php
$starttime = explode(' ', microtime());
$starttime = $starttime[1] + $starttime[0];


$PORT = $_SERVER["SERVER_PORT"];
if ($PORT == '80') {
$HTTP='http://';
}
else {
$HTTP='https://';
}

$MAPA=$HTTP.'{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';


if(isset($_GET["id"])) $id=$_GET["id"];
if(isset($_GET["lat"])) $lat=$_GET["lat"];
if(isset($_GET["lon"])) $lon=$_GET["lon"];
if(isset($_GET["zoom"])) $zoom=$_GET["zoom"];
if(isset($_GET["day"])) $day=$_GET["day"];
if(isset($_GET["month"])) $month=$_GET["month"];
if(isset($_GET["year"])) $year=$_GET["year"];
if(isset($_GET["device"])) $device=$_GET["device"];
if(isset($_GET["devicerpi"])) $devicerpi=$_GET["devicerpi"];
$tracking_list_db_row=0;

if ((empty($_GET["day"])) && (empty($_GET["month"])) && (empty($_GET["year"]))) {
 $day = Date("d");
 $month = Date("m");
 $year = Date("Y");
} else {
 $day=$_GET["day"];
 $month=$_GET["month"];
 $year=$_GET["year"];
}

if ((empty($_GET["lat"])) && (empty($_GET["lon"])) && (empty($_GET["zoom"]))) { 

########## More points (day)
 @include"_config.php";


 $REQUESTED=$month;
 $CURRENT=Date("m");
 $CURRENTLAST=date("m", strtotime( date( "Y-m-d", strtotime( date("Y-m-d") ) ) . "-1 month" ) );
 if (($CURRENT == $REQUESTED) || ($CURRENTLAST == $REQUESTED)) {
  $MySQL_table=$MySQL_table1;
 }
 else {
  $MySQL_table=$MySQL_table2;
 }

 $sql = "SELECT lat, lon, time FROM $MySQL_table WHERE devicerpi='$devicerpi' AND lat IS NOT NULL AND lon IS NOT NULL AND lat <> 0 AND lon <> 0 AND time >= '$year-$month-$day 00:00:00' AND time < '$year-$month-$day 23:59:59' ORDER BY time ASC ";

 $tracking_list_db = mysqli_query($spojenie,$sql);
 if (!$tracking_list_db || mysqli_num_rows($tracking_list_db)==0) {
  $lat='48.700000';
  $lon='20.100000';
  $zoom='13';
  $marker='var trackPoints=[];';
 } else {
  $tracking_list_db_row=mysqli_num_rows($tracking_list_db);
  if ($tracking_list_db_row < 20000) {
   $step=1;
  } elseif ($tracking_list_db_row < 30000) {
   $step=2;
  } elseif ($tracking_list_db_row < 60000) {
   $step=5;
  } else {
   $step=10;
  }
  $marker='var trackPoints = [
';

  $last_lat = null;
  $last_lon = null;
  $last_time = null;
  while ($entries = mysqli_fetch_assoc($tracking_list_db)) {
   $lat_now = $entries['lat'];
   $lon_now = $entries['lon'];
   $time_now = $entries['time'];
   $break_line = false;
   if ($last_time !== null) {
    // kontrola času medzi bodmi
    $time_diff = strtotime($time_now) - strtotime($last_time);
    if ($time_diff > 120) {
     $break_line = true;
    }
    // kontrola vzdialenosti medzi bodmi
    $distance = sqrt(
     pow(($lat_now-$last_lat)*111000,2) +
     pow(($lon_now-$last_lon)*111000,2)
    );
    if ($distance > 1000) {
     $break_line = true;
    }
   }
   // prerušenie čiary
   if ($break_line) {
    $marker .= "null,
";
   }
   $marker .= '['.$lat_now.','.$lon_now."],
";
   $last_lat=$lat_now;
   $last_lon=$lon_now;
   $last_time=$time_now;
   $lat=$lat_now;
   $lon=$lon_now;
  }
  $marker = rtrim($marker,",\n");
  $marker .= '];';
 }
mysqli_close($spojenie);
} else {
########## One single point ##########
 $lat_now=$_GET["lat"];
 $lon_now=$_GET["lon"];
 $marker='var trackPoints = [['.$lat_now.','.$lon_now.']];';

}


?>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
 <title> GPS Tracking </title>
 <meta http-equiv="Expires" CONTENT="Sun, 12 May 2003 00:36:05 GMT">
 <meta http-equiv="Pragma" CONTENT="no-cache">
 <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
 <meta http-equiv="Cache-control" content="no-cache">
 <meta http-equiv="Content-Language" content="sk">
 <meta name="GOOGLEBOT" CONTENT="noodp">
 <meta name="pagerank" content="10">
 <meta name="msnbot" content="robots-terms">
 <meta name="revisit-after" content="2 days">
 <meta name="robots" CONTENT="index, follow">
 <meta name="alexa" content="100">
 <meta name="distribution" content="Global">
 <meta name="keywords" lang="en" content="gps, tracking">
 <meta name="description" content="GPS Tracking">
 <link rel="stylesheet" href="leaflet.css">
 <script type="text/javascript" src="leaflet.js"></script>
</head>
<body bgcolor="black" text="white">
<?php

echo "<center>
<font color=\"red\"><b>Position:</b></font> ".$lat." / ".$lon."<br>
<font color=\"red\"><b>Points:</b></font> ".$tracking_list_db_row." (total) <br>
<font color=\"red\"><b>Screen:</b></font> "?>
<script>
 document.write(window.innerWidth-"50"+"px x ");
 document.write(window.innerHeight-"200"+"px");
</script>
<div id="status"></div>

<?php "</center> \n"; ?>

<table id="map" width="100"><td id="maph" height="100">
</td></table>

<script>
document.getElementById("map").width = window.innerWidth-"50";
document.getElementById("maph").height = window.innerHeight-"200";
</script>

<script type="text/javascript">
    map = L.map('map').setView([<?php echo $lat;?>, <?php echo $lon;?>], 10);
    L.tileLayer('<?php echo $MAPA;?>', { maxZoom: 18,}).addTo(map);

    var popup = L.popup();
    function onMapClick(e) {
        popup
        .setLatLng(e.latlng)
        .setContent("<b>Your position on map</b> <br>" + "<b>Lat:</b> " + e.latlng.lat.toFixed(6) + "<br> <b>Lon:</b> " + e.latlng.lng.toFixed(6))
        .openOn(map);
    }
    map.on('click', onMapClick);


<?php echo $marker;?>

var track = [];
var segment = [];
for (var i = 0; i < trackPoints.length; i++) {
 if (trackPoints[i] === null) {
  if (segment.length > 1) {
   track.push(segment);
  }
  segment = [];
 } else {
  segment.push(trackPoints[i]);
 }
}

// posledný úsek
if (segment.length > 1) {
 track.push(segment);
}

if (trackPoints.length > 1) {
 // vykresli trasu
 for (var i = 0; i < track.length; i++) {
  L.polyline(track[i], {
   color: 'black',
   weight: 4,
   opacity: 1
  }).addTo(map);
 }
} else if (trackPoints.length == 1) {
 // vykresli iba bod
 L.circleMarker(trackPoints[0], {
  radius: 6,
  color: '#000000',
  fillColor: '#FF0000',
  fillOpacity: 1
 }).addTo(map);
}



</script>

<?php
$mtime = explode(' ', microtime());
$totaltime = $mtime[0] + $mtime[1] - $starttime;
printf ('<font color="FF0000"> Stránka vygenerovaná za %.3f sekundy. </font>', $totaltime);
?>
</body>
</html>
