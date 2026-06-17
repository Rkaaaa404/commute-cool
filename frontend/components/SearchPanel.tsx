'use client';
import { Paper, Autocomplete, Button, Select, Stack, ActionIcon, Group, Text, Loader } from '@mantine/core';
import { IconMapPin, IconTarget, IconCurrentLocation, IconArrowsVertical, IconSun, IconCloud } from '@tabler/icons-react';
import { useState, useCallback, useEffect, useRef } from 'react';
import type { Coordinate, HeatTolerance } from '../types';
import { fetchWeather } from '../services/api';

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
  onLocateGPS: (c: Coordinate) => void;
}

async function geocodeLocation(query: string): Promise<Array<{label: string, lat: number, lng: number}>> {
  if (!query || query.length < 3) return [];
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Surabaya')}&limit=5&countrycodes=id`
    );
    const data = await res.json();
    return data.map((d: any) => ({
      label: d.display_name.split(',')[0] + ', ' + d.display_name.split(',')[1],
      lat: parseFloat(d.lat),
      lng: parseFloat(d.lon)
    }));
  } catch {
    return [];
  }
}

async function reverseGeocode(lat: number, lng: number): Promise<string> {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`);
    const data = await res.json();
    if (data && data.address) {
      return data.address.road || data.address.suburb || data.display_name.split(',')[0];
    }
  } catch { /* ignore */ }
  return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

export default function SearchPanel({
  origin, destination, tolerance, onToleranceChange, onSearch, onSetOrigin, onSetDestination, loading, clickMode, onLocateGPS
}: Props) {
  const [originText, setOriginText] = useState('');
  const [destText, setDestText] = useState('');
  const [originOptions, setOriginOptions] = useState<{label: string, lat: number, lng: number}[]>([]);
  const [destOptions, setDestOptions] = useState<{label: string, lat: number, lng: number}[]>([]);
  const [weather, setWeather] = useState<{temp: number, apparent: number} | null>(null);
  
  const searchTimeoutRef = useRef<NodeJS.Timeout>(null);

  useEffect(() => {
    fetchWeather().then(setWeather);
  }, []);

  // Update text when coords change externally (e.g. map click)
  useEffect(() => {
    if (origin) {
      reverseGeocode(origin.lat, origin.lng).then(name => setOriginText(name));
    } else {
      setOriginText('');
    }
  }, [origin]);

  useEffect(() => {
    if (destination) {
      reverseGeocode(destination.lat, destination.lng).then(name => setDestText(name));
    } else {
      setDestText('');
    }
  }, [destination]);

  const onOriginInput = (val: string) => {
    setOriginText(val);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      const opts = await geocodeLocation(val);
      setOriginOptions(opts);
    }, 500);
  };

  const onDestInput = (val: string) => {
    setDestText(val);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      const opts = await geocodeLocation(val);
      setDestOptions(opts);
    }, 500);
  };

  const handleOriginSelect = (val: string) => {
    const opt = originOptions.find(o => o.label === val);
    if (opt) {
      onSetOrigin({ lat: opt.lat, lng: opt.lng });
      onLocateGPS({ lat: opt.lat, lng: opt.lng });
    }
  };

  const handleDestSelect = (val: string) => {
    const opt = destOptions.find(o => o.label === val);
    if (opt) {
      onSetDestination({ lat: opt.lat, lng: opt.lng });
      onLocateGPS({ lat: opt.lat, lng: opt.lng });
    }
  };

  const handleSwap = () => {
    const tempText = originText;
    setOriginText(destText);
    setDestText(tempText);

    const tempCoord = origin;
    if (destination) onSetOrigin(destination);
    else onSetOrigin(null as any); // Reset to null properly handled upstream usually, but here we just pass
    
    if (tempCoord) onSetDestination(tempCoord);
  };

  const handleGPS = useCallback(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coord = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        // Check if within Surabaya bounds
        if (coord.lat >= -7.35 && coord.lat <= -7.20 && coord.lng >= 112.60 && coord.lng <= 112.85) {
          onSetOrigin(coord);
          onLocateGPS(coord);
        } else {
          // Surabaya center fallback
          const fallback = { lat: -7.2575, lng: 112.7521 };
          onSetOrigin(fallback);
          onLocateGPS(fallback);
        }
      },
      () => {
        const fallback = { lat: -7.2575, lng: 112.7521 };
        onSetOrigin(fallback);
        onLocateGPS(fallback);
      }
    );
  }, [onSetOrigin, onLocateGPS]);

  return (
    <Paper
      shadow="md"
      radius="lg"
      p="md"
      style={{ position: 'absolute', top: 12, left: 12, width: 340, zIndex: 50 }}
    >
      <Stack gap="xs">
        {weather && (
          <Group gap={6} align="center" style={{ backgroundColor: 'var(--mantine-color-gray-0)', padding: '6px 10px', borderRadius: '8px' }}>
            {weather.temp > 30 ? <IconSun size={16} color="var(--mantine-color-yellow-6)" /> : <IconCloud size={16} color="gray" />}
            <Text size="xs" fw={500} c="dimmed">
              Surabaya: {weather.temp}°C (Terasa {weather.apparent}°C)
            </Text>
          </Group>
        )}

        <Group gap={4} align="flex-end">
          <Autocomplete
            label={clickMode === 'origin' ? "📍 Memilih titik awal..." : "Titik Awal"}
            size="sm"
            placeholder="Cari lokasi..."
            data={originOptions.map(o => o.label)}
            value={originText}
            onChange={onOriginInput}
            onOptionSubmit={handleOriginSelect}
            leftSection={<IconMapPin size={14} color={clickMode === 'origin' ? '#1a936f' : '#457b9d'} />}
            style={{ flex: 1 }}
            styles={{ input: { borderColor: clickMode === 'origin' ? '#1a936f' : undefined } }}
          />
          <ActionIcon mb={4} variant="light" color="teal" onClick={handleGPS} title="Gunakan lokasi saya">
            <IconCurrentLocation size={18} />
          </ActionIcon>
        </Group>

        <Group justify="center" gap={0} mt={-10} mb={-10} style={{ position: 'relative', zIndex: 2 }}>
          <ActionIcon radius="xl" variant="default" size="sm" onClick={handleSwap}>
            <IconArrowsVertical size={14} />
          </ActionIcon>
        </Group>

        <Autocomplete
          label={clickMode === 'destination' ? "🎯 Memilih tujuan..." : "Tujuan"}
          size="sm"
          placeholder="Cari lokasi..."
          data={destOptions.map(o => o.label)}
          value={destText}
          onChange={onDestInput}
          onOptionSubmit={handleDestSelect}
          leftSection={<IconTarget size={14} color={clickMode === 'destination' ? '#1a936f' : '#e63946'} />}
          styles={{ input: { borderColor: clickMode === 'destination' ? '#1a936f' : undefined } }}
        />

        <Select
          size="xs"
          label="Toleransi panas kamu hari ini?"
          data={[
            { value: 'low', label: 'Rendah (Sedang santai / Sama anak)' },
            { value: 'medium', label: 'Sedang (Biasa saja)' },
            { value: 'high', label: 'Tinggi (Buru-buru / Olahraga)' },
          ]}
          value={tolerance}
          onChange={(v) => onToleranceChange((v || 'medium') as HeatTolerance)}
        />

        <Button
          fullWidth
          color="teal"
          onClick={onSearch}
          loading={loading}
          disabled={!origin || !destination}
          mt="xs"
        >
          Cari Rute Ternyaman
        </Button>
      </Stack>
    </Paper>
  );
}
