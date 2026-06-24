import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useSocket } from '../context/SocketContext';

const createSvgIcon = (color, svgContent) => new L.DivIcon({
  html: `<div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;">
          <svg viewBox="0 0 24 24" width="38" height="38" fill="${color}" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
            ${svgContent}
          </svg>
         </div>`,
  className: '',
  iconSize: [38, 38],
  iconAnchor: [19, 38],
  popupAnchor: [0, -38],
});

const busSvg = '<path d="M18 11V7c0-1.1-.9-2-2-2H8c-1.1 0-2 .9-2 2v4c-1.66 0-3 1.34-3 3v3h2v2h2v-2h8v2h2v-2h2v-3c0-1.66-1.34-3-3-3zm-6-4h4v3h-4V7zM8 7h2v3H8V7zm3 10c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm5 0c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z"/>';
const pinSvg = '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>';

const busIcon = createSvgIcon('#2563eb', busSvg);  // Brand bus (moving)
const stopIcon = createSvgIcon('#f43f5e', pinSvg); // Rose pin for bus stop
const meIcon = createSvgIcon('#2563eb', pinSvg);   // Brand pin for "You"

export function formatEta(sec) {
  if (sec == null) return null;
  if (sec < 60) return `~${sec} sec`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s ? `~${m} min ${s} sec` : `~${m} min`;
}

function MapUpdater({ center, userCoords, buses, isTracking }) {
  const map = useMap();
  // Center on the selected stop / user once.
  useEffect(() => {
    if (center && center.lat) map.flyTo([center.lat, center.lng], 15, { duration: 1.2 });
    else if (userCoords && userCoords.lat) map.flyTo([userCoords.lat, userCoords.lng], 15, { duration: 1.2 });
  }, [center, userCoords, map]);
  // While tracking, keep both the stop and the moving bus in view.
  useEffect(() => {
    if (!isTracking) return;
    const bus = buses.find(b => b.isDispatched);
    if (bus && center?.lat) {
      map.fitBounds([[bus.lat, bus.lng], [center.lat, center.lng]], { padding: [60, 60], maxZoom: 16 });
    }
  }, [buses, isTracking, center, map]);
  return null;
}

export default function LiveBusMap({ center, userCoords, isTracking = false, onEtaChange }) {
  const { socket } = useSocket();
  const [buses, setBuses] = useState([]);

  useEffect(() => {
    if (!socket) return;
    const onLiveBuses = (data) => setBuses(data);
    socket.on('live-buses', onLiveBuses);
    return () => socket.off('live-buses', onLiveBuses);
  }, [socket]);

  const dispatched = buses.filter(b => b.isDispatched);
  const etas = dispatched.map(b => b.etaSeconds).filter(v => v != null);
  const nextEta = etas.length ? Math.min(...etas) : null;

  // Report the current ETA upward (so the page can show it below the map).
  useEffect(() => {
    if (onEtaChange) onEtaChange(isTracking ? nextEta : null);
  }, [nextEta, isTracking, onEtaChange]);

  let mapCenter = [13.0827, 80.2707];
  if (center?.lat) mapCenter = [center.lat, center.lng];
  else if (userCoords?.lat) mapCenter = [userCoords.lat, userCoords.lng];

  return (
    <div className="h-[360px] w-full rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 relative z-0">
      <MapContainer center={mapCenter} zoom={14} style={{ height: '100%', width: '100%' }} zoomControl={false} attributionControl={false}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapUpdater center={center} userCoords={userCoords} buses={buses} isTracking={isTracking} />

        {userCoords?.lat && !center?.lat && (
          <Marker position={[userCoords.lat, userCoords.lng]} icon={meIcon}>
            <Popup className="font-semibold text-slate-800">You are here</Popup>
          </Marker>
        )}

        {center?.lat && (
          <Marker position={[center.lat, center.lng]} icon={stopIcon}>
            <Popup className="font-semibold text-slate-800">Your stop: {center.name}</Popup>
          </Marker>
        )}

        {/* Moving bus(es) heading to the stop — only while tracking. */}
        {isTracking && dispatched.map(bus => (
          <Marker key={bus.id} position={[bus.lat, bus.lng]} icon={busIcon}>
            <Popup>
              <div className="font-semibold text-slate-800">{bus.name}</div>
              <div className="text-xs text-slate-500">
                {formatEta(bus.etaSeconds) ? `Arriving in ${formatEta(bus.etaSeconds)}` : 'On the way'}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
