<?php
if (empty($_GET["time"])) {
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
 <title> GPS logging and tracking </title>
 <link rel="SHORTCUT ICON" href="favicon.ico" type="image/x-icon">
 <meta http-equiv="Expires" CONTENT="Sun, 12 May 2003 00:36:05 GMT">
 <meta http-equiv="Pragma" CONTENT="no-cache">
 <meta http-equiv="Content-Type" content="text/html; charset=windows-1250">
 <meta http-equiv="Cache-control" content="no-cache">
 <meta http-equiv="Content-Language" content="sk">
 <meta name="google-site-verification" content="GHY_X_yeijpdBowWr_AKSMWAT8WQ-ILU-Z441AsYG9A">
 <meta name="GOOGLEBOT" CONTENT="noodp">
 <meta name="pagerank" content="10">
 <meta name="msnbot" content="robots-terms">
 <meta name="msvalidate.01" content="B786069E75B8F08919826E2B980B971A">
 <meta name="revisit-after" content="2 days">
 <meta name="robots" CONTENT="index, follow">
 <meta name="alexa" content="100">
 <meta name="distribution" content="Global">
 <meta name="keywords" lang="sk" content="gps, logging, tracking">
 <meta name="description" content="Webpage for GPS logging">
 <meta name="Author" content="ZTK-Comp WEBHOSTING">
 <meta name="copyright" content="(c) 2015 ZTK-Comp">
 <link href="calendar.css" type="text/css" rel="stylesheet">
</head>
<body bgcolor="silver">

<?php
date_default_timezone_set('Europe/Bratislava');
} else {
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
 <title> GPS </title>
</head>
<body>
<?php
}

$starttime = explode(' ', microtime());
$starttime = $starttime[1] + $starttime[0];

$ip=$_SERVER["REMOTE_ADDR"]; 
@include"_config.php";


if (empty($_GET["day"])) $day=Date("d");
if (isset($_GET["day"])) $day=$_GET["day"];

if (empty($_GET["month"])) $month=Date("m");
if (isset($_GET["month"])) $month=$_GET["month"]; 

if (empty($_GET["year"])) $year=Date("Y");
if (isset($_GET["year"])) $year=$_GET["year"];

if (empty($_GET["hour"])) $hour=Date("H");
if (isset($_GET["hour"])) $hour=$_GET["hour"];

if (empty($_GET["minute"])) $minute=Date("i");
if (isset($_GET["minute"])) $minute=$_GET["minute"];

if (empty($_GET["second"])) $second=Date("s");
if (isset($_GET["second"])) $second=$_GET["second"];

if (isset($_GET["lat"])) $lat=$_GET["lat"];
if (isset($_GET["lon"])) $lon=$_GET["lon"];
if (isset($_GET["alt"])) $alt=round($_GET["alt"]);

if (empty($_GET["acc"])) $acc="10.0";
if (isset($_GET["acc"])) $acc=$_GET["acc"];

if (empty($_GET["spd"])) $spd="0";
if (isset($_GET["spd"])) $spd=$_GET["spd"];

if (empty($_GET["speed"])) $spd="0";
if (isset($_GET["speed"])) $spd=$_GET["speed"];


if (isset($_GET["sat"])) $sat=$_GET["sat"];

if (empty($_GET["bat"])) $bat="";
if (isset($_GET["bat"])) $bat=$_GET["bat"];


if (empty($_GET["device"])) $device="";
if (isset($_GET["device"])) $device=$_GET["device"];

if (empty($_GET["devicerpi"])) $devicerpi="";
if (isset($_GET["devicerpi"])) $devicerpi=$_GET["devicerpi"];

if (empty($_POST["devicerpi"])) $_POST["devicerpi"]=$devicerpi;
if (isset($_POST["devicerpi"])) $devicerpi=$_POST["devicerpi"];


if (empty($_GET["direction"])) $direction="0.0";
if (isset($_GET["direction"])) $direction=$_GET["direction"];

