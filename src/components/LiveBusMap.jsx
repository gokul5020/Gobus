import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useSocket } from '../context/SocketContext';

// Pin icons only — no bus icons are drawn on the map; the bus is represented
// to the user purely by its ETA.
const createSvgIcon = (color, svgContent) => new L.DivIcon({
  html: `<div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;">
          <svg viewBox="0 0 24 24" width="40" height="40" fill="${color}" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
            ${svgContent}
          </svg>
         </div>`,
  className: '',
  iconSize: [40, 40],
  iconAnchor: [20, 40],
  popupAnchor: [0, -40],
});

const pinSvg = '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>';
const stopIcon = createSvgIcon('#f43f5e', pinSvg); // Rose pin for bus stop
const meIcon = createSvgIcon('#2563eb', pinSvg);   // Brand pin for "You"

// Format an ETA (seconds) into a short human label.
function formatEta(sec) {
  if (sec == null) return null;
  if (sec < 60) return `~${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s ? `~${m}m ${s}s` : `~${m} min`;
}

function MapUpdater({ center, userCoords }) {
  const map = useMap();
  useEffect(() => {
    if (center && center.lat) {
      map.flyTo([center.lat, center.lng], 15, { duration: 1.5 });
    } else if (userCoords && userCoords.lat) {
      map.flyTo([userCoords.lat, userCoords.lng], 15, { duration: 1.5 });
    }
  }, [center, userCoords, map]);
  return null;
}

export default function LiveBusMap({ center, userCoords, isTracking = false }) {
  const { socket } = useSocket();
  const [buses, setBuses] = useState([]);

  useEffect(() => {
    if (!socket) return;
    const onLiveBuses = (data) => setBuses(data);
    socket.on('live-buses', onLiveBuses);
    return () => socket.off('live-buses', onLiveBuses);
  }, [socket]);

  // Default center point
  let mapCenter = [13.0827, 80.2707];
  if (center?.lat) mapCenter = [center.lat, center.lng];
  else if (userCoords?.lat) mapCenter = [userCoords.lat, userCoords.lng];

  // ETA of the soonest bus dispatched to the user.
  const dispatched = buses.filter(b => b.isDispatched);
  const withEta = dispatched.filter(b => b.etaSeconds != null);
  const nextEta = withEta.length ? Math.min(...withEta.map(b => b.etaSeconds)) : null;
  const showEta = isTracking && dispatched.length > 0;

  return (
    <div className="h-[400px] w-full rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 relative z-0">
      {showEta && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-2 px-4 py-2 rounded-lg bg-white/95 dark:bg-slate-900/95 border border-slate-200 dark:border-slate-700 shadow-card text-sm">
          <span className="w-2 h-2 rounded-full bg-brand" />
          <span className="font-medium text-slate-700 dark:text-slate-200">
            {nextEta != null ? `Your bus is arriving in ${formatEta(nextEta)}` : 'Locating your bus…'}
          </span>
        </div>
      )}

      <MapContainer
        center={mapCenter}
        zoom={13}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        <MapUpdater center={center} userCoords={userCoords} />

        {/* User Location Marker – only when no stop is selected. */}
        {userCoords?.lat && !center?.lat && (
          <Marker position={[userCoords.lat, userCoords.lng]} icon={meIcon}>
            <Popup className="font-semibold text-slate-800">You are here</Popup>
          </Marker>
        )}

        {/* Selected Bus Stop Marker */}
        {center?.lat && (
          <Marker position={[center.lat, center.lng]} icon={stopIcon}>
            <Popup className="font-semibold text-slate-800">Selected stop: {center.name}</Popup>
          </Marker>
        )}

        {/* No bus markers are rendered — the dispatched bus is shown to the
            user via the ETA banner above, not as an icon on the map. */}
      </MapContainer>
    </div>
  );
}
