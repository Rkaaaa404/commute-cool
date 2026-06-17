import { Paper, TextInput, Button, Select, Stack } from '@mantine/core';
import { IconMapPin, IconTarget } from '@tabler/icons-react';
import type { Coordinate, HeatTolerance } from '../types';

interface Props {
  origin: Coordinate | null;
  destination: Coordinate | null;
  tolerance: HeatTolerance;
  onToleranceChange: (v: HeatTolerance) => void;
  onSearch: () => void;
  loading: boolean;
}

function formatCoord(c: Coordinate | null) {
  if (!c) return '';
  return `${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}`;
}

export default function SearchPanel({ origin, destination, tolerance, onToleranceChange, onSearch, loading }: Props) {
  return (
    <Paper
      shadow="md"
      radius="lg"
      p="md"
      style={{ position: 'absolute', top: 16, left: 16, width: 320, zIndex: 10 }}
    >
      <Stack gap="xs">
        <TextInput
          size="sm"
          placeholder="Titik awal (klik peta)"
          value={formatCoord(origin)}
          readOnly
          leftSection={<IconMapPin size={14} color="#457b9d" />}
        />
        <TextInput
          size="sm"
          placeholder="Tujuan (klik peta)"
          value={formatCoord(destination)}
          readOnly
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
          loading={loading}
          disabled={!origin || !destination}
        >
          Cari Rute
        </Button>
      </Stack>
    </Paper>
  );
}
