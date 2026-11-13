<?php
declare(strict_types=1);
?><!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <title>GPS Live Tracking</title>
    <link rel="stylesheet" href="leaflet.css">
    <script src="leaflet.js"></script>
    <style>
        * { box-sizing: border-box; }
        html, body { height: 100%; margin: 0; font-family: Arial, sans-serif; color: #172033; }
        body { overflow: hidden; background: #eef2f6; }
        #map { position: absolute; inset: 0; z-index: 1; background: #dce5e9; }
        .panel {
            position: absolute; z-index: 500; top: 14px; left: 14px;
            width: min(370px, calc(100vw - 28px)); padding: 14px;
            background: rgba(255,255,255,.96); border: 1px solid rgba(15,23,42,.12);
            border-radius: 12px; box-shadow: 0 4px 22px rgba(15,23,42,.18);
            backdrop-filter: blur(8px);
        }
        .topline { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
        h1 { font-size: 17px; margin: 0; }
        .status { font-size: 12px; font-weight: 700; padding: 5px 9px; border-radius: 20px; background: #e5e7eb; color: #374151; }
        .status.online { background: #dcfce7; color: #166534; }
        .status.offline { background: #fee2e2; color: #991b1b; }
        .vehicle-select { width: 100%; margin-top: 12px; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font-size: 14px; }
        .speed-row { display: flex; align-items: baseline; gap: 7px; margin: 13px 0 10px; }
        .speed { font-size: 36px; line-height: 1; font-weight: 700; color: #0f766e; font-variant-numeric: tabular-nums; }
        .unit { color: #64748b; font-size: 13px; }
        .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 14px; border-top: 1px solid #e2e8f0; padding-top: 10px; }
        .stat-label { display: block; color: #64748b; font-size: 11px; margin-bottom: 3px; }
        .stat-value { font-size: 13px; font-weight: 600; overflow-wrap: anywhere; }
        .actions { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; }
        button { border: 0; border-radius: 7px; padding: 8px 11px; background: #1d4ed8; color: white; font-weight: 600; cursor: pointer; }
        button.secondary { background: #e2e8f0; color: #1e293b; }
        .hint { color: #64748b; font-size: 11px; }
        .error { color: #b91c1c; font-size: 12px; margin-top: 8px; min-height: 14px; }
        .car-marker { background: transparent; border: 0; }
        .car-marker svg { display: block; filter: drop-shadow(0 2px 2px rgba(0,0,0,.45)); transform-origin: 50% 50%; }
        @media (max-width: 600px) {
            .panel { top: 8px; left: 8px; width: min(340px, calc(100vw - 16px)); padding: 11px; }
            .speed { font-size: 31px; }
        }
    </style>
</head>
<body>
<div id="map"></div>

<section class="panel" aria-label="GPS live ovládanie">
    <div class="topline">
        <h1>GPS Live Tracking</h1>
        <span id="status" class="status">Načítavam…</span>
    </div>
    <select id="vehicle" class="vehicle-select" aria-label="Vyber vozidlo">
        <option value="">Načítavam vozidlá…</option>
    </select>
    <div class="speed-row">
        <span id="speed" class="speed">—</span>
        <span class="unit">km/h</span>
    </div>
    <div class="stats">
        <div><span class="stat-label">Posledná aktualizácia</span><span id="updated" class="stat-value">—</span></div>
        <div><span class="stat-label">GPS stav</span><span id="gps" class="stat-value">—</span></div>
        <div><span class="stat-label">Satelity</span><span id="satellites" class="stat-value">—</span></div>
        <div><span class="stat-label">Smer</span><span id="direction" class="stat-value">—</span></div>
    </div>
    <div class="actions">
        <button id="follow" type="button">Sledovať vozidlo</button>
        <span class="hint">Obnova každých 5 sekúnd</span>
    </div>
    <div id="error" class="error" role="status"></div>
</section>

<script>
(function () {
    'use strict';

    const API = 'live_api.php';
    const POLL_MS = 5000;
    const ROUTE_REFRESH_MS = 60000;
    const map = L.map('map', { zoomControl: true }).setView([48.7, 20.1], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    const vehicleSelect = document.getElementById('vehicle');
    const statusEl = document.getElementById('status');
    const speedEl = document.getElementById('speed');
    const updatedEl = document.getElementById('updated');
    const gpsEl = document.getElementById('gps');
    const satellitesEl = document.getElementById('satellites');
    const directionEl = document.getElementById('direction');
    const errorEl = document.getElementById('error');
    const followButton = document.getElementById('follow');

    let marker = null;
    let trail = null;
    let pollTimer = null;
    let routePollTimer = null;
    let polling = false;
    let routeLoading = false;
    let follow = true;
    let firstPosition = true;
    let animationFrame = null;
    let selectedDevice = '';

    function setStatus(label, state) {
        statusEl.textContent = label;
        statusEl.className = 'status ' + (state || '');
    }

    function carIcon(direction, online) {
        const color = online ? '#16a34a' : '#64748b';
        const html = '<svg viewBox="0 0 40 40" width="40" height="40" style="transform:rotate(' +
            Number(direction || 0) + 'deg)">' +
            '<path d="M12 5 Q12 2 16 2 H24 Q28 2 28 5 L32 14 L32 31 Q32 35 28 35 H12 Q8 35 8 31 V14 Z" fill="' +
            color + '" stroke="#ffffff" stroke-width="2"/>' +
            '<path d="M13 9 H27 L30 17 H10 Z" fill="#dbeafe" stroke="#ffffff" stroke-width="1"/>' +
            '<path d="M11 24 H29 V31 H11 Z" fill="#0f172a" opacity=".22"/>' +
            '<circle cx="12" cy="11" r="2" fill="#fef3c7"/><circle cx="28" cy="11" r="2" fill="#fef3c7"/>' +
            '<circle cx="12" cy="30" r="2" fill="#1f2937"/><circle cx="28" cy="30" r="2" fill="#1f2937"/>' +
            '</svg>';
        return L.divIcon({ className: 'car-marker', html: html, iconSize: [40, 40], iconAnchor: [20, 20] });
    }

    function animateMarker(target, duration) {
        if (!marker) {
            marker = L.marker(target, { icon: carIcon(0, true), zIndexOffset: 1000 }).addTo(map);
            return;
        }
        if (animationFrame !== null) {
            cancelAnimationFrame(animationFrame);
            animationFrame = null;
        }
        const start = marker.getLatLng();
        const startedAt = performance.now();
        function frame(now) {
            const progress = Math.min(1, (now - startedAt) / duration);
            const eased = progress * (2 - progress);
            marker.setLatLng([
                start.lat + (target.lat - start.lat) * eased,
                start.lng + (target.lng - start.lng) * eased
            ]);
            if (progress < 1) {
                animationFrame = requestAnimationFrame(frame);
            } else {
                animationFrame = null;
            }
        }
        animationFrame = requestAnimationFrame(frame);
    }

    function formatUpdate(isoTime) {
        if (!isoTime) return 'Neznámy čas';
        const date = new Date(isoTime);
        return Number.isNaN(date.getTime()) ? 'Neznámy čas' :
            date.toLocaleTimeString('sk-SK', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    async function fetchJson(url) {
        const response = await fetch(url, { cache: 'no-store', headers: { 'Accept': 'application/json' } });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Chyba servera');
        return data;
    }

    async function loadVehicles() {
        const data = await fetchJson(API + '?action=devices');
        vehicleSelect.innerHTML = '';
        if (!data.devices.length) {
            vehicleSelect.add(new Option('Žiadne registrované vozidlá', ''));
            return;
        }
        data.devices.forEach(function (device) {
            vehicleSelect.add(new Option(device.name + ' — ' + device.id, device.id));
        });

        const requested = new URLSearchParams(window.location.search).get('device');
        const match = data.devices.find(d => d.id === requested);
        vehicleSelect.value = match ? match.id : data.devices[0].id;
        selectedDevice = vehicleSelect.value;
        await updatePosition();
        fetchRoute();
        startPolling();
    }

    async function updatePosition() {
        if (!selectedDevice || polling) return;
        polling = true;
        try {
            const data = await fetchJson(API + '?action=position&device=' + encodeURIComponent(selectedDevice));
            errorEl.textContent = '';
            const pos = data.position;

            if (data.online) {
                setStatus('ONLINE', 'online');
            } else {
                setStatus('OFFLINE', 'offline');
            }

            updatedEl.textContent = data.last_seen
                ? formatUpdate(data.last_seen) + (data.age_seconds !== null ? ' (' + data.age_seconds + ' s)' : '')
                : 'Bez údajov';

            if (pos) {
                speedEl.textContent = Math.round(pos.speed);
                gpsEl.textContent = data.gps_valid ? 'Platný fix' : 'Posledný známy fix';
                satellitesEl.textContent = pos.satellites;
                directionEl.textContent = Math.round(pos.direction) + '°';
                const target = L.latLng(pos.lat, pos.lon);

                if (!marker) {
                    marker = L.marker(target, {
                        icon: carIcon(pos.direction, data.online),
                        zIndexOffset: 1000
                    }).addTo(map);
                    marker.bindPopup('');
                    if (firstPosition) {
                        map.setView(target, 15);
                        firstPosition = false;
                    }
                } else {
                    marker.setIcon(carIcon(pos.direction, data.online));
                    animateMarker(target, POLL_MS - 150);
                }

                marker.setPopupContent(
                    '<b>' + String(data.device.name).replace(/[&<>"]/g, '') + '</b><br>' +
                    Math.round(pos.speed) + ' km/h<br>' + formatUpdate(pos.time)
                );

                if (follow) {
                    map.panTo(target, { animate: true, duration: 1.2 });
                }
            } else {
                speedEl.textContent = '—';
                gpsEl.textContent = 'Bez GPS polohy';
                satellitesEl.textContent = '—';
                directionEl.textContent = '—';
            }

        } catch (error) {
            errorEl.textContent = error.message || 'Nepodarilo sa načítať GPS údaje';
        } finally {
            polling = false;
        }
    }

    async function fetchRoute() {
        if (!selectedDevice || routeLoading) return;
        const requestedDevice = selectedDevice;
        routeLoading = true;
        try {
            const data = await fetchJson(API + '?action=route&device=' + encodeURIComponent(requestedDevice));
            // Ignore a late response if the user switched to another vehicle meanwhile.
            if (requestedDevice !== selectedDevice) return;
            if (Array.isArray(data.route) && data.route.length > 1) {
                if (!trail) {
                    trail = L.polyline(data.route, {
                        color: '#2563eb',
                        weight: 5,
                        opacity: 0.78,
                        lineCap: 'round',
                        lineJoin: 'round'
                    }).addTo(map);
                } else {
                    trail.setLatLngs(data.route);
                }
            } else if (trail) {
                trail.setLatLngs(data.route || []);
            }
        } catch (error) {
            // The live position remains usable even if historical data cannot be loaded.
            errorEl.textContent = 'Polohu máme, história sa nenačítala: ' + (error.message || 'chyba servera');
        } finally {
            routeLoading = false;
        }
    }

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        if (routePollTimer) clearInterval(routePollTimer);
        pollTimer = setInterval(updatePosition, POLL_MS);
        routePollTimer = setInterval(fetchRoute, ROUTE_REFRESH_MS);
    }

    vehicleSelect.addEventListener('change', function () {
        selectedDevice = vehicleSelect.value;
        if (marker) { map.removeLayer(marker); marker = null; }
        if (trail) { map.removeLayer(trail); trail = null; }
        firstPosition = true;
        speedEl.textContent = '—';
        errorEl.textContent = '';
        updatePosition();
        fetchRoute();
    });

    followButton.addEventListener('click', function () {
        follow = !follow;
        followButton.textContent = follow ? 'Sledovať vozidlo' : 'Sledovanie vypnuté';
        followButton.classList.toggle('secondary', !follow);
        if (follow && marker) map.panTo(marker.getLatLng());
    });

    loadVehicles().catch(function (error) {
        setStatus('CHYBA', 'offline');
        errorEl.textContent = error.message || 'Nepodarilo sa načítať vozidlá';
    });
})();
</script>
</body>
</html>
