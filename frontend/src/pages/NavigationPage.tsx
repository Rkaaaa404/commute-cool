import { useState, useCallback } from 'react';
import MapView from '../components/MapView';
import SearchPanel from '../components/SearchPanel';
import RoutePanel from '../components/RoutePanel';
import CCTVModal from '../components/CCTVModal';
import type { Coordinate, RouteResponse, HeatTolerance, CCTVCamera } from '../types';
import { fetchRoute } from '../services/api';
import { notifications } from '@mantine/notifications';

export default function NavigationPage() {
  const [origin, setOrigin] = useState<Coordinate | null>(null);
  const [destination, setDestination] = useState<Coordinate | null>(null);
  const [routeData, setRouteData] = useState<RouteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [tolerance, setTolerance] = useState<HeatTolerance>('medium');
  const [cctvModal, setCctvModal] = useState<CCTVCamera | null>(null);
  const [clickMode, setClickMode] = useState<'origin' | 'destination'>('origin');

  const handleMapClick = useCallback((coord: Coordinate) => {
    if (clickMode === 'origin') {
      setOrigin(coord);
      setClickMode('destination');
    } else {
      setDestination(coord);
      setClickMode('origin');
    }
  }, [clickMode]);

  const handleSearch = useCallback(async () => {
    if (!origin || !destination) return;
    setLoading(true);
    try {
      const data = await fetchRoute(origin, destination, tolerance);
      setRouteData(data);
    } catch (err) {
      notifications.show({
        title: 'Error',
        message: 'Gagal menghitung rute. Pastikan backend berjalan.',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  }, [origin, destination, tolerance]);

  const handleClearRoute = useCallback(() => {
    setRouteData(null);
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <MapView
        origin={origin}
        destination={destination}
        routeData={routeData}
        onMapClick={handleMapClick}
      />
      <SearchPanel
        origin={origin}
        destination={destination}
        tolerance={tolerance}
        onToleranceChange={setTolerance}
        onSearch={handleSearch}
        loading={loading}
      />
      {routeData && (
        <RoutePanel
          routeData={routeData}
          onClose={handleClearRoute}
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
