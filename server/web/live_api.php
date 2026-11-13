<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');

date_default_timezone_set('UTC');

function live_json_response(array $data, int $status = 200): void {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function live_parse_utc(?string $value): ?DateTimeImmutable {
    if (!$value) {
        return null;
    }
    try {
        return new DateTimeImmutable($value, new DateTimeZone('UTC'));
    } catch (Exception $e) {
        return null;
    }
}

function live_number($value, float $default = 0.0): float {
    return is_numeric($value) ? (float)$value : $default;
}

@include __DIR__ . '/_config.php';

if (!isset($spojenie) || !($spojenie instanceof mysqli) || $spojenie->connect_errno) {
    live_json_response(['ok' => false, 'error' => 'Database connection unavailable'], 503);
}

if (!isset($MySQL_table1, $MySQL_table2)
    || !preg_match('/^[A-Za-z0-9_]+$/', $MySQL_table1)
    || !preg_match('/^[A-Za-z0-9_]+$/', $MySQL_table2)) {
    live_json_response(['ok' => false, 'error' => 'GPS table configuration is invalid'], 500);
}

$action = $_GET['action'] ?? 'position';

if ($action === 'devices') {
    $result = $spojenie->query("SELECT devicerpi, name FROM gps_devices ORDER BY name, devicerpi");
    if (!$result) {
        live_json_response(['ok' => false, 'error' => 'Unable to load GPS devices'], 500);
    }

    $devices = [];
    while ($row = $result->fetch_assoc()) {
        $devices[] = [
            'id' => (string)$row['devicerpi'],
            'name' => (string)$row['name']
        ];
    }
    live_json_response(['ok' => true, 'devices' => $devices]);
}

$deviceId = trim((string)($_GET['device'] ?? ''));
if ($deviceId === '' || strlen($deviceId) > 16) {
    live_json_response(['ok' => false, 'error' => 'Missing or invalid device ID'], 400);
}

// Only registered devices can be queried through this endpoint.
$deviceStmt = $spojenie->prepare(
    "SELECT name FROM gps_devices WHERE devicerpi = ? LIMIT 1"
);
if (!$deviceStmt) {
    live_json_response(['ok' => false, 'error' => 'Unable to prepare device lookup'], 500);
}
$deviceStmt->bind_param('s', $deviceId);
$deviceStmt->execute();
$deviceResult = $deviceStmt->get_result();
$device = $deviceResult ? $deviceResult->fetch_assoc() : null;
$deviceStmt->close();

if (!$device) {
    live_json_response(['ok' => false, 'error' => 'Unknown GPS device'], 404);
}

$table = $MySQL_table1;
$archiveTable = $MySQL_table2;

// Latest received record: used to determine whether the tracker is online.
$latestStmt = $spojenie->prepare(
    "SELECT lat, lon, alt, spd, sat, time, direction, gps_valid, creg, csq
     FROM {$table}
     WHERE devicerpi = ?
     ORDER BY time DESC, id DESC
     LIMIT 1"
);
if (!$latestStmt) {
    live_json_response(['ok' => false, 'error' => 'Unable to prepare latest-position query'], 500);
}
$latestStmt->bind_param('s', $deviceId);
$latestStmt->execute();
$latestResult = $latestStmt->get_result();
$latest = $latestResult ? $latestResult->fetch_assoc() : null;
$latestStmt->close();

// After monthly archiving the live table can be empty; retain the last known
// position by falling back to the archive table.
if (!$latest) {
    $archiveLatestStmt = $spojenie->prepare(
        "SELECT lat, lon, alt, spd, sat, time, direction, gps_valid, creg, csq
         FROM {$archiveTable}
         WHERE devicerpi = ?
         ORDER BY time DESC, id DESC
         LIMIT 1"
    );
    if (!$archiveLatestStmt) {
        live_json_response(['ok' => false, 'error' => 'Unable to prepare archive lookup'], 500);
    }
    $archiveLatestStmt->bind_param('s', $deviceId);
    $archiveLatestStmt->execute();
    $archiveLatestResult = $archiveLatestStmt->get_result();
    $latest = $archiveLatestResult ? $archiveLatestResult->fetch_assoc() : null;
    $archiveLatestStmt->close();
}

if (!$latest) {
    live_json_response([
        'ok' => true,
        'device' => ['id' => $deviceId, 'name' => (string)$device['name']],
        'online' => false,
        'gps_valid' => false,
        'last_seen' => null,
        'age_seconds' => null,
        'position' => null,
        'route' => []
    ]);
}

$lastSeen = live_parse_utc((string)$latest['time']);
$ageSeconds = $lastSeen
    ? max(0, time() - $lastSeen->getTimestamp())
    : null;
$isOnline = $ageSeconds !== null && $ageSeconds <= 30;

// Use the newest valid GPS fix for the marker, even if the most recent
// modem report temporarily has no GPS fix.
$positionStmt = $spojenie->prepare(
    "SELECT lat, lon, alt, spd, sat, time, direction
     FROM {$table}
     WHERE devicerpi = ?
       AND gps_valid = 1
       AND lat <> '' AND lon <> ''
       AND lat <> '0' AND lon <> '0'
     ORDER BY time DESC, id DESC
     LIMIT 1"
);
if (!$positionStmt) {
    live_json_response(['ok' => false, 'error' => 'Unable to prepare GPS-fix query'], 500);
}
$positionStmt->bind_param('s', $deviceId);
$positionStmt->execute();
$positionResult = $positionStmt->get_result();
$positionRow = $positionResult ? $positionResult->fetch_assoc() : null;
$positionStmt->close();

if (!$positionRow) {
    $archivePositionStmt = $spojenie->prepare(
        "SELECT lat, lon, alt, spd, sat, time, direction
         FROM {$archiveTable}
         WHERE devicerpi = ?
           AND gps_valid = 1
           AND lat <> '' AND lon <> ''
           AND lat <> '0' AND lon <> '0'
         ORDER BY time DESC, id DESC
         LIMIT 1"
    );
    if (!$archivePositionStmt) {
        live_json_response(['ok' => false, 'error' => 'Unable to prepare archive GPS-fix query'], 500);
    }
    $archivePositionStmt->bind_param('s', $deviceId);
    $archivePositionStmt->execute();
    $archivePositionResult = $archivePositionStmt->get_result();
    $positionRow = $archivePositionResult ? $archivePositionResult->fetch_assoc() : null;
    $archivePositionStmt->close();
}

$position = null;
if ($positionRow) {
    $lat = live_number($positionRow['lat'], 999.0);
    $lon = live_number($positionRow['lon'], 999.0);
    if ($lat >= -90 && $lat <= 90 && $lon >= -180 && $lon <= 180) {
        $positionTime = live_parse_utc((string)$positionRow['time']);
        $position = [
            'lat' => $lat,
            'lon' => $lon,
            'alt' => live_number($positionRow['alt']),
            'speed' => live_number($positionRow['spd']),
            'satellites' => (int)$positionRow['sat'],
            'direction' => live_number($positionRow['direction']),
            'time' => $positionTime ? $positionTime->format(DateTimeInterface::ATOM) : null
        ];
    }
}

// Keep a rolling 30-minute trail. The two time formats are handled separately:
// current records use ISO UTC (T), older records may use a SQL-style space.
$cutoff = time() - 1800;
$cutoffIso = gmdate('Y-m-d\\TH:i:s', $cutoff);
$cutoffSql = gmdate('Y-m-d H:i:s', $cutoff);
$routeStmt = $spojenie->prepare(
    "SELECT lat, lon, time FROM (
         SELECT lat, lon, time, id
         FROM {$table}
         WHERE devicerpi = ?
           AND gps_valid = 1
           AND lat <> '' AND lon <> ''
           AND lat <> '0' AND lon <> '0'
           AND (
               (time LIKE '____-__-__T%' AND time >= ?)
               OR
               (time NOT LIKE '____-__-__T%' AND time >= ?)
           )
         UNION ALL
         SELECT lat, lon, time, id
         FROM {$archiveTable}
         WHERE devicerpi = ?
           AND gps_valid = 1
           AND lat <> '' AND lon <> ''
           AND lat <> '0' AND lon <> '0'
           AND (
               (time LIKE '____-__-__T%' AND time >= ?)
               OR
               (time NOT LIKE '____-__-__T%' AND time >= ?)
           )
     ) AS recent_points
     ORDER BY time ASC, id ASC
     LIMIT 600"
);
if (!$routeStmt) {
    live_json_response(['ok' => false, 'error' => 'Unable to prepare route query'], 500);
}
$routeStmt->bind_param('ssssss', $deviceId, $cutoffIso, $cutoffSql, $deviceId, $cutoffIso, $cutoffSql);
$routeStmt->execute();
$routeResult = $routeStmt->get_result();

$route = [];
if ($routeResult) {
    while ($row = $routeResult->fetch_assoc()) {
        $lat = live_number($row['lat'], 999.0);
        $lon = live_number($row['lon'], 999.0);
        if ($lat < -90 || $lat > 90 || $lon < -180 || $lon > 180) {
            continue;
        }
        $route[] = [$lat, $lon];
    }
}
$routeStmt->close();
$spojenie->close();

live_json_response([
    'ok' => true,
    'device' => ['id' => $deviceId, 'name' => (string)$device['name']],
    'online' => $isOnline,
    'gps_valid' => (bool)$latest['gps_valid'],
    'last_seen' => $lastSeen ? $lastSeen->format(DateTimeInterface::ATOM) : null,
    'age_seconds' => $ageSeconds,
    'network' => (int)$latest['creg'],
    'signal' => (int)$latest['csq'],
    'position' => $position,
    'route' => $route
]);