if (empty($_GET["dir"])) $direction="0.0";
if (isset($_GET["dir"])) $direction=$_GET["dir"];

if (empty($_GET["temprpi"])) $temprpi="";
if (isset($_GET["temprpi"])) $temprpi=$_GET["temprpi"];

if (empty($_GET["loadrpi"])) $loadrpi="";
if (isset($_GET["loadrpi"])) $loadrpi=$_GET["loadrpi"];



### BTS RELATED
if (empty($_GET["MCC"])) $mcc="";
if (isset($_GET["MCC"])) $mcc=$_GET["MCC"];

if (empty($_GET["MNC"])) $mnc="";
if (isset($_GET["MNC"])) $mnc=$_GET["MNC"];

if (empty($_GET["BSIC"])) $bsic="";
if (isset($_GET["BSIC"])) $bsic=$_GET["BSIC"];

if (empty($_GET["CELLID"])) $cellid="";
if (isset($_GET["CELLID"])) $cellid=$_GET["CELLID"];

if (empty($_GET["LAC"])) $lac="";
if (isset($_GET["LAC"])) $lac=$_GET["LAC"];



$REQUESTED=$month;
$CURRENT=Date("m");
$CURRENTLAST=date("m", strtotime( date( "Y-m-d", strtotime( date("Y-m-d") ) ) . "-0 month" ) );
if (($CURRENT == $REQUESTED) || ($CURRENTLAST == $REQUESTED)) {
 $MySQL_table=$MySQL_table1;
}
else {
 $MySQL_table=$MySQL_table2;
}


$count_sql = "SELECT COUNT(*) AS total FROM $MySQL_table WHERE devicerpi='$devicerpi' AND time >= CONVERT_TZ('$year-$month-$day 00:00:00', 'Europe/Bratislava', 'UTC') AND time < CONVERT_TZ('$year-$month-$day 00:00:00' + INTERVAL 1 DAY, 'Europe/Bratislava', 'UTC') ";
$count_result = mysqli_query($spojenie,$count_sql);
$count_row = mysqli_fetch_assoc($count_result);
$tracking_list_db_row_total = $count_row['total'];

$step = 1;

if ($tracking_list_db_row_total > 2000) {
 $step = 2;   // približne 1 bod/min
}
if ($tracking_list_db_row_total > 4000) {
 $step = 3;   // približne 1 bod/min
}
if ($tracking_list_db_row_total > 6000) {
 $step = 4;   // približne 1 bod/min
}
if ($tracking_list_db_row_total > 8000) {
 $step = 5;   // približne 1 bod/min
}
if ($tracking_list_db_row_total > 10000) {
 $step = 6;   // približne 1 bod/min
}
if ($tracking_list_db_row_total > 15000) {
 $step = 7;   // približne 1 bod/min
}
if ($tracking_list_db_row_total > 20000) {
 $step = 10;   // každý 10. bod
}
if ($tracking_list_db_row_total > 25000) {
 $step = 30;
}


$sql = "SELECT *, time FROM $MySQL_table WHERE devicerpi='$devicerpi' AND time >= CONVERT_TZ('$year-$month-$day 00:00:00', 'Europe/Bratislava', 'UTC') AND time <  CONVERT_TZ('$year-$month-$day 00:00:00' + INTERVAL 1 DAY, 'Europe/Bratislava', 'UTC') AND id MOD $step = 0 ORDER BY time DESC";
$tracking_list_db = mysqli_query($spojenie,$sql);


$tracking_list_db_row = mysqli_num_rows ($tracking_list_db);

$tracking_list_db_devicesrpi = mysqli_query($spojenie,"SELECT DISTINCT(devicerpi) FROM $MySQL_table WHERE devicerpi != '' AND time like '$year-$month-$day%' order by device asc");
$tracking_list_db_devicesrpi_row = mysqli_num_rows ($tracking_list_db_devicesrpi);

