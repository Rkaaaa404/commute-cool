import { Paper, TextInput, Button, Select, Stack, ActionIcon, Group } from '@mantine/core';
import { IconMapPin, IconTarget, IconCurrentLocation } from '@tabler/icons-react';
import { useState, useCallback } from 'react';
import type { Coordinate, HeatTolerance } from '../types';

interface Props {
  origin: Coordinate | null;
  destination: Coordinate | null;
  tolerance: HeatTolerance;
  onToleranceChange: (v: HeatTolerance) => void;
  onSearch: () => void;
  onSetOrigin: (c: Coordinate) => void;
  onSetDestination: (c: Coordinate) => void;
  loading: boolean;
  clickMode: 'origin' | 'destination';
}

// Simple geocoder using Nominatim (free, no key needed)
async function geocodeLocation(query: string): Promise<Coordinate | null> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&viewbox=112.60,-7.20,112.85,-7.35&bounded=1&limit=5&countrycodes=id`
    );
    const data = await res.json();
    if (data.length > 0) {
      return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
    }
    // Retry without bounds (wider search with Surabaya appended)
    const res2 = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Surabaya')}&limit=3&countrycodes=id`
    );
    const data2 = await res2.json();
    if (data2.length > 0) {
      return { lat: parseFloat(data2[0].lat), lng: parseFloat(data2[0].lon) };
    }
  } catch { /* ignore */ }
  return null;
}

function formatCoord(c: Coordinate | null) {
  if (!c) return '';
  return `${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}`;
}

export default function SearchPanel({
  origin, destination, tolerance, onToleranceChange, onSearch, onSetOrigin, onSetDestination, loading, clickMode
}: Props) {
  const [originText, setOriginText] = useState('');
  const [destText, setDestText] = useState('');
  const [geocoding, setGeocoding] = useState(false);

  const handleOriginSearch = useCallback(async () => {
    if (!originText.trim()) return;
    setGeocoding(true);
    const coord = await geocodeLocation(originText);
    if (coord) onSetOrigin(coord);
    setGeocoding(false);
  }, [originText, onSetOrigin]);

  const handleDestSearch = useCallback(async () => {
    if (!destText.trim()) return;
    setGeocoding(true);
    const coord = await geocodeLocation(destText);
    if (coord) onSetDestination(coord);
    setGeocoding(false);
  }, [destText, onSetDestination]);

  const handleGPS = useCallback(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coord = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        // Check if within Surabaya bounds
        if (coord.lat >= -7.35 && coord.lat <= -7.20 && coord.lng >= 112.60 && coord.lng <= 112.85) {
          onSetOrigin(coord);
        } else {
          // Use Surabaya center as fallback
          onSetOrigin({ lat: -7.2575, lng: 112.7521 });
        }
      },
      () => {
        // Fallback to Surabaya center
        onSetOrigin({ lat: -7.2575, lng: 112.7521 });
      }
    );
  }, [onSetOrigin]);

  const originDisplay = origin ? formatCoord(origin) : '';
  const destDisplay = destination ? formatCoord(destination) : '';

  return (
    <Paper
      shadow="md"
      radius="lg"
      p="md"
      style={{ position: 'absolute', top: 12, left: 12, width: 330, zIndex: 50 }}
    >
      <Stack gap="xs">
        <Group gap={4}>
          <TextInput
            size="sm"
            placeholder={clickMode === 'origin' ? 'Klik peta atau ketik lokasi...' : 'Titik awal'}
            value={originText || originDisplay}
            onChange={(e) => setOriginText(e.currentTarget.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleOriginSearch()}
            leftSection={<IconMapPin size={14} color="#457b9d" />}
            style={{ flex: 1 }}
          />
          <ActionIcon variant="light" color="teal" onClick={handleGPS} title="Gunakan lokasi saat ini">
            <IconCurrentLocation size={16} />
          </ActionIcon>
        </Group>

        <TextInput
          size="sm"
          placeholder={clickMode === 'destination' ? 'Klik peta atau ketik tujuan...' : 'Tujuan'}
          value={destText || destDisplay}
          onChange={(e) => setDestText(e.currentTarget.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleDestSearch()}
          leftSection={<IconTarget size={14} color="#e63946" />}
        />

        <Select
          size="xs"
          label="Toleransi panas"
          data={[
            { value: 'low', label: 'Rendah (lansia/anak)' },
            { value: 'medium', label: 'Sedang' },
            { value: 'high', label: 'Tinggi (aktif)' },
          ]}
          value={tolerance}
          onChange={(v) => onToleranceChange((v || 'medium') as HeatTolerance)}
        />

        <Button
          fullWidth
          color="teal"
          onClick={onSearch}
          loading={loading || geocoding}
          disabled={!origin || !destination}
        >
          Cari Rute
        </Button>
      </Stack>
    </Paper>
  );
}
