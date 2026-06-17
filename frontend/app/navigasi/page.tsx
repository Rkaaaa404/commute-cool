'use client';

import { useState, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import SearchPanel from '@/components/SearchPanel';
import RoutePanel from '@/components/RoutePanel';
import CCTVModal from '@/components/CCTVModal';
import type { Coordinate, RouteResponse, HeatTolerance, CCTVCamera } from '@/types';
import { fetchRoute } from '@/services/api';
import { notifications } from '@mantine/notifications';
import { MapViewRef } from '@/components/MapView';

// Dynamic import for MapView to disable SSR
const MapView = dynamic(() => import('@/components/MapView'), { ssr: false });

export default function NavigationPage() {
  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [routeData, setRouteData] = useState<RouteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [tolerance, setTolerance] = useState<HeatTolerance>('medium');
  const [cctvModal, setCctvModal] = useState<CCTVCamera | null>(null);
  const [clickMode, setClickMode] = useState<'origin' | 'destination'>('origin');
  const [selectedRouteType, setSelectedRouteType] = useState<string | null>(null);

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
    // Fly to the new location when user uses GPS or Autocomplete
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
      if (data.routes && data.routes.length > 0) {
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
      <MapView
        ref={mapRef}
        origin={origin}
        destination={destination}
        routeData={routeData}
        selectedRouteType={selectedRouteType}
        onMapClick={handleMapClick}
        onCCTVClick={setCctvModal}
        clickMode={clickMode}
      />
      
      {/* Banner mode indikator */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: '50%',
        transform: 'translateX(-50%)',
        background: clickMode === 'origin' ? '#1a936f' : '#e63946',
        color: 'white',
        padding: '4px 16px',
        borderBottomLeftRadius: '8px',
        borderBottomRightRadius: '8px',
        fontSize: '12px',
        fontWeight: 'bold',
        zIndex: 40,
        boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
      }}>
        {clickMode === 'origin' ? '📍 Mode Pilih Titik Awal' : '🎯 Mode Pilih Tujuan'}
      </div>

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
      {routeData && (
        <RoutePanel
          routeData={routeData}
          selectedRouteType={selectedRouteType}
          onSelectRoute={setSelectedRouteType}
          onClose={() => setRouteData(null)}
          onCCTVClick={setCctvModal}
        />
      )}
      <CCTVModal
        camera={cctvModal}
        onClose={() => setCctvModal(null)}
      />
    </div>
  );
}
