'use client';

import { useState, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import SearchPanel from '@/components/SearchPanel';
import RoutePanel from '@/components/RoutePanel';
import CCTVModal from '@/components/CCTVModal';
import MapLayerSwitcher from '@/components/MapLayerSwitcher';
import TCSLegend from '@/components/TCSLegend';
import type { Coordinate, RouteResponse, HeatTolerance, CCTVCamera } from '@/types';
import { fetchRoute } from '@/services/api';
import { notifications } from '@mantine/notifications';
import { MapViewRef } from '@/components/MapView';

// Dynamic import for MapView to disable SSR (maplibre uses browser APIs)
const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

// ── Styles ─────────────────────────────────────────────────────────────────

const SIDEBAR_STYLE: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  left: 12,
  width: 340,
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  maxHeight: 'calc(100vh - 24px)',
  pointerEvents: 'none',
};

const CLICK_MODE_BANNER_BASE: React.CSSProperties = {
  position: 'absolute',
  top: 0,
  left: '50%',
  transform: 'translateX(-50%)',
  color: 'white',
  padding: '4px 16px',
  borderBottomLeftRadius: '8px',
  borderBottomRightRadius: '8px',
  fontSize: '12px',
  fontWeight: 'bold',
  zIndex: 40,
  boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
};

const WEATHER_BANNER_STYLE: React.CSSProperties = {
  position: 'absolute',
  top: 48,
  left: '50%',
  transform: 'translateX(-50%)',
  background: '#f59f00',
  color: 'white',
  padding: '6px 20px',
  borderRadius: '8px',
  fontSize: '13px',
  fontWeight: 'bold',
  zIndex: 45,
  boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
  maxWidth: '90%',
  textAlign: 'center',
};

const BOTTOM_CONTROLS_STYLE: React.CSSProperties = {
  position: 'absolute',
  bottom: 24,
  left: 24,
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  pointerEvents: 'auto',
};

// ── Component ───────────────────────────────────────────────────────────────

export default function NavigationPage() {
  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [routeData, setRouteData] = useState<RouteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [tolerance, setTolerance] = useState<HeatTolerance>('medium');
  const [cctvModal, setCctvModal] = useState<CCTVCamera | null>(null);
  const [clickMode, setClickMode] = useState<'origin' | 'destination'>('origin');
  const [selectedRouteType, setSelectedRouteType] = useState<string | null>(null);
  const [showTempHeatmap, setShowTempHeatmap] = useState(false);

  const mapRef = useRef<MapViewRef>(null);

  const handleMapClick = useCallback((coord: Coordinate) => {
    if (clickMode === 'origin') {
      setOrigin(coord);
      setClickMode('destination');
    } else {
      setDestination(coord);
      setClickMode('origin');
    }
  }, [clickMode]);

  const handleLocateGPS = useCallback((coord: Coordinate) => {
    mapRef.current?.flyTo(coord);
  }, []);

  const handleSetOrigin = useCallback((coord: Coordinate) => {
    setOrigin(coord);
    setClickMode('destination');
  }, []);

  const handleSetDestination = useCallback((coord: Coordinate) => {
    setDestination(coord);
    setClickMode('origin');
  }, []);

  const handleSearch = useCallback(async () => {
    if (!origin || !destination) return;
    setLoading(true);
    try {
      const data = await fetchRoute(origin, destination, tolerance);
      setRouteData(data);
      if (data.routes?.length > 0) {
        setSelectedRouteType(data.heat_budget?.recommended_route || data.routes[0].type);
      }
    } catch {
      notifications.show({
        title: 'Error',
        message: 'Gagal menghitung rute. Pastikan backend berjalan.',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  }, [origin, destination, tolerance]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Map (full-screen background) */}
      <MapView
        ref={mapRef}
        origin={origin}
        destination={destination}
        routeData={routeData}
        selectedRouteType={selectedRouteType}
        onMapClick={handleMapClick}
        onCCTVClick={setCctvModal}
        clickMode={clickMode}
        showTempHeatmap={showTempHeatmap}
      />

      {/* Click mode indicator banner */}
      <div
        style={{
          ...CLICK_MODE_BANNER_BASE,
          background: clickMode === 'origin' ? '#1a936f' : '#e63946',
        }}
      >
        {clickMode === 'origin' ? '📍 Mode Pilih Titik Awal' : '🎯 Mode Pilih Tujuan'}
      </div>

      {/* Left sidebar: search + route panel */}
      <div style={SIDEBAR_STYLE}>
        <div style={{ pointerEvents: 'auto' }}>
          <SearchPanel
            origin={origin}
            destination={destination}
            tolerance={tolerance}
            onToleranceChange={setTolerance}
            onSearch={handleSearch}
            onSetOrigin={handleSetOrigin}
            onSetDestination={handleSetDestination}
            loading={loading}
            clickMode={clickMode}
            onLocateGPS={handleLocateGPS}
          />
        </div>
        {routeData && (
          <div style={{ pointerEvents: 'auto', display: 'flex', minHeight: 0 }}>
            <RoutePanel
              routeData={routeData}
              selectedRouteType={selectedRouteType}
              onSelectRoute={(type) => setSelectedRouteType(prev => prev === type ? null : type)}
              onClose={() => setRouteData(null)}
              onCCTVClick={setCctvModal}
            />
          </div>
        )}
      </div>

      {/* CCTV modal */}
      <CCTVModal camera={cctvModal} onClose={() => setCctvModal(null)} />

      {/* Weather warning banner */}
      {routeData?.weather_alert && (
        <div style={WEATHER_BANNER_STYLE}>
          ⚠️ {routeData.weather_alert}
        </div>
      )}

      {/* Bottom-left controls: TCS legend + layer switcher */}
      <div style={BOTTOM_CONTROLS_STYLE}>
        {!showTempHeatmap && <TCSLegend />}
        <MapLayerSwitcher
          value={showTempHeatmap ? 'temp' : 'tcs'}
          onChange={(val) => setShowTempHeatmap(val === 'temp')}
        />
      </div>
    </div>
  );
}