$sql = "SELECT COUNT(DISTINCT devicerpi) AS total FROM $MySQL_table WHERE devicerpi <> '' ";
$result = mysqli_query($spojenie,$sql);
$row = mysqli_fetch_assoc($result);
$tracking_list_db_devicesrpi_total_row = $row['total'];


if ( $devicerpi == '' ) {
 $selected_devicerpi=" >>> Vyberte si zariadenie <<< ";
} else {
 $selected_devicerpi = " >>> Vybrane: ".$devicerpi." <<< ";
}

echo "<table border=\"0\" width=\"260\" align=\"center\">
 <tr>
  <td align=\"center\">
   <form method=\"post\" action=\"index.php?year=".$year."&amp;month=".$month."&amp;day=".$day."&amp;devicerpi=".$devicerpi."\">
    <select name=\"devicerpi\">
     <option value=\"".$devicerpi."\" selected> ".$selected_devicerpi."</option>
";

 for ($i = 1; $i <= $tracking_list_db_devicesrpi_row; $i++) {
  if ( $i == 1 ) $i = '01';
  if ( $i == 2 ) $i = '02';
  if ( $i == 3 ) $i = '03';
  if ( $i == 4 ) $i = '04';
  if ( $i == 5 ) $i = '05';
  if ( $i == 6 ) $i = '06';
  if ( $i == 7 ) $i = '07';
  if ( $i == 8 ) $i = '08';
  if ( $i == 9 ) $i = '09';
  $devicerpientries = mysqli_fetch_array($tracking_list_db_devicesrpi, MYSQLI_ASSOC);
  $devicerpiinfo=$devicerpientries["devicerpi"];
  $devicerpientries_details = mysqli_query($spojenie,"SELECT device FROM $MySQL_table WHERE devicerpi='$devicerpiinfo' LIMIT 1");
  $devrpientries = mysqli_fetch_array ($devicerpientries_details, MYSQLI_ASSOC);
  $devrpiinfo = $devrpientries["device"];
  echo "     <option value=\"".$devicerpiinfo."\"> ".$i." => ".$devrpiinfo." - ".$devicerpiinfo." </option>
"; 
}

echo "    </select>
    <input type=\"submit\" value=\"Potvrdit\">
   </form>
  </td>
 </tr>
 <tr>
  <td align=\"center\">";
 if ($tracking_list_db_row != "0") {
  echo $tracking_list_db_row." / ".$tracking_list_db_row_total."<br>";
 } else {
  echo "<br>";
 }
echo "   <a href=\"http://".$_SERVER["SERVER_NAME"]."/osm.php?year=$year&amp;month=$month&amp;day=$day&amp;devicerpi=$devicerpi\" target=\"_blank\" style=\"text-decoration:none\"><b>Zobraz dnesnu mapu</b> </a><br>
</table>\n\n";

############################################
################# KALENDAR #################
############################################
class Calendar {
    /**
     * Constructor
     */
    public function __construct(){
        $this->naviHref = htmlentities($_SERVER['PHP_SELF']);
    }
    /********************* PROPERTY ********************/
    public $dayLabels = array("Pon","Uto","Str","Štv","Pia","Sob","Ned");
    public $currentYear=0;
    public $currentMonth=0;
    public $currentDay=0;
    public $currentDate=null;
    public $daysInMonth=0;
    public $naviHref= null;

