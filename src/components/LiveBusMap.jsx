import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useSocket } from '../context/SocketContext';

// Custom icons using standard fast CDNs
// SVG icon components for Leaflet
const createSvgIcon = (color, svgContent) => {
  return new L.DivIcon({
    html: `<div style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="${color}" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
              ${svgContent}
            </svg>
           </div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40]
  });
};

const busSvgStoke = '<path d="M18 11V7c0-1.1-.9-2-2-2H8c-1.1 0-2 .9-2 2v4c-1.66 0-3 1.34-3 3v3h2v2h2v-2h8v2h2v-2h2v-3c0-1.66-1.34-3-3-3zm-6-4h4v3h-4V7zM8 7h2v3H8V7zm3 10c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm5 0c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z"/>';
const pinSvg = '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>';

const busIcon = createSvgIcon('#3b82f6', busSvgStoke); // Blue bus
const dispatchedBusIcon = createSvgIcon('#10b981', busSvgStoke); // Green bus (pulse via CSS)
const stopIcon = createSvgIcon('#f43f5e', pinSvg); // Rose pin for bus stop
const meIcon = createSvgIcon('#3b82f6', pinSvg); // Blue pin for "Me"

function MapUpdater({ center, userCoords }) {
  const map = useMap();
  useEffect(() => {
    // Priority 1: Center on the specific selected stop
    if (center && center.lat) {
      map.flyTo([center.lat, center.lng], 15, { duration: 1.5 });
    } 
    // Priority 2: Center on user's real location when detected
    else if (userCoords && userCoords.lat) {
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
    
    const onLiveBuses = (data) => {
      setBuses(data);
    };
    
    socket.on('live-buses', onLiveBuses);
    return () => socket.off('live-buses', onLiveBuses);
  }, [socket]);

  // Default center point
  let mapCenter = [13.0827, 80.2707];
  if (center?.lat) mapCenter = [center.lat, center.lng];
  else if (userCoords?.lat) mapCenter = [userCoords.lat, userCoords.lng];

  return (
    <div className="h-[400px] w-full rounded-2xl overflow-hidden border-2 border-slate-200 dark:border-slate-800 relative z-0 shadow-inner">
      <MapContainer 
        center={mapCenter} 
        zoom={13} 
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <MapUpdater center={center} userCoords={userCoords} />
        
        {/* User Location Marker (Blue) – only when no stop is selected, so we
            don't stack a second pin on top of the chosen stop. */}
        {userCoords?.lat && !center?.lat && (
          <Marker position={[userCoords.lat, userCoords.lng]} icon={meIcon}>
            <Popup className="font-semibold text-slate-800">You are here</Popup>
          </Marker>
        )}

        {/* Selected Bus Stop Marker (Rose) */}
        {center?.lat && (
          <Marker position={[center.lat, center.lng]} icon={stopIcon}>
            <Popup className="font-semibold text-slate-800">Selected Stop: {center.name}</Popup>
          </Marker>
        )}

        {/* Live Buses */}
        {buses.map(bus => (
          (!isTracking || bus.isDispatched) ? (
            <Marker 
              key={bus.id} 
              position={[bus.lat, bus.lng]} 
              icon={bus.isDispatched ? dispatchedBusIcon : busIcon}
            >
              <Popup>
                <div className="font-bold text-slate-800">{bus.name}</div>
                <div className="text-xs text-slate-500">{bus.isDispatched ? 'Dispatched to you!' : 'On Route'}</div>
              </Popup>
            </Marker>
          ) : null
        ))}
      </MapContainer>
    </div>
  );
}