    /********************* PUBLIC **********************/
    /**
    * print out the calendar
    */
    public function show() {
        $year  = null;
        $month = null;
        $day = null;
        if(null==$year&&isset($_GET['year'])){
            $year = $_GET['year'];
        }else if(null==$year){
            $year = date("Y",time());
        }

        if(null==$month&&isset($_GET['month'])){
            $month = $_GET['month'];
        }else if(null==$month){
            $month = date("m",time());
        }

        if(null==$day&&isset($_GET['day'])){
            $day = $_GET['day'];
        }else if(null==$day){
            $day = date("d",time());
        }

        $this->currentYear=$year;
        $this->currentMonth=$month;
        $this->daysInMonth=$this->_daysInMonth($month,$year);
        $content='<div id="calendar">'.
                        '<div class="box">'.
                        $this->_createNavi().
                        '</div>'.
                        '<div class="box-content">'.
                                '<ul class="label">'.$this->_createLabels().'</ul>';
                                $content.='<div class="clear"></div>';
                                $content.='<ul class="dates">';

                                $weeksInMonth = $this->_weeksInMonth($month,$year);
                                // Create weeks in a month
                                for( $i=0; $i<$weeksInMonth; $i++ ){
                                    //Create days in a week
                                    for($j=1;$j<=7;$j++){
                                        $content.=$this->_showDay($i*7+$j);
                                    }
                                }
                                $content.='</ul>';
                                $content.='<div class="clear"></div>';
                        $content.='</div>';
        $content.='</div>';
        return $content;
    }
    /********************* PRIVATE **********************/
    /**
    * create the li element for ul
    */
    public function _showDay($cellNumber){
        $year  = null;
        $month = null;
        $day = null;
        if(null==$year&&isset($_GET['year'])){
            $year = $_GET['year'];
        }else if(null==$year){
            $year = date("Y",time());
        }

        if(null==$month&&isset($_GET['month'])){
            $month = $_GET['month'];
        }else if(null==$month){
            $month = date("m",time());
        }


        if(null==$day&&isset($_GET['day'])){
            $day = $_GET['day'];
        }else if(null==$day){
            $day = date("d",time());
        }

        $this->selectedDAY=$day;
        if($this->currentDay==0){
            $firstDayOfTheWeek = date('N',strtotime($this->currentYear.'-'.$this->currentMonth.'-01'));
            if(intval($cellNumber) == intval($firstDayOfTheWeek)){
                $this->currentDay=1;
            }
        }
        if( ($this->currentDay!=0)&&($this->currentDay<=$this->daysInMonth) ){
            $this->currentDate = date('Y-m-d',strtotime($this->currentYear.'-'.$this->currentMonth.'-'.($this->currentDay)));
            $cellContent = $this->currentDay;
	    if ($cellContent < 10) {
	         $cellContent = '0'.$cellContent;
	    }

            $this->currentDay++;
        }else{
            $this->currentDate =null;
            $cellContent=null;
        }
	/* Here is list of days */
        $todayday = date('d');
        $todayYmd = date('Ymd');


        if ($cellContent == $todayday) {
         $bgcolor="style=\"background: red!important\"";
        } else {
         $bgcolor="style=\"background: silver!important\"";
        }

        if ($cellContent == $this->selectedDAY) {
         $bgcolor="style=\"background: lightgreen!important\"";
        }

        return '<li '.$bgcolor.'> <a href="?year='.$this->currentYear.'&amp;month='.$this->currentMonth.'&amp;day='.$cellContent.'&amp;devicerpi='.$this->devicerpi.'">'.$cellContent.'</a> </li>
';
    }
    /**
    * create navigation
    */
    public function _createNavi(){
        $devicerpi = $_POST['devicerpi'];
        $this->devicerpi=$devicerpi;
        $nextMonth = $this->currentMonth==12?1:intval($this->currentMonth)+1;
        $nextYear = $this->currentMonth==12?intval($this->currentYear)+1:$this->currentYear;
        $preMonth = $this->currentMonth==1?12:intval($this->currentMonth)-1;
        $preYear = $this->currentMonth==1?intval($this->currentYear)-1:$this->currentYear;
        return
	/* Calendar menu */
            '<div class="header">'.
                '<a class="prev" href="'.$this->naviHref.'?month='.sprintf('%02d',$preMonth).'&amp;year='.$preYear.'&amp;devicerpi='.$this->devicerpi.'"> <<< </a>'.
                '<span class="title"><a href=".">'.date('Y M',strtotime($this->currentYear.'-'.$this->currentMonth.'-1')).' '.date('d').' '.date('H:i').'</a></span>'.
                '<a class="next" href="'.$this->naviHref.'?month='.sprintf("%02d", $nextMonth).'&amp;year='.$nextYear.'&amp;devicerpi='.$this->devicerpi.'"> >>> </a>'.
            '</div>';
    }
    /**
    * create calendar week labels
    */
    public function _createLabels(){
        $content='';
        foreach($this->dayLabels as $index=>$label){
            $content.='<li class="'.($label==6?'end title':'start title').' title">'.$label.'</li>';
        }
        return $content;
    }
    /**
    * calculate number of weeks in a particular month
    */
    public function _weeksInMonth($month=null,$year=null){
        if( null==($year) ) {
            $year =  date("Y",time());
        }
        if(null==($month)) {
            $month = date("m",time());
        }
        // find number of days in this month
        $daysInMonths = $this->_daysInMonth($month,$year);
        $numOfweeks = ($daysInMonths%7==0?0:1) + intval($daysInMonths/7);
        $monthEndingDay= date('N',strtotime($year.'-'.$month.'-'.$daysInMonths));
        $monthStartDay = date('N',strtotime($year.'-'.$month.'-01'));
        if($monthEndingDay<$monthStartDay){
            $numOfweeks++;
        }
        return $numOfweeks;
    }
    /**
    * calculate number of days in a particular month
    */
    public function _daysInMonth($month=null,$year=null){
        if(null==($year))
            $year =  date("Y",time());
        if(null==($month))
            $month = date("m",time());
        return date('t',strtotime($year.'-'.$month.'-01'));
    }
}
$calendar = new Calendar();
echo $calendar->show();
############################################
################# KALENDAR #################
############################################

 $WEB_HEADER="
<table align=\"center\" border=\"1\" cellpadding=\"0\" cellspacing=\"0\">
 <tr>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>ID</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Súradnice</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Nadm. výška</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Rýchlosť</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Smer</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Satelity</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Čas</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Miesto</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>ŠPZ</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>GPS</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Network</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Signal</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>Operator</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>CellID</b></font></td>
 </tr>

 <tr>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\">><font color=\"00FAAA\"><b>[Lat / Lon]</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>[m.n.m.]</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>[km/h]</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>[stav]</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"><font color=\"00FAAA\"><b>[Home / Roaming]</b></font></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
  <td bgcolor=\"#000000\" align=\"center\"></td>
 </tr>

";
 $WEB_MIDDLE="";
 $WEB_FOOTER="</table>\n\n";

 $address_cache = array();
 for ($i = 1; $i <= $tracking_list_db_row; $i++) {
  $entries = mysqli_fetch_array ($tracking_list_db, MYSQLI_ASSOC);

  $direction='---';
  if (($entries['direction'] >   '0') and ($entries['direction'] <  '45' )) { $drection='S';}
  if (($entries['direction'] >  '46') and ($entries['direction'] < '125' )) { $direction='V';}
  if (($entries['direction'] > '126') and ($entries['direction'] < '225' )) { $direction='J';}
  if (($entries['direction'] > '226') and ($entries['direction'] < '275' )) { $direction='Z';}
  if (($entries['direction'] > '276') and ($entries['direction'] < '366' )) { $direction='S';}

  $bgmiesto='#ffffff';

############################################
############## GPS TO ADDRESS ##############
############################################
  $GET_LAT=substr($entries['lat'],0,7);
  $GET_LON=substr($entries['lon'],0,7);
  $key=$GET_LAT.'_'.$GET_LON;
  if (isset($address_cache[$key])) {
   $miesto=$address_cache[$key];
  } else {
   $sql="SELECT miesto FROM $MySQL_table3 WHERE lat LIKE '$GET_LAT%' AND lon LIKE '$GET_LON%' AND status='OK' LIMIT 1";
   $res=mysqli_query($spojenie,$sql);
   if(mysqli_num_rows($res)==1){
    $row=mysqli_fetch_assoc($res);
    $miesto=$row['miesto'];
   } else {
    $miesto="- - -";
    $url="https://api.geoapify.com/v1/geocode/reverse?type=street&format=xml&lat=".$entries['lat']."&lon=".$entries['lon']."&apiKey=".$GAPIKEY;
    file_put_contents(
     "get_url.txt",
     $url."\n",
     FILE_APPEND
    );
   }
   $address_cache[$key]=$miesto;
  }
############################################
############## GPS TO ADDRESS ##############
############################################

  $SPD=substr($entries['spd'],0,2);
  if ($SPD < '3') {$SPD='0';}

  $lat_last=$entries['lat'];
  $lon_last=$entries['lon'];

  $SPZ=$entries['device'];
  switch ($devicerpi) {
   case "e661385283997828":
    $SPZ="BMW_E46";
    break;

   case "bd6718189a7ba68a":
    $SPZ='BMW_E90';
    break;
  }


  $network=$entries['creg'];
  switch ($network) {
   case "0":
    $network="GSM Not Registered";
    break;


   case "1":
    $network="Home";
    break;

   case "5":
    $network='Roaming';
    break;
  }


  $gps_valid=$entries['gps_valid'];
  switch ($gps_valid) {
   case "0":
    $gps_valid="no GPS";
    break;

   case "1":
    $gps_valid='OK';
    break;
  }


  if (($entries['csq'] > '0')  and ($entries['csq'] <  '10' )) { $csq='Veľmi slabý signál';}
  if (($entries['csq'] > '90') and ($entries['csq'] <  '15' )) { $csq='Slabší signál';}
  if (($entries['csq'] > '14') and ($entries['csq'] <  '20' )) { $csq='Dobrý signál';}
  if (($entries['csq'] > '19') and ($entries['csq'] <  '26' )) { $csq='Veľmi dobrý signál';}
  if (($entries['csq'] > '25') and ($entries['csq'] <  '35' )) { $csq='Výborný signál';}
  if (($entries['csq'] == '0') or ($entries['csq'] == '99')) { $csq='Neznáma hodnota';}

if ($entries['lat'] == '0.000000' ){
 $POS=round($entries['lat'],4).' / '.round($entries['lon'],4);
} else {
 $POS='<a href="osm.php?id='.$entries['id'].'&amp;lat='.$entries['lat'].'&amp;lon='.$entries['lon'].'&amp;zoom=18" target="_blank" style="text-decoration:none">'.round($entries['lat'],4).' / '.round($entries['lon'],4).'</a>';
}

  $WEB_MIDDLE=$WEB_MIDDLE.' <tr>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$i.'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$POS.'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.round($entries['alt'],3).'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.round($SPD,2).'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$direction.'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$entries['sat'].'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.(new DateTime($entries['time'], new DateTimeZone('UTC')))->setTimezone(new DateTimeZone('Europe/Bratislava'))->format('Y-m-d H:i:s').'</td>
  <td bgcolor="'.$bgmiesto.'" align="left">'.$miesto.'</td>
  <td bgcolor="'.$bgmiesto.'" align="left">'.$SPZ.'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$gps_valid.'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$network.'&nbsp;&nbsp;</td>
  <td bgcolor="'.$bgmiesto.'" align="left">'.$entries['csq'].'-'.$csq.'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$entries['mcc'].$entries['mnc'].'</td>
  <td bgcolor="'.$bgmiesto.'" align="center">'.$entries['cellid'].'</td>
 </tr>
'; 

 }
 echo $WEB_HEADER.$WEB_MIDDLE.$WEB_FOOTER;
 echo '<p align="center">
<a href="http://validator.w3.org/check?uri=referer" target="_blank">
 <img src="http://www.w3.org/Icons/valid-html401" alt="Valid HTML 4.01 Transitional" height="31" width="88" border="0">
</a> <br>
';

 $mtime = explode(' ', microtime());
 $totaltime = $mtime[0] + $mtime[1] - $starttime;
 printf ('<font color="000DDA"> Stránka vygenerovaná za %.3f sekundy. </font>', $totaltime);

mysqli_close($spojenie);
?>

</body>
</html>
